# 深圳 HQ：campaign / approval / task_queue

## 已完成

```text
core/hq.py
core/api_routes/hq_routes.py
core/bootstrap.py
scripts/hq_executor.py
```

## 流程

```text
创建 campaign
→ 审批
→ 生成 queued 任务
→ 本地 executor claim
→ 执行平台发布
→ receipt 回写
→ 失败自动重试（最多 3 次）
```

## API

```text
GET  /hq/campaigns
POST /hq/campaigns
POST /hq/campaigns/{id}/approve
GET  /hq/tasks
POST /hq/tasks/claim
POST /hq/tasks/{id}/receipt
```

## 示例

```bash
curl -X POST http://127.0.0.1:8001/hq/campaigns \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"name":"sases-v1","region":"cn","platforms":["x","xiaohongshu"],"content":{"body":"..."}}'
```

审批：

```bash
curl -X POST http://127.0.0.1:8001/hq/campaigns/1/approve \
  -H "Authorization: Bearer <jwt>"
```

本地执行器：

```bash
SASES_HQ_URL=http://120.77.136.90:8001 \
SASES_HQ_TOKEN=<jwt> \
python scripts/hq_executor.py --once
```

## 深圳实测

```text
create 200
approve 200
claim 200
receipt 200
```

生产容器：

```text
node-A
schema tables:120
```

## 当前适配器

```text
[✓] X
[ ] 小红书
[ ] 抖音
[ ] TikTok
[ ] Blogger
```

未实现的平台会返回：

```text
adapter_not_implemented
```

不会假装发布成功。

## 注意

- 只有审批后的任务才会变成 `queued`。
- 失败最多重试 3 次，超过后置为 `failed`。
- 本地 executor 需要 Edge CDP 和平台登录态。
- 任务 payload 必须带 GitHub 仓库。

## 镜像固化

```text
docker_sases:hq
```

已从包含 HQ 代码的仓库重新构建，并重建生产容器：

```text
/version: node-A, tables:120
/hq/campaigns: 401（路由已加载，需要认证）
create/approve/claim/receipt: 200
```

容器重建不再依赖 `docker cp`。
