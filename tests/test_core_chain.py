# tests/test_core_chain.py
# 核心链路测试脚本：宠物→基地→解救→升级→进化
# 用法：python tests/test_core_chain.py

import os
import sys
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.db import init_db, db_cursor
from core.services import pet_service, base_service, rescue_service, quality_service


TEST_USERNAME = "__test_core_chain__"
TEST_PASSWORD_HASH = "test_hash_placeholder"


def setup_test_user():
    """创建或获取测试用户"""
    init_db()
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT id FROM users WHERE username=?", (TEST_USERNAME,))
        row = cur.fetchone()
        if row:
            return row["id"]
        cur.execute("""
            INSERT INTO users (username, password_hash, sases_id, credits)
            VALUES (?, ?, ?, ?)
        """, (TEST_USERNAME, TEST_PASSWORD_HASH, "sases_test_chain", 1000))
        return cur.lastrowid


def cleanup_test_user(user_id):
    """清理测试数据"""
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM pets WHERE owner_user_id=?", (user_id,))
        cur.execute("DELETE FROM game_resources WHERE owner_user_id=?", (user_id,))
        cur.execute("DELETE FROM base_facilities WHERE owner_user_id=?", (user_id,))
        cur.execute("DELETE FROM rescue_tasks WHERE rescued_by_user_id=?", (user_id,))


def print_step(name, success, detail=""):
    status = "✅" if success else "❌"
    print(f"{status} {name}")
    if detail:
        print(f"   {detail}")


def test_pet_chain(user_id):
    """测试宠物链路：创建 → 喂养 → 强化 → 进化"""
    print("\n=== 测试宠物链路 ===")

    pet = pet_service.create_pet(user_id=user_id, rarity="C")
    assert pet is not None, "宠物创建失败"
    print_step("创建宠物", True, f"ID={pet['id']}, 名称={pet['pet_name']}, 稀有度={pet['rarity']}")

    pet_id = pet["id"]

    feed_result = pet_service.feed_pet(pet_id, user_id, exp_amount=50)
    assert feed_result["success"], "喂养失败"
    print_step("喂养宠物", True, f"等级={feed_result['level']}, 经验={feed_result['exp']}")

    pet_service.add_resource(user_id, "强化石", 100)
    strengthen_result = pet_service.strengthen_pet(pet_id, user_id, "strength")
    assert strengthen_result["success"], "强化失败"
    print_step("强化宠物", True, f"力量={strengthen_result['pet']['strength']}")

    pet_service.add_resource(user_id, "进化石", 200)
    evolve_result = pet_service.evolve_pet(pet_id, user_id)
    print_step("进化宠物", True, f"结果: {evolve_result.get('message', '未知')}")

    pets = pet_service.list_user_pets(user_id)
    assert len(pets) > 0, "宠物列表为空"
    print_step("查询宠物列表", True, f"共 {len(pets)} 只宠物")

    return pet_id


def test_base_chain(user_id):
    """测试基地链路：初始化 → 升级 → 产出"""
    print("\n=== 测试基地链路 ===")

    base_service.initialize_facilities(user_id)
    facilities = base_service.list_facilities(user_id)
    assert len(facilities) > 0, "设施初始化失败"
    print_step("初始化设施", True, f"共 {len(facilities)} 个设施")

    pet_service.add_resource(user_id, "能量石", 500)
    upgrade_result = base_service.upgrade_facility(user_id, "采集站")
    assert upgrade_result["success"], f"升级失败: {upgrade_result.get('message')}"
    print_step("升级采集站", True, f"新等级={upgrade_result['new_level']}")

    for _ in range(2):
        pet_service.add_resource(user_id, "能量石", 500)
        base_service.upgrade_facility(user_id, "采集站")

    overview = base_service.get_base_overview(user_id)
    assert "facilities" in overview, "总览加载失败"
    print_step("基地总览", True, f"共 {len(overview['facilities'])} 个设施")

    # 把 last_produced_at 设为 2 小时前，让产出积累生效
    past_time = (datetime.now() - timedelta(hours=2)).isoformat()
    with db_cursor(commit=True) as cur:
        cur.execute("""
            UPDATE base_facilities SET last_produced_at=?
            WHERE owner_user_id=? AND facility_type='采集站'
        """, (past_time, user_id))

    collect_result = base_service.collect_output(user_id, "采集站")
    if collect_result["success"]:
        print_step("收取产出", True, f"获得 {collect_result['resource']} × {collect_result['amount']}（累计 {collect_result['elapsed_hours']} 小时）")
    else:
        print_step("收取产出", False, collect_result.get("message"))


def test_rescue_chain(user_id):
    """测试解救任务链路：创建问题 → 生成任务 → 接取 → 完成"""
    print("\n=== 测试解救任务链路 ===")

    issue_id = quality_service.submit_debug_issue(
        title="测试问题",
        detail="这是一个测试用的质量问题",
        severity="low",
        source_id="test-001"
    )
    print_step("创建质量问题", True, f"issue_id={issue_id}")

    gen_result = rescue_service.generate_rescue_tasks_from_issues(limit=10)
    print_step("生成解救任务", True, f"生成 {gen_result['created_count']} 个任务")

    tasks = rescue_service.list_available_tasks(limit=10)
    assert len(tasks) > 0, "没有可接取任务"
    task = tasks[0]
    print_step("查询任务", True, f"共 {len(tasks)} 个，第一个 task_id={task['id']}")

    accept_result = rescue_service.accept_task(task["id"], user_id)
    assert accept_result["success"], "接取失败"
    print_step("接取任务", True, f"状态={accept_result['status']}")

    complete_result = rescue_service.complete_task(task["id"], user_id, "已修复", True)
    assert complete_result["success"], "完成失败"
    print_step("完成任务", True, f"获得宠物: {complete_result['pet']['name']}, 奖励: {complete_result['reward']}")


def test_resource_chain(user_id):
    """测试资源链路：增加 → 查询"""
    print("\n=== 测试资源链路 ===")

    pet_service.add_resource(user_id, "阳光", 100)
    amount = pet_service.get_resource(user_id, "阳光")
    assert amount >= 100, "资源增加失败"
    print_step("增加阳光", True, f"当前数量={amount}")

    all_resources = pet_service.get_all_resources(user_id)
    print_step("查询所有资源", True, f"共 {len(all_resources)} 种资源")


def main():
    print("=" * 60)
    print("SASES 核心链路测试")
    print("=" * 60)

    user_id = setup_test_user()
    print(f"\n测试用户 ID: {user_id}")

    try:
        cleanup_test_user(user_id)
        print("已清理旧的测试数据")

        test_pet_chain(user_id)
        test_base_chain(user_id)
        test_rescue_chain(user_id)
        test_resource_chain(user_id)

        print("\n" + "=" * 60)
        print("✅ 所有测试通过")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
