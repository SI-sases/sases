# Hive Credits Experiment Report

> Date: 2026-09-26
> Environment: Single machine (Windows), Python 3.12 + FastAPI + SQLite
> Nodes: 10 (node-A to node-J, ports 9001-9010)

---

## 1. Objective

Validate whether a single machine can simulate a multi-node "hive" and verify these mechanisms:

1. Data isolation (each node has its own database)
2. Hash anchoring (accurately reflects credit state)
3. Tamper detection (any node's change can be detected by others)
4. Alert deduplication (no log explosion)
5. Majority vote consensus (collectively identify abnormal nodes)

---

## 2. Implementation

### 2.1 Core Scripts

- `scripts/hive_sim.py`: single-node service, exposes 5 APIs
- `scripts/hive_batch.py`: batch launcher for N nodes

### 2.2 API List

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/info` | GET | Returns node ID and DB path |
| `/balance/{user_id}` | GET | Query a user's credits |
| `/transfer` | POST | Transfer credits (params: from_user, to_user, amount) |
| `/hash` | GET | Returns SHA256 of full credit state |
| `/anchors` | GET | Latest 20 anchor records |
| `/suspects` | GET | Peers this node considers abnormal |

### 2.3 Database Tables

Each node has an independent DB with 4 tables:

- `accounts`: user_id, username, credits
- `transfers`: transfer records
- `anchors`: hash anchor history
- `suspected_peers`: peers considered abnormal by this node

### 2.4 Background Tasks

- `periodic_anchor(30)`: writes anchor every 30 seconds
- `heartbeat_check(15)`: compares hashes with peers every 15 seconds (with dedup)
- `majority_vote_check(20)`: collects all peer hashes every 20 seconds, uses majority vote to identify anomalies

---

## 3. Experiment Steps and Results

### 3.1 Launch 10 Nodes

    python scripts/hive_batch.py --count 10 --port-base 9001

Result: All 10 nodes started, each using ~68MB memory.

### 3.2 Initial Consistency Check

All 10 nodes start with identical hash (25019b74caf6176a).

### 3.3 Tamper Test

Transfer 100 credits on node-A. Result: node-A hash becomes b98341b4d3207844, other 9 nodes remain at 25019b74caf6176a.

### 3.4 Alert Deduplication Verification

Before fix: 360 alerts in 3 minutes.
After fix: 18 alerts in 2 minutes, still 18 after 5 minutes.
Conclusion: Deduplication works.

### 3.5 Majority Vote Verification

After tampering node-A:
- Node 9001 (A): suspects = 0
- Nodes 9002-9010: suspects = 1 (each marks A)

Key: All 9 nodes record identical majority_hash, achieving consensus.

---

## 4. Key Findings

### 4.1 Single Machine Can Host Multiple Virtual Nodes
10 nodes: 680MB. Predicted 100 nodes: ~6.8GB.

### 4.2 Hash Anchoring is Precise
Any credit change is immediately reflected. SHA256 guarantees no collisions.

### 4.3 Deduplication is Essential
Without it: dozens of alerts per minute. With it: one per state change.

### 4.4 Isolation Effect of Majority Vote
The abnormal node does NOT know. Matches collective consensus.

---

## 5. Limitations

### 5.1 Single Machine Equals Single Trust Boundary
10 processes still controlled by one person. Not true decentralization.

### 5.2 Unimplemented
Cross-node transfers, automatic lockout, network partition tolerance, Ed25519 identity.

### 5.3 Edge Cases
Startup time differences, concurrent log writes, heartbeat overhead.

---

## 6. Recommendations

### 6.1 Short-term
Integrate into SASES (expose /hive/hash), add external anchoring, add node identity.

### 6.2 Mid-term
Verify on 3 real machines, add majority-vote lockout, two-phase commit.

### 6.3 Long-term
DHT discovery, lightweight chain, decentralized identity.

---

## 7. File Inventory

- scripts/hive_sim.py: Single-node service
- scripts/hive_batch.py: Batch launcher
- D:/sases-hive/node-*.db: Independent DBs per node
- D:/sases-hive/alerts.log: Hash mismatch alerts

---

## 7.5 Cross-Instance Group Chat (Stage 2)

### Implemented

- Group creation sync: `POST /hive/sync/group` + auto-broadcast
- Member invite sync: `POST /hive/sync/member` + auto-broadcast
- Message sync: `POST /hive/sync/message` + auto-broadcast
- Dedup by `global_msg_id` (messages) and `global_group_id` (groups)

### Tested

3 instances (node-A/B/C) on the same machine:
- Group created on node-A → visible on node-B/C in 3 seconds
- Member invited on node-A → appears on node-B/C
- Message sent on node-A → appears on node-B/C with same global_msg_id

### Known Limitations

- Member removal not broadcasted (TODO)
- Leave group not broadcasted (TODO)
- No WebSocket push (needs manual refresh)
- Old messages before deploy are not retroactively synced


## 8. Conclusion

Single-machine hive is fully feasible. Hash anchoring plus majority vote detects inconsistency and achieves consensus.

Full tamper-proofing requires multiple independent machines. Single-machine validates mechanism feasibility only.

---

Experiment by: SASES Team
Date: 2026-09-26
