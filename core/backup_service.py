# core/backup_service.py
# 数据库自动备份服务：每天备份 users.db，保留最近 7 天
import os
import shutil
import asyncio
from datetime import datetime, timedelta

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'users.db')
# 备份目录
BACKUP_DIR = os.path.join(os.path.dirname(__file__), '..', 'backups')
# 保留天数
KEEP_DAYS = 7


def ensure_backup_dir():
    """确保备份目录存在"""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)


def create_backup() -> dict:
    """创建一次备份，返回备份信息"""
    ensure_backup_dir()

    if not os.path.exists(DB_PATH):
        return {
            "success": False,
            "message": "数据库文件不存在"
        }

    today = datetime.now().strftime("%Y%m%d")
    backup_filename = f"users_{today}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)

    try:
        # 如果今天的备份已存在，先删除旧的
        if os.path.exists(backup_path):
            os.remove(backup_path)

        shutil.copy2(DB_PATH, backup_path)

        # 获取文件大小
        size_bytes = os.path.getsize(backup_path)
        size_mb = round(size_bytes / 1024 / 1024, 2)

        return {
            "success": True,
            "filename": backup_filename,
            "size_mb": size_mb,
            "created_at": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"备份失败: {str(e)}"
        }


def cleanup_old_backups() -> dict:
    """清理超过保留天数的备份"""
    ensure_backup_dir()

    cutoff = datetime.now() - timedelta(days=KEEP_DAYS)
    deleted_count = 0
    kept_count = 0

    for filename in os.listdir(BACKUP_DIR):
        if not filename.startswith("users_") or not filename.endswith(".db"):
            continue

        filepath = os.path.join(BACKUP_DIR, filename)
        try:
            # 从文件名解析日期
            date_str = filename.replace("users_", "").replace(".db", "")
            file_date = datetime.strptime(date_str, "%Y%m%d")

            if file_date < cutoff:
                os.remove(filepath)
                deleted_count += 1
            else:
                kept_count += 1
        except Exception as e:
            print(f"清理备份 {filename} 失败: {e}")

    return {
        "deleted": deleted_count,
        "kept": kept_count
    }


def list_backups() -> list:
    """列出所有备份文件"""
    ensure_backup_dir()

    backups = []
    for filename in sorted(os.listdir(BACKUP_DIR), reverse=True):
        if not filename.startswith("users_") or not filename.endswith(".db"):
            continue

        filepath = os.path.join(BACKUP_DIR, filename)
        try:
            size_bytes = os.path.getsize(filepath)
            backups.append({
                "filename": filename,
                "size_mb": round(size_bytes / 1024 / 1024, 2),
                "created_at": datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()
            })
        except Exception:
            continue

    return backups


async def periodic_backup_task():
    """后台定时任务：每天凌晨 3 点备份"""
    while True:
        try:
            now = datetime.now()
            # 计算下一个凌晨 3 点
            next_run = now.replace(hour=3, minute=0, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)

            # 等待到下一个 3 点
            wait_seconds = (next_run - now).total_seconds()
            await asyncio.sleep(wait_seconds)

            # 执行备份
            result = await asyncio.to_thread(create_backup)
            if result["success"]:
                print(f"[备份] 创建成功: {result['filename']} ({result['size_mb']} MB)")
                cleanup_result = await asyncio.to_thread(cleanup_old_backups)
                if cleanup_result["deleted"] > 0:
                    print(f"[备份] 清理 {cleanup_result['deleted']} 个旧备份")
            else:
                print(f"[备份] 失败: {result.get('message')}")

        except Exception as e:
            print(f"[备份] 定时任务异常: {e}")
            await asyncio.sleep(3600)  # 出错后等 1 小时再重试
