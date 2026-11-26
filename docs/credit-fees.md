# 跨节点传递费

## 规则

```text
本地节点内部转账：0
跨云节点转账：1 种子积分/次
```

客户端不扣；由发送方所在的服务端扣。

## 行为

```text
发送方本地余额不足 1 种子积分
→ 拒绝跨节点转账
```

手续费记录：

```text
transactions.tx_type = node_transfer_fee
amount = 1
credit_type = credits
```

同时写入：

```text
contribution_log.event_type = node_transfer_fee
```

## 不改变

```text
sases-credit-v1
rules_hash
compute 内部字段
```

## 开发者 / 管理员豁免

以下用户不收跨节点传递费：

```text
users.is_admin = 1
或 SASES_FEE_EXEMPT_USERS=1,2,3
```

客户端仍然不扣；豁免只发生在服务端。

## 命名

对外显示：

```text
算力积分 → 源
```

内部仍使用：

```text
credit_type = compute
```

API 兼容旧值，不做数据库迁移。

## 为什么

```text
跨节点有资源成本
防止滥用
让种子积分有实际用途
```
