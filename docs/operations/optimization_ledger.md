# SASES 优化台账（加法原则）

规则：只追加，不覆盖历史。每个问题必须记录问题、优化、验证、涉及文件、影响节点和热更新范围。

## 本地 Windows / 客户端

| 问题 | 优化 | 验证 | 文件 | 热更新 |
|---|---|---|---|---|
| 启动器交接 `python-embed` 缺少 PyQt6，EXE 静默退出 | EXE 直接运行内置 UI，不再交接外部 Python | 启动器可正常打开 | `launcher/launcher.py`、`launcher/ui/main_window.py` | 需要 |
| 隐藏 Hive 节点 8101/8102 端口冲突 | 移除隐藏节点和定时器 | 不再出现 node-hidden-1/2 | `launcher/ui/main_window.py` | 需要 |
| HKCU 自启动不稳定，Guardian 重复拉起 | Guardian 计划任务 + 两连败重启 + 单实例保护 | 只有一个 SASES 实例 | `scripts/guardian.ps1`、`scripts/install_guardian.ps1` | 需要 |
| `/messages/conversations`、`/group/list` 日志刷屏 | 启动器日志过滤 + messages.js 300ms 防抖 | 日志量和请求量下降 | `static/modules/messages.js`、`launcher/ui/main_window.py` | 需要 |
| 小窗口点击未命中 | `focused_window=false` 时两段式点击 + 窗口聚焦 | `click_focus_ok.txt=True` | `harness_modules/screen_click/main.py` | 需要 |
| 两个 link_agent 抢同一个锁 | 按身份区分锁文件 | 两个节点可同时运行 | `scripts/link_agent.py` | 需要 |
| WireGuard 在线引导程序失败 | 优先完整 MSI 安装包 | 远程安装返回 installed=true | `launcher/wireguard_setup.py` | 需要 |
| Playwright 默认启动缺少 headless shell | 固定 Chromium 可执行文件路径 | `playwright_ok Example Domain` | 发布执行器配置 | 客户端配置，不打包浏览器 |
| 平台登录态不统一 | 统一平台账号清单 | `docs/agi_promotion/platform_accounts.md` | 文档 | 不需要 |
| 本地 SASES 8001 未监听，任务无法执行 | 启动 `scripts/run_forever.py`，设置 `SASES_NODE_ID=local-assistant` | `/version` 返回 local-assistant | `.env`、本地进程 | 不适用 |
| 浏览器执行器无统一入口 | 新增 `scripts/browser_exec.py`，固定 Chromium 路径，异常返回结构化 JSON | `example.com` 返回 ok=true | `scripts/browser_exec.py` | 需要 |
| 新浏览器没有平台登录态 | XHS 会跳 `/login`，抖音创作者页跳首页，Medium 跳登录 | 记录为 `needs_login`，不再静默失败 | `docs/operations/optimization_ledger.md` | 需要 |
| 浏览器执行器无持久化会话 | 增加 `--profile` 支持 Edge/Chromium 用户目录 | 空 profile 测试 ok=true | `scripts/browser_exec.py` | 需要 |
| 新浏览器没有已登录 Edge 会话 | 增加 CDP 接管 `--cdp http://127.0.0.1:9222`，直接使用 Edge 登录态 | XHS 返回 `sases - rednote`，ok=true | `scripts/browser_exec.py`、`scripts/start_edge_cdp.ps1` | 需要 |
| Edge 重启后 CDP 不稳定 | 增加 `scripts/start_edge_cdp.ps1`，检查 9222 并带调试端口重启 Edge | CDP ready on 9222 | `scripts/start_edge_cdp.ps1` | 需要 |
| 本地 SASES/Edge 重启后需人工启动 | 增加 `start_local_stack.ps1` + 启动文件夹快捷方式 | cdp=True sases=True | `scripts/start_local_stack.ps1`、`scripts/install_local_stack.ps1` | 需要 |
| Edge profile 路径含空格，CDP 启动后变成新 profile | 用 `C:\edge_profile` junction 指向真实 User Data，固定 Default profile | CDP ready on 9222 | `scripts/start_edge_cdp.ps1` | 需要 |
| 平台登录态不透明 | 增加 `platform_check.py`，通过 CDP 逐个检查 | 小红书/抖音页面空白 page_error；GitHub/gitcn logged_in；Medium/LinkedIn/Blogger needs_login | `scripts/platform_check.py` | 需要 |
| 平台账号资料分散 | 统一六个平台资料，所有内容必须带 GitHub 仓库 | `docs/agi_promotion/platform_accounts.md` | 文档 + `scripts/account_inventory.py` | 不需要 |
| 小红书/抖音发布页空包或要求重新登录 | 页面诊断：小红书 page_error；抖音“页面暂时无法打开/重新登录”识别为 needs_login | `platform_check.py` 输出明确状态 | `scripts/platform_check.py` | 需要 |
| 误判为 CDP 导致小红书空白 | 用普通 Edge（无 CDP）复测，仍空白，确认是平台页面/网络侧 | 普通 Edge 截图空白 | 台账 | 不需要 |
| Medium/gitcn 不稳定或不使用 | 从执行清单移除 | 平台表只保留六个 | `platform_accounts.md`、`platform_check.py` | 需要 |

## 深圳 node-A（HQ）

| 问题 | 优化 | 验证 | 文件 | 热更新 |
|---|---|---|---|---|
| 干净 Ubuntu 无 Docker | 安装 Docker 29.1.3 + docker-compose | `docker --version` | 服务器环境 | 不适用 |
| Docker Hub/PyPI 不可达 | 使用 daocloud 镜像 + `PIP_INDEX_URL` | 镜像构建成功 | `deploy/docker/Dockerfile` | 需要 |
| Dockerfile apt 卡住 | 去掉 apt/build-essential，改用 slim + Python healthcheck | 构建 1.27GB 成功 | `deploy/docker/Dockerfile` | 需要 |
| compose 构建上下文错误 | 从仓库根构建，`-f deploy/docker/Dockerfile` | 构建成功 | 部署命令 | 不需要 |
| compose v1 `ContainerConfig` 报错 | 生产改用 `docker run`，文档要求 compose v2 | `/version` 正常 | `docs/self-hosting.md` | 不需要 |
| 只绑定 127.0.0.1 导致香港不可达 | 生产绑定 `0.0.0.0:8001` | 香港 18003 → node-A | `docker run` 参数 | 不需要 |
| 生产数据丢失 | 恢复 `users.db`、`.env`、`data/` | users 38、integrity ok | 备份包 | 不适用 |
| wg1 未恢复，广州不可达 | 恢复 wg1 `10.10.0.1/24`、51821 | wg1 active | `/etc/wireguard/wg1.conf` | 不适用 |
| 容器内 link_agent 用 127.0.0.1 连不到宿主 | 使用 `172.17.0.1:18002` | node-A→node-B delivered=true | `sases-link.service`、`.env` | 需要 |
| compose healthcheck 仍用 curl | 删除 compose 覆盖，使用镜像 Python healthcheck | Docker CI success | `deploy/docker/docker-compose.yml` | 需要 |
| 总部角色只有策略文件 | 设置 `node-A` HQ、`node-C`/`node-B` 地区、local executor | `region_policy.json` 校验 | `region_policy.json` | 需要 |

## 杭州 node-C

| 问题 | 优化 | 验证 | 文件 | 热更新 |
|---|---|---|---|---|
| wg0 hub 需同时连香港/深圳 | 保留 `10.0.0.1:51820` hub，双 peer | 两 peer 握手 | `/etc/wireguard/wg0.conf` | 不适用 |
| 杭州到香港直连可用 | 保留 HZ↔HK 40ms 路径 | ping/TCP 8001 | 网络 | 不适用 |
| 深圳↔香港不能直连 | 杭州继续做中继 | HK→SZ 18003 正常 | SSH 隧道 | 不适用 |
| VPN 客户端缺少统一入口 | 10.0.0.10 客户端 | 可访问 10.0.0.1/2/3 | `/root/vpnclient1.conf` | 不适用 |
| region 节点 ID 是旧 Windows ID | 改为 `node-C`/`node-B` | policy 校验 | `region_policy.json` | 需要 |

## 香港 node-B

| 问题 | 优化 | 验证 | 文件 | 热更新 |
|---|---|---|---|---|
| 深圳↔香港直连被阻断 | 通过杭州 SSH 隧道 | 18003 → node-A | `sases-sz-tunnel.service` | 不适用 |
| link_agent 拉到自己的 inbox | 拉取时带 `receiver=<本节点>` | node-B 可领取 node-A 任务 | `scripts/link_agent.py` | 需要 |
| 双方 manifest issuer 不同 | 共享 `SASES_LINK_TOKEN` 临时认证 | 跨节点 200 | `core/api_routes/link_routes.py` | 需要 |
| 深圳→香港发布失败 | 修正 base 后 delivered=true | `prod_restore_001` | `.env` | 需要 |

## Git 与发布

| 内容 | 提交/状态 |
|---|---|
| Docker slim + pip mirror | `a0abe47` |
| compose healthcheck 修复 | `694fe48` |
| 云端更新文档 | `f9d0d1f` |
| 平台发布方案 | `1904292` |
| HQ 策略/平台清单 | `c0c7df5` |
| v1.0.0 Release + 源码资产 | 已发布 |
| Docker CI | success |

## 热更新同步范围

必须同步：

```text
core/
scripts/
static/
launcher/
harness_modules/
deploy/docker/
docs/operations/
region_policy.json
client_version.json
```

禁止同步：

```text
.env
users.db
data/
node_identity.json
node_signing.key
WireGuard 私钥
平台 Cookie/Token
```

## 验证命令

```bash
# 深圳
curl -fsS http://127.0.0.1:8001/version

# 香港 → 深圳
curl -fsS http://127.0.0.1:18003/version

# 深圳 → 香港
curl -fsS http://172.17.0.1:18002/version

# 生产库
docker exec docker_sases_1 python -c "import sqlite3;c=sqlite3.connect('/data/users.db');print(c.execute('PRAGMA integrity_check').fetchone()[0])"
```
