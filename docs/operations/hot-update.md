# SASES 热更新与客户端同步

## 原则

1. 只追加，不覆盖历史。
2. 每个优化先写台账：`docs/operations/optimization_ledger.md`。
3. 再写热更新清单：`docs/operations/hotfix_manifest.json`。
4. 本地和 Git 必须各有一份。
5. 客户端只同步代码/静态资源，不同步数据库、密钥、Cookie。

## 流程

```text
修改代码
  ↓
写 optimization_ledger.md
  ↓
更新 hotfix_manifest.json
  ↓
提交并推送 Git
  ↓
build_update.py 生成客户端包
  ↓
上传 client_update.zip / client_version.json
  ↓
客户端拉取、校验 sha256、替换、重启
```

## 生成客户端更新包

```bash
python build_update.py --version 1.0.0-test.42
```

输出：

```text
D:\sases_build\client_update.zip
D:\sases_build\client_version.json
D:\sases_build\code_update.zip
D:\sases_build\version.json
```

## 上传

把以下文件放到深圳 HQ：

```text
static/downloads/client_update.zip
static/downloads/client_version.json
static/downloads/code_update.zip
static/downloads/version.json
```

客户端读取：

```text
/static/downloads/client_version.json
```

校验：

```text
sha256
size
min_version
```

## 客户端应用

```text
1. 下载 zip
2. 校验 sha256
3. 解压到临时目录
4. 只替换代码/静态文件
5. 保留 .env、users.db、data/、node_identity.json、node_signing.key
6. 重启 launcher
7. 上报新版本和结果
```

## 禁止同步

```text
.env
users.db
data/
node_identity.json
node_signing.key
WireGuard 私钥
平台 Cookie/Token
```

## 回滚

```text
保留上一版 zip
客户端下载失败或启动失败时回滚上一版
数据库不随热更新回滚；如需回滚数据库，使用备份
```

## 当前清单

```text
docs/operations/optimization_ledger.md
docs/operations/hotfix_manifest.json
```
