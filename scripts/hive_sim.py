"""SASES 积分节点模拟 - 单机多节点验证
用法:
    python scripts/hive_sim.py --node-id node-A --db D:/sases-hive/node-A.db --port 9001 --peers http://127.0.0.1:9002,http://127.0.0.1:9003
"""
import argparse
import asyncio
import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI

NODE_ID = None
DB_PATH = None
PEERS = []
HIVE_DIR = 'D:/sases-hive'

app = FastAPI()


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS accounts (user_id INTEGER PRIMARY KEY, username TEXT, credits INTEGER DEFAULT 0, updated_at TEXT)')
    cur.execute('CREATE TABLE IF NOT EXISTS transfers (id INTEGER PRIMARY KEY AUTOINCREMENT, from_user INTEGER, to_user INTEGER, amount INTEGER, created_at TEXT)')
    cur.execute('CREATE TABLE IF NOT EXISTS anchors (id INTEGER PRIMARY KEY AUTOINCREMENT, node_id TEXT, anchor_at TEXT, credits_hash TEXT, account_count INTEGER)')
    cur.execute('CREATE TABLE IF NOT EXISTS suspected_peers (id INTEGER PRIMARY KEY AUTOINCREMENT, peer_url TEXT, peer_hash TEXT, majority_hash TEXT, detected_at TEXT, UNIQUE(peer_url))')
    cur.execute('SELECT COUNT(*) as c FROM accounts')
    if cur.fetchone()['c'] == 0:
        now = datetime.now().isoformat()
        for uid, name in [(1, 'alice'), (2, 'bob'), (3, 'carol')]:
            cur.execute('INSERT INTO accounts (user_id, username, credits, updated_at) VALUES (?, ?, ?, ?)', (uid, name, 1000, now))
    conn.commit()
    conn.close()


def compute_hash():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT user_id, credits FROM accounts ORDER BY user_id')
    rows = cur.fetchall()
    conn.close()
    raw = json.dumps([(r['user_id'], r['credits']) for r in rows], sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


@app.get('/info')
def info():
    return {'node_id': NODE_ID, 'db': str(DB_PATH)}


@app.get('/balance/{user_id}')
def balance(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT credits FROM accounts WHERE user_id=?', (user_id,))
    row = cur.fetchone()
    conn.close()
    return {'user_id': user_id, 'credits': row['credits'] if row else 0}


@app.post('/transfer')
def transfer(from_user: int, to_user: int, amount: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT credits FROM accounts WHERE user_id=?', (from_user,))
    row = cur.fetchone()
    if not row or row['credits'] < amount:
        conn.close()
        return {'ok': False, 'error': 'insufficient balance'}
    now = datetime.now().isoformat()
    cur.execute('UPDATE accounts SET credits=credits-?, updated_at=? WHERE user_id=?', (amount, now, from_user))
    cur.execute('UPDATE accounts SET credits=credits+?, updated_at=? WHERE user_id=?', (amount, now, to_user))
    cur.execute('INSERT INTO transfers (from_user, to_user, amount, created_at) VALUES (?,?,?,?)', (from_user, to_user, amount, now))
    conn.commit()
    conn.close()
    return {'ok': True, 'hash_after': compute_hash()[:16]}


@app.get('/hash')
def hash_endpoint():
    return {'node_id': NODE_ID, 'hash': compute_hash(), 'at': datetime.now().isoformat()}


@app.get('/anchors')
def list_anchors():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT * FROM anchors ORDER BY id DESC LIMIT 20')
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {'anchors': rows}


@app.get('/suspects')
def list_suspects():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT peer_url, peer_hash, majority_hash, detected_at FROM suspected_peers ORDER BY detected_at DESC')
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {'node_id': NODE_ID, 'suspects': rows}


def write_anchor():
    h = compute_hash()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) as c FROM accounts')
    cnt = cur.fetchone()['c']
    cur.execute('INSERT INTO anchors (node_id, anchor_at, credits_hash, account_count) VALUES (?,?,?,?)', (NODE_ID, datetime.now().isoformat(), h, cnt))
    conn.commit()
    conn.close()
    print(f'[{NODE_ID}] anchor: {h[:16]}... ({cnt} accounts)')


async def periodic_anchor(interval_seconds: int = 30):
    await asyncio.sleep(5)
    while True:
        try:
            write_anchor()
        except Exception as e:
            print(f'[{NODE_ID}] anchor failed: {e}')
        await asyncio.sleep(interval_seconds)


async def heartbeat_check(interval_seconds: int = 15):
    _last_alert_state = {}
    await asyncio.sleep(10)
    while True:
        try:
            my_hash = compute_hash()
            for peer in PEERS:
                try:
                    async with httpx.AsyncClient(timeout=3) as client:
                        r = await client.get(f'{peer}/hash')
                        peer_hash = r.json().get('hash')
                        if peer_hash != my_hash:
                            cur_state = (my_hash, peer_hash)
                            if _last_alert_state.get(peer) != cur_state:
                                msg = f'[{datetime.now().isoformat()}] HASH MISMATCH: {NODE_ID}={my_hash[:16]} vs {peer}={peer_hash[:16]}'
                                print(msg)
                                with open(f'{HIVE_DIR}/alerts.log', 'a', encoding='utf-8') as f:
                                    f.write(msg + chr(10))
                                _last_alert_state[peer] = cur_state
                        else:
                            _last_alert_state.pop(peer, None)
                except Exception:
                    pass
        except Exception as e:
            print(f'[{NODE_ID}] heartbeat failed: {e}')
        await asyncio.sleep(interval_seconds)


async def majority_vote_check(interval_seconds: int = 20):
    from collections import Counter
    await asyncio.sleep(15)
    while True:
        try:
            hashes = [(NODE_ID, compute_hash())]
            for peer in PEERS:
                try:
                    async with httpx.AsyncClient(timeout=3) as client:
                        r = await client.get(f'{peer}/hash')
                        hashes.append((peer, r.json().get('hash')))
                except Exception:
                    pass
            if len(hashes) < 3:
                await asyncio.sleep(interval_seconds)
                continue
            cnt = Counter(h for _, h in hashes)
            majority_hash, majority_count = cnt.most_common(1)[0]
            if majority_count >= (len(hashes) * 2 // 3):
                conn = get_conn()
                cur = conn.cursor()
                for node, h in hashes:
                    if node == NODE_ID:
                        continue
                    if h != majority_hash:
                        cur.execute('INSERT OR REPLACE INTO suspected_peers (peer_url, peer_hash, majority_hash, detected_at) VALUES (?, ?, ?, ?)', (node, h, majority_hash, datetime.now().isoformat()))
                        print(f'[{NODE_ID}] SUSPECT: {node} hash={h[:16]} vs majority={majority_hash[:16]}')
                    else:
                        cur.execute('DELETE FROM suspected_peers WHERE peer_url=?', (node,))
                conn.commit()
                conn.close()
        except Exception as e:
            print(f'[{NODE_ID}] majority_vote failed: {e}')
        await asyncio.sleep(interval_seconds)


@app.on_event('startup')
async def startup():
    asyncio.create_task(periodic_anchor(30))
    asyncio.create_task(heartbeat_check(15))
    asyncio.create_task(majority_vote_check(20))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--node-id', required=True)
    parser.add_argument('--db', required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--peers', default='')
    args = parser.parse_args()

    NODE_ID = args.node_id
    DB_PATH = Path(args.db)
    PEERS = [p.strip() for p in args.peers.split(',') if p.strip()]

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    Path(HIVE_DIR).mkdir(parents=True, exist_ok=True)

    init_db()
    print(f'[{NODE_ID}] starting, DB={DB_PATH}, port={args.port}, peers={PEERS}')

    uvicorn.run(app, host='127.0.0.1', port=args.port, log_level='warning')
