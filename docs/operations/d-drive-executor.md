# D 盘 SASES 执行器

## 目的

广州远程不可用时，用 D 盘独立 SASES 版本作为本地执行器，由深圳 HQ 控制。

## 隔离原则

```text
C:\sases        保持不动，端口 8001
D:\sases        独立版本，端口 8010，节点 d-drive-executor
```

D 盘不复制 C 盘的：

```text
.env
users.db
data/
logs
```

## D 盘配置

```env
SASES_NODE_ID=d-drive-executor
SASES_EXECUTOR_ID=d-drive-executor
SASES_PORT=8010
SASES_HQ_URL=http://120.77.136.90:8001
SASES_CDP_URL=http://127.0.0.1:9222
SASES_LINK_TOKEN=<本机私密，不提交>
```

## 启动

```powershell
C:\Users\xiaomai\sases\venv312\Scripts\python.exe `
  -m uvicorn app_full:app `
  --host 127.0.0.1 --port 8010
```

## 深圳控制验证

```text
1. 深圳 HQ 创建 campaign
2. 审批
3. D 盘 hq_executor claim
4. 执行 dry-run
5. receipt 回写
```

实测结果：

```text
create  200
approve 200
claim   200
receipt 200
executor: d-drive-executor
```

## 验证命令

```powershell
$env:SASES_HQ_URL="http://120.77.136.90:8001"
$env:SASES_EXECUTOR_ID="d-drive-executor"
$env:SASES_LINK_TOKEN="<私密>"
D:\sases\scripts\hq_executor.py --once --dry-run
```

## 注意

- D 盘执行器与 C 盘共用 Python 运行时，但工作目录、数据库、端口和 `.env` 独立。
- 不影响 C 盘的 8001 服务和数据库。
- 真实发布前先 dry-run。
- 不把 `.env` 或 token 提交 Git。
