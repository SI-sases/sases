# 云服务器浏览器能力

## 结论

```text
可以。
云服务器可以运行无头 Chromium，打开网页、截图、填表、点击、抓取内容。
```

已在深圳 node-A 实测：

```text
镜像：sases-browser:test
大小：约 2 GB
Chromium：Playwright Chromium 159
```

## 构建

```bash
cd deploy/browser
docker build \
  --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
  -t sases-browser:test .
```

## 运行

```bash
docker run --rm --shm-size=512m \
  -v "$PWD/scripts/cloud_browser_test.py:/test.py" \
  sases-browser:test python /test.py
```

## 实测结果

```text
https://example.com
  title: Example Domain
  status: 200

https://www.xiaohongshu.com/
  final_url: https://www.xiaohongshu.com/explore
  title: 小红书 - 你的生活兴趣社区
  status: 200
```

抖音首页在无头浏览器中返回 `ERR_ABORTED`，需要单独适配或走 API/客户端。

## 能力

```text
[✓] 打开网页
[✓] 截图
[✓] 点击
[✓] 表单填写
[✓] 读取 DOM/文本
[✓] 执行 JavaScript
[✓] 下载文件
[✓] 定时任务里调用
```

## 限制

```text
1. 无头浏览器是全新会话，不带本地 Edge 登录态。
2. 平台登录需要 Cookie、storage_state 或扫码一次。
3. 深圳服务器 1.7 GB 内存，只建议单页面/低并发。
4. 抖音、TikTok 等有风控，无头浏览器可能被拦截。
5. 浏览器镜像约 2 GB，磁盘要留足。
```

## 与本地 SASES 的关系

```text
本地 SASES：有用户登录态、可操作平台
深圳浏览器容器：可做公网页面检查、抓取、截图、无登录任务
杭州/香港：可按区域部署
```

后续可以把 `sases-browser` 作为深圳 HQ 的网页执行器：

```text
HQ 下发 web.open / web.screenshot / web.extract 任务
→ 浏览器容器执行
→ 回传结果
```

不要把平台密码、Cookie 提交到 Git。
