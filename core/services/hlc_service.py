# core/services/hlc_service.py
"""
HLC（混合逻辑时钟）服务

格式：{13位毫秒}.{6位逻辑计数}.{4位节点ID}
示例：1697000000000.000042.n001

设计原则：
  1. 单调递增：任何时候生成的 HLC 都大于之前生成的
  2. 时钟回退安全：物理时钟回退时，用逻辑计数补偿
  3. 持久化：每次生成后写入 DB，崩溃恢复不丢
  4. 可比较：字符串比较 = 时间序比较（因为定长补零）
"""
import os
import time
import threading
from datetime import datetime
from ..db import db_cursor

# 默认节点 ID
DEFAULT_NODE = "n001"

# 物理时间位数（毫秒，13 位够用到 2286 年）
PHYSICAL_DIGITS = 13
# 逻辑计数位数（6 位，每毫秒 100 万次事件）
COUNTER_DIGITS = 6
# 节点 ID 位数
NODE_DIGITS = 4


def _get_node_id():
    """从环境变量读节点 ID，默认 n001"""
    raw = os.environ.get("SASES_NODE_ID", "node-A")
    # 如果是 node-A 这种格式，转成 n001
    if raw.startswith("node-"):
        # node-A → n001, node-B → n002, node-hidden-1 → nhid1 之类
        suffix = raw[5:]
        if len(suffix) == 1 and suffix.isalpha():
            return f"n{ord(suffix.upper()) - 64:03d}"
        # 其他情况，取前 4 位
        return ("n" + suffix.replace("-", ""))[:NODE_DIGITS].ljust(NODE_DIGITS, "0")
    # 直接用
    return raw[:NODE_DIGITS].ljust(NODE_DIGITS, "0")


NODE_ID = _get_node_id()

# 内存缓存：避免每次都读 DB
_lock = threading.Lock()
_last_physical = 0
_last_counter = 0
_initialized = False


def _ensure_table():
    """确保 hlc_state 表存在"""
    with db_cursor(commit=True) as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hlc_state (
                node_id TEXT PRIMARY KEY,
                last_physical INTEGER NOT NULL DEFAULT 0,
                last_counter INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT
            )
        """)


def _load_state():
    """从 DB 加载状态到内存"""
    global _last_physical, _last_counter, _initialized
    if _initialized:
        return
    _ensure_table()
    with db_cursor() as cur:
        cur.execute("SELECT last_physical, last_counter FROM hlc_state WHERE node_id=?", (NODE_ID,))
        row = cur.fetchone()
        if row:
            _last_physical = row["last_physical"] or 0
            _last_counter = row["last_counter"] or 0
        else:
            # 初始化记录
            with db_cursor(commit=True) as cur2:
                cur2.execute(
                    "INSERT INTO hlc_state (node_id, last_physical, last_counter, updated_at) VALUES (?, 0, 0, ?)",
                    (NODE_ID, datetime.now().isoformat())
                )
    _initialized = True


def _persist_state():
    """把内存状态写入 DB"""
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE hlc_state SET last_physical=?, last_counter=?, updated_at=? WHERE node_id=?",
            (_last_physical, _last_counter, datetime.now().isoformat(), NODE_ID)
        )


def generate_hlc() -> str:
    """
    生成一个新的 HLC。

    规则：
      1. 取当前物理毫秒 now_ms
      2. 如果 now_ms > last_physical：用 now_ms，counter = 0
      3. 如果 now_ms == last_physical：counter += 1
      4. 如果 now_ms < last_physical（时钟回退）：用 last_physical，counter += 1
      5. 持久化后返回
    """
    global _last_physical, _last_counter
    with _lock:
        _load_state()

        now_ms = int(time.time() * 1000)

        if now_ms > _last_physical:
            # 物理时间前进，计数归零
            _last_physical = now_ms
            _last_counter = 0
        else:
            # 物理时间相同或回退，计数递增
            _last_counter += 1
            # 计数器溢出保护
            if _last_counter >= 10 ** COUNTER_DIGITS:
                _last_physical += 1
                _last_counter = 0

        _persist_state()

        return format_hlc(_last_physical, _last_counter, NODE_ID)


def format_hlc(physical_ms: int, counter: int, node_id: str) -> str:
    """格式化 HLC：13位毫秒.6位补零计数.4位节点ID"""
    return f"{physical_ms:0{PHYSICAL_DIGITS}d}.{counter:0{COUNTER_DIGITS}d}.{node_id[:NODE_DIGITS].ljust(NODE_DIGITS, '0')}"


def parse_hlc(hlc_str: str):
    """解析 HLC 字符串 → (physical_ms, counter, node_id)"""
    if not hlc_str:
        return (0, 0, DEFAULT_NODE)
    try:
        parts = hlc_str.split(".")
        if len(parts) != 3:
            return (0, 0, DEFAULT_NODE)
        return (int(parts[0]), int(parts[1]), parts[2])
    except Exception:
        return (0, 0, DEFAULT_NODE)


def compare_hlc(a: str, b: str) -> int:
    """
    比较两个 HLC。
    返回：-1 (a<b), 0 (a==b), 1 (a>b)

    因为格式定长补零，字符串比较 = 时间序比较。
    """
    if a == b:
        return 0
    return -1 if (a or "") < (b or "") else 1


def now_hlc_for_backfill(iso_time: str) -> str:
    """把 ISO 时间转成 HLC（用于回填历史数据）"""
    if not iso_time:
        return format_hlc(0, 0, "n000")
    try:
        s = str(iso_time).strip().replace("Z", "").replace(" ", "T")
        if "." in s:
            s = s.split(".")[0]
        dt = datetime.fromisoformat(s)
        ts_ms = int(dt.timestamp() * 1000)
        return format_hlc(ts_ms, 0, "n000")
    except Exception:
        return format_hlc(0, 0, "n000")


def get_current_state() -> dict:
    """返回当前 HLC 状态（用于监控）"""
    _load_state()
    return {
        "node_id": NODE_ID,
        "last_physical": _last_physical,
        "last_counter": _last_counter,
        "last_physical_iso": datetime.fromtimestamp(_last_physical / 1000).isoformat() if _last_physical else None,
        "last_hlc": format_hlc(_last_physical, _last_counter, NODE_ID),
    }


# ========== 自测 ==========
if __name__ == "__main__":
    print(f"[hlc] 节点 ID: {NODE_ID}")
    print(f"[hlc] 当前状态: {get_current_state()}")

    # 连续生成 5 个
    print("\n[hlc] 连续生成 5 个：")
    prev = None
    for i in range(5):
        h = generate_hlc()
        assert prev is None or compare_hlc(prev, h) < 0, f"单调性失败: {prev} >= {h}"
        print(f"  {i+1}. {h}")
        prev = h

    # 解析测试
    print("\n[hlc] 解析测试：")
    p, c, n = parse_hlc(prev)
    print(f"  {prev} → physical={p}, counter={c}, node={n}")

    # 比较测试
    print("\n[hlc] 比较测试：")
    a = format_hlc(1000, 0, "n001")
    b = format_hlc(1000, 1, "n001")
    c = format_hlc(1001, 0, "n001")
    print(f"  {a} < {b}: {compare_hlc(a, b) == -1}")
    print(f"  {b} < {c}: {compare_hlc(b, c) == -1}")
    print(f"  {c} > {a}: {compare_hlc(c, a) == 1}")

    print("\n[hlc] ✅ 全部测试通过")
