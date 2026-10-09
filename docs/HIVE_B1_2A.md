# B1.2-A：独立只读副本（2026-10-09）

## 目标

让 8002 从"共享 DB 的第二个入口"升级为"独立 DB 的只读副本"。

## 架构

8001（主，可读写）
   ↓ /hive/replica/export 全量导出
8002（副本，只读）
   ├── 独立 DB（hive-nodes/node-B/replica.db）
   ├── 定期同步（每 30 秒）
   └── 写操作被中间件拦截（403）

## 同步范围（REPLICA_TABLES）

- users
- conversations
- messages
- groups
- group_members
- group_messages
- pets
- game_resources
- base_facilities
- transactions
- contribution_log

## 关键实现

### 1. core/hive/replica.py
- export_replica()：主节点导出核心表
- apply_replica()：副本全量覆盖本地表
- sync_replica_from_master()：副本定期同步

### 2. 只读中间件（bootstrap.py）
- 拦截 POST/PUT/PATCH/DELETE
- 白名单：/token /auth /hive
- 其他写操作返回 403 read-only replica

### 3. 环境变量
- REPLICA_MODE=true 开启副本模式
- SASES_DB_PATH=hive-nodes/node-B/replica.db 指定独立 DB
- SASES_DISABLE_FK=true 关闭外键约束

## 遇到的问题

### 问题 1：space_nodes 表从未被建
- 主库 users.db 里有（历史遗留）
- 新 DB 没有 → 启动崩
- 修复：db.py 补 CREATE TABLE space_nodes

### 问题 2：users 表字段不齐
- 主库有 17 列，副本只有 13 列
- 缺：state_hash / tampered_flag / auto_pollinate_enabled / is_admin / email
- 修复：db.py 补 4 个 _ensure_column + email

### 问题 3：同步时列不匹配
- 主库 SELECT * 拿到所有列
- 副本 INSERT 时表里没有某列 → 报错
- 修复：apply_replica 取"两边共有的列"

## 验证结果

| 表 | replica.db | 主库 |
|----|-----------|------|
| users | 8 | 8 |
| conversations | 8 | 8 |
| messages | 1712 | 1712 |
| groups | 2 | 2 |

写操作验证：POST /messages/send → 403 read-only replica

## 局限

- 副本不能写（写操作 403）
- 只同步 11 张核心表（不是全量 49 张）
- 全量覆盖（每次 DELETE + INSERT）
- 数据量大时性能会下降（当前 1712 条消息可接受）

## 下一步 B1.2-B

- 副本支持读+写（本地写入）
- 双向同步（副本的写回传给主）
- 冲突解决（logical_clock）
