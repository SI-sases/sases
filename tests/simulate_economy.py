# tests/simulate_economy.py
# 经济模型模拟脚本：模拟 100 个虚拟玩家 30 天行为
# 用法：python tests/simulate_economy.py

import random
import statistics
from datetime import datetime, timedelta
from collections import defaultdict


# ========== 配置 ==========
NUM_PLAYERS = 100
NUM_DAYS = 30

# 玩家类型分布
PLAYER_TYPES = {
    "active": 0.2,      # 20% 活跃玩家
    "medium": 0.5,      # 50% 中度玩家
    "casual": 0.3       # 30% 休闲玩家
}

# 玩家行为参数
PLAYER_BEHAVIOR = {
    "active": {
        "daily_login": 1.0,
        "rescue_tasks_per_day": 3,
        "feed_pet_per_day": 5,
        "evolve_attempts_per_day": 1,
        "battle_per_day": 3,
        "base_collect_per_day": 3
    },
    "medium": {
        "daily_login": 0.7,
        "rescue_tasks_per_day": 1.5,
        "feed_pet_per_day": 2,
        "evolve_attempts_per_day": 0.5,
        "battle_per_day": 1,
        "base_collect_per_day": 1
    },
    "casual": {
        "daily_login": 0.4,
        "rescue_tasks_per_day": 0.5,
        "feed_pet_per_day": 1,
        "evolve_attempts_per_day": 0.2,
        "battle_per_day": 0.3,
        "base_collect_per_day": 0.5
    }
}

# 产出参数
BASE_OUTPUT_PER_HOUR = 1.0       # 采集站基础产出
AVG_FACILITY_LEVEL = 5           # 平均设施等级
SUNLIGHT_PER_COLLECT = BASE_OUTPUT_PER_HOUR * (1 + AVG_FACILITY_LEVEL * 0.08) * 8  # 每次收取8小时

# 解救奖励
RESCUE_REWARD_SUNLIGHT = 10
RESCUE_REWARD_PET_LEVELS = {"low": "C", "medium": "A", "high": "SR"}
RESCUE_REWARD_DISTRIBUTION = {"low": 0.7, "medium": 0.25, "high": 0.05}

# 宠物进化消耗与成功率
EVOLVE_COST = {
    "C": {"stones": 10, "success_rate": 0.80},
    "B": {"stones": 20, "success_rate": 0.70},
    "A": {"stones": 50, "success_rate": 0.60},
    "S": {"stones": 100, "success_rate": 0.40},
    "SR": {"stones": 200, "success_rate": 0.20},
}

# 博弈对局
BATTLE_ENTRY_FEE = 20
BATTLE_PLATFORM_FEE = 0.05  # 5% 抽成
BATTLE_REWARD_POOL = BATTLE_ENTRY_FEE * 2 * (1 - BATTLE_PLATFORM_FEE)


# ========== 玩家模型 ==========
class Player:
    def __init__(self, player_id, player_type):
        self.id = player_id
        self.type = player_type
        self.behavior = PLAYER_BEHAVIOR[player_type]

        # 资源
        self.resources = {
            "阳光": 100,
            "能量石": 50,
            "进化石": 20,
            "强化石": 30,
            "晶石": 10,
            "万能钥匙": 1
        }

        # 宠物
        self.pets = {
            "C": 2,
            "B": 0,
            "A": 0,
            "S": 0,
            "SR": 0,
            "SSR": 0
        }

        # 累计数据
        self.total_rescues = 0
        self.total_evolves_attempted = 0
        self.total_evolves_success = 0
        self.total_battles = 0
        self.total_battle_wins = 0

    def daily_activity(self, day):
        """模拟玩家一天的活动"""
        if random.random() > self.behavior["daily_login"]:
            return  # 今天没登录

        # 1. 收取基地产出
        collects = self.behavior["base_collect_per_day"]
        for _ in range(int(collects)):
            if random.random() < (collects - int(collects)) or _ < int(collects):
                self.resources["阳光"] += int(SUNLIGHT_PER_COLLECT)
                self.resources["能量石"] += random.randint(0, 3)
                self.resources["进化石"] += random.randint(0, 1)

        # 2. 完成解救任务
        rescues = self.behavior["rescue_tasks_per_day"]
        for _ in range(int(rescues)):
            if random.random() < (rescues - int(rescues)) or _ < int(rescues):
                self.resources["阳光"] += RESCUE_REWARD_SUNLIGHT
                self.resources["万能钥匙"] += 1
                # 随机获得宠物
                roll = random.random()
                cumul = 0
                for level, prob in RESCUE_REWARD_DISTRIBUTION.items():
                    cumul += prob
                    if roll < cumul:
                        pet_rarity = RESCUE_REWARD_PET_LEVELS[level]
                        self.pets[pet_rarity] += 1
                        break
                self.total_rescues += 1

        # 3. 喂养宠物
        feeds = self.behavior["feed_pet_per_day"]
        for _ in range(int(feeds)):
            # 喂养消耗经验胶囊，简化为消耗少量资源
            if self.resources["阳光"] >= 5:
                self.resources["阳光"] -= 5

        # 4. 尝试进化宠物
        evolves = self.behavior["evolve_attempts_per_day"]
        for _ in range(int(evolves)):
            self._try_evolve()

        # 5. 参与博弈对局
        battles = self.behavior["battle_per_day"]
        for _ in range(int(battles)):
            if random.random() < (battles - int(battles)) or _ < int(battles):
                self._do_battle()

    def _try_evolve(self):
        """尝试进化一只宠物"""
        # 找到一只可以进化的宠物
        for rarity in ["C", "B", "A", "S", "SR"]:
            if self.pets[rarity] > 0:
                cost = EVOLVE_COST[rarity]
                if self.resources["进化石"] >= cost["stones"]:
                    self.resources["进化石"] -= cost["stones"]
                    self.total_evolves_attempted += 1
                    if random.random() < cost["success_rate"]:
                        # 进化成功
                        next_rarity = {"C": "B", "B": "A", "A": "S", "S": "SR", "SR": "SSR"}[rarity]
                        self.pets[rarity] -= 1
                        self.pets[next_rarity] += 1
                        self.total_evolves_success += 1
                    return

    def _do_battle(self):
        """参与一次博弈对局"""
        if self.resources["阳光"] < BATTLE_ENTRY_FEE:
            return
        self.resources["阳光"] -= BATTLE_ENTRY_FEE
        self.total_battles += 1

        # 简化胜率：按玩家类型
        win_rate = {"active": 0.6, "medium": 0.5, "casual": 0.4}[self.type]
        if random.random() < win_rate:
            self.resources["阳光"] += int(BATTLE_REWARD_POOL)
            self.total_battle_wins += 1


# ========== 模拟执行 ==========
def run_simulation():
    print("=" * 60)
    print(f"经济模型模拟：{NUM_PLAYERS} 个玩家 × {NUM_DAYS} 天")
    print("=" * 60)

    # 创建玩家
    players = []
    for i in range(NUM_PLAYERS):
        roll = random.random()
        cumul = 0
        ptype = "medium"
        for t, prob in PLAYER_TYPES.items():
            cumul += prob
            if roll < cumul:
                ptype = t
                break
        players.append(Player(i, ptype))

    # 记录每天的快照
    daily_snapshots = []

    for day in range(1, NUM_DAYS + 1):
        for p in players:
            p.daily_activity(day)

        # 记录当天快照
        snapshot = {
            "day": day,
            "阳光": sum(p.resources["阳光"] for p in players),
            "能量石": sum(p.resources["能量石"] for p in players),
            "进化石": sum(p.resources["进化石"] for p in players),
            "强化石": sum(p.resources["强化石"] for p in players),
            "晶石": sum(p.resources["晶石"] for p in players),
            "宠物C": sum(p.pets["C"] for p in players),
            "宠物B": sum(p.pets["B"] for p in players),
            "宠物A": sum(p.pets["A"] for p in players),
            "宠物S": sum(p.pets["S"] for p in players),
            "宠物SR": sum(p.pets["SR"] for p in players),
            "宠物SSR": sum(p.pets["SSR"] for p in players),
            "累计解救": sum(p.total_rescues for p in players),
            "累计进化": sum(p.total_evolves_attempted for p in players),
            "累计对局": sum(p.total_battles for p in players),
        }
        daily_snapshots.append(snapshot)

        if day % 5 == 0 or day == 1 or day == NUM_DAYS:
            print(f"\n第 {day} 天:")
            print(f"  阳光总量: {snapshot['阳光']:,}")
            print(f"  进化石总量: {snapshot['进化石']:,}")
            print(f"  宠物分布: C={snapshot['宠物C']}, B={snapshot['宠物B']}, A={snapshot['宠物A']}, S={snapshot['宠物S']}, SR={snapshot['宠物SR']}, SSR={snapshot['宠物SSR']}")
            print(f"  累计解救: {snapshot['累计解救']}, 累计进化: {snapshot['累计进化']}, 累计对局: {snapshot['累计对局']}")

    # ========== 最终统计 ==========
    print("\n" + "=" * 60)
    print("最终统计报告")
    print("=" * 60)

    final = daily_snapshots[-1]
    first = daily_snapshots[0]

    print("\n【资源总量变化】")
    for resource in ["阳光", "能量石", "进化石", "强化石", "晶石"]:
        start = first[resource]
        end = final[resource]
        growth = (end - start) / start * 100 if start > 0 else 0
        print(f"  {resource}: {start:,} → {end:,} ({growth:+.1f}%)")

    print("\n【宠物分布变化】")
    for pet in ["宠物C", "宠物B", "宠物A", "宠物S", "宠物SR", "宠物SSR"]:
        start = first[pet]
        end = final[pet]
        print(f"  {pet}: {start} → {end}")

    print("\n【玩家行为统计】")
    total_rescues = sum(p.total_rescues for p in players)
    total_evolves = sum(p.total_evolves_attempted for p in players)
    total_evolves_success = sum(p.total_evolves_success for p in players)
    total_battles = sum(p.total_battles for p in players)
    total_wins = sum(p.total_battle_wins for p in players)

    print(f"  总解救任务: {total_rescues}")
    print(f"  总进化尝试: {total_evolves}，成功 {total_evolves_success}（成功率 {total_evolves_success/total_evolves*100:.1f}%）")
    print(f"  总博弈对局: {total_battles}，胜场 {total_wins}（胜率 {total_wins/total_battles*100:.1f}%）")

    print("\n【按玩家类型统计】")
    for ptype in ["active", "medium", "casual"]:
        type_players = [p for p in players if p.type == ptype]
        avg_sunlight = statistics.mean(p.resources["阳光"] for p in type_players) if type_players else 0
        avg_pets = statistics.mean(sum(p.pets.values()) for p in type_players) if type_players else 0
        print(f"  {ptype}: {len(type_players)} 人，平均阳光 {avg_sunlight:.0f}，平均宠物 {avg_pets:.1f}")

    print("\n【异常检测】")
    # 检测资源是否爆炸增长
    sunlight_growth = (final["阳光"] - first["阳光"]) / first["阳光"] if first["阳光"] > 0 else 0
    if sunlight_growth > 10:
        print(f"  ⚠️ 阳光 30 天增长超过 10 倍，可能通胀过快")
    else:
        print(f"  ✅ 阳光增长 {sunlight_growth*100:.1f}%，处于合理范围")

    # 检测宠物是否过度集中
    total_pets = sum(final[p] for p in ["宠物C", "宠物B", "宠物A", "宠物S", "宠物SR", "宠物SSR"])
    high_rarity = final["宠物SR"] + final["宠物SSR"]
    high_ratio = high_rarity / total_pets if total_pets > 0 else 0
    if high_ratio > 0.3:
        print(f"  ⚠️ 高稀有度宠物占比 {high_ratio*100:.1f}%，可能过易获得")
    else:
        print(f"  ✅ 高稀有度宠物占比 {high_ratio*100:.1f}%，分布合理")

    # 检测进化石是否枯竭
    if final["进化石"] < 100:
        print(f"  ⚠️ 进化石总量仅 {final['进化石']}，可能过于稀缺")
    else:
        print(f"  ✅ 进化石总量 {final['进化石']}，供应充足")

    print("\n" + "=" * 60)
    print("模拟完成")
    print("=" * 60)


if __name__ == "__main__":
    random.seed(42)  # 固定随机种子，保证结果可复现
    run_simulation()
