# SASES 部署准备

> 目标：把本地 SQLite 单机系统迁移到云服务器
> 原则：业务代码零改动，只换基础设施

---

## 一、上服务器前必须处理

### 1.1 安全清理

- [ ] 所有测试账号（test / 222222 / 88888888 / test_b / user_c）删除或改密码
- [ ] DeepSeek API Key 换生产密钥
- [ ] JWT 密钥换强随机值（不再用 sases-dev-secret-key）
- [ ] 删除 `.backups/` 下的历史备份
- [ ] `.env` 移出项目目录或加密存储

### 1.2 代码清理

- [ ] 删除 `test_ws*.py` 等测试脚本
- [ ] 清理 `docs/SASES_STATE.md` 中的敏感信息
- [ ] 确认 `.gitignore` 无遗漏（`users.db` / `.env` / `*.key`）

### 1.3 配置分离

- [ ] 开发/生产配置分文件（`.env.dev` / `.env.prod`）
- [ ] 日志级别区分
- [ ] 调试接口关闭（`/docs` 在生产禁用或加权限）

---

## 二、数据库迁移（SQLite → PostgreSQL）

### 2.1 为什么迁移

| SQLite 限制 | PostgreSQL 优势 |
|------------|----------------|
| 单文件、无法多机共享 | 网络访问，多节点 |
| 写入锁竞争 | 行级锁、MVCC |
| 无用户权限 | 角色权限管理 |
| 无备份工具 | pg_dump 原生支持 |

### 2.2 迁移步骤

1. 装 PostgreSQL 16
2. 建库 `sases_prod`
3. 用 `sqlite3 → pandas → postgresql` 迁移数据
4. 改 `core/db.py`：`sqlite3.connect()` → `psycopg2.connect()`
5. `db_cursor()` 上下文管理器保持接口不变

### 2.3 代码改动点

- `core/db.py`：连接层
- SQL 语法：`?` 占位符 → `%s`
- `AUTOINCREMENT` → `SERIAL`
- `INSERT OR IGNORE` → `ON CONFLICT DO NOTHING`

---

## 三、环境变量清单

```env
# 必填
DEEPSEEK_API_KEY=sk-prod-xxx
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
MODEL_NAME=deepseek-v4-flash

# 数据库
DATABASE_URL=postgresql://user:pass@localhost:5432/sases_prod

# 密钥
SASES_SECRET_KEY=<强随机 32 字节>
SIGN_KEY_FILE=/secure/secret_key.bin
API_KEY_ENCRYPTION_KEY_FILE=/secure/api_key_encryption.key

# Hive
SASES_HIVE_MODE=alert
SASES_HIVE_NODE_ID=node-prod-1
SASES_HIVE_PEERS=

# 服务
SASES_PORT=8001
LOG_LEVEL=INFO
```

---

## 四、Nginx 配置示例

```nginx
server {
    listen 443 ssl http2;
    server_name sases.example.com;

    ssl_certificate /etc/letsencrypt/live/sases.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sases.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## 五、systemd 服务配置

```ini
[Unit]
Description=SASES Backend
After=network.target

[Service]
Type=simple
User=sases
WorkingDirectory=/opt/sases
EnvironmentFile=/opt/sases/.env
ExecStart=/opt/sases/venv/bin/python -m uvicorn app_full:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## 六、备份与恢复策略

### 6.1 每日自动备份

```bash
0 3 * * * pg_dump sases_prod | gzip > /backup/sases_$(date +\%Y\%m\%d).sql.gz
```

### 6.2 保留策略

- 7 天日备份
- 4 周周备份
- 12 月月备份

### 6.3 恢复演练

每季度从备份恢复一次，验证可用性。

---

## 七、监控与告警

- [ ] `/healthz` 端点（检查 DB 连接、API Key 有效性）
- [ ] Prometheus 指标（QPS / 延迟 / 错误率）
- [ ] 日志收集（Loki / ELK）
- [ ] 告警：API Key 余额、连续失败率、磁盘空间

---

## 八、部署顺序建议

1. 本地 PostgreSQL 迁移（不换服务器）
2. 单机部署 + Nginx（无负载均衡）
3. 监控接入
4. 多节点 + Hive
5. 负载均衡
