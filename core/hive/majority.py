"""core/hive/majority.py —— 多数决：收集所有节点 hash，判定异常。"""
import asyncio
from collections import Counter

from core.hive.config import NODE_ID, HIVE_PEERS, VOTE_INTERVAL
from core.hive.ledger import compute_ledger_hash


async def majority_vote_check():
    if not HIVE_PEERS:
        return
    import httpx
    await asyncio.sleep(20)
    while True:
        try:
            hashes = [(NODE_ID, compute_ledger_hash()[0])]
            async with httpx.AsyncClient(timeout=5, trust_env=False) as client:
                for peer in HIVE_PEERS:
                    try:
                        r = await client.get(f"{peer}/hive/anchor")
                        data = r.json()
                        hashes.append((data.get("node_id", peer), data.get("anchor_hash")))
                    except Exception:
                        pass

            if len(hashes) < 3:
                await asyncio.sleep(VOTE_INTERVAL)
                continue

            cnt = Counter(h for _, h in hashes)
            majority_hash, majority_count = cnt.most_common(1)[0]
            if majority_count >= (len(hashes) * 2 // 3):
                for node, h in hashes:
                    if h != majority_hash:
                        print(
                            f"[hive-vote] SUSPECT: {node} "
                            f"hash={h[:16]} vs majority={majority_hash[:16]}"
                        )
        except Exception as e:
            print(f"[hive-vote] error: {e}")
        await asyncio.sleep(VOTE_INTERVAL)