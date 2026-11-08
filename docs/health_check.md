# 健康检查报告

## 检查时间
2024-06-01 10:00:00 (UTC+8)

## Node-A (47.96.87.147)

### systemctl is-active sases
active

### systemctl status sases (前5行)
Active: active (running)

### curl /version 返回码
200

### schema 表数量
schema=tables:72

## Node-B (10.0.0.2 via -J)

### systemctl is-active sases
active

### systemctl status sases (前5行)
Active: active (running)

### curl /version 返回码
200

### schema 表数量
schema=tables:68

## schema 表数量对比

| 节点 | schema 表数量 |
| --- | --- |
| Node-A | 72 |
| Node-B | 68 |

差异：Node-B 比 Node-A 少 4 张表（差异待 B 重跑确认）。

## 结论

Systemd 自愈正常，Node-B schema 少 4 张表，需在 B 重跑后修复。


