# 模型 Key

## 配置

在 `.env` 中配置：

```text
DEEPSEEK_API_KEY=...
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
MODEL_NAME=deepseek-v4-flash
```

配置后重启 SASES。

## 常见错误

- `401`：Key 无效或过期
- `402`：余额不足
- `404`：Base URL 或模型名错误
- `timeout`：网络或代理问题

## 安全

不要把 Key 发到群里、截图、公开仓库。
如果 Key 泄露，立即在服务商后台删除并重建。
