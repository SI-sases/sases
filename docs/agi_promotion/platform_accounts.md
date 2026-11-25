# 平台账号与主页资料清单

用于本地 SASES 统一发布执行。只记录公开主页信息，不记录密码、Cookie、Token。

## 已确认

### 小红书

- 账号名：sases
- 小红书号：xht20201028
- 主页：https://www.xiaohongshu.com/user/profile/63eafd940000000026005a6a
- 粉丝：277
- 获赞与收藏：992
- IP 属地：美国
- 已发布笔记：云服务器部署属于自己的AGI（已通过审核，公开）
- 置顶评论建议：GitHub 搜索 SI-sases/sases

### GitHub

- 账号：SI-sases
- 仓库：https://github.com/SI-sases/sases
- Release：https://github.com/SI-sases/sases/releases/tag/v1.0.0
- 源码资产：https://github.com/SI-sases/sases/releases/download/v1.0.0/sases-v1.0.0-source.tar.gz

### Blogger

- 博客名：sases云端服务器部署agi
- 已发布：Deploy Your Own AGI on a Cloud Server
- 主页 URL：待从 Blogger 后台“查看博客”复制
- 账号：Google / SI-sases

### gitcn.org

- 论坛：https://forum.github-zh.cn
- 账号：SI-sases（GitHub OAuth）
- 已提交：SASES v1.0.0：在云服务器上部署自己的 AGI
- 状态：待版主审批
- 分类：常规

### X / Twitter

- 账号：@i88033
- 已发布：Deploy Your Own AGI on a Cloud Server
- 短链：https://t.co/p6hLl3W3ul

## 待补齐

### 抖音

- 创作者中心：https://creator.douyin.com/creator-micro/content/upload?enter_from=dou_web
- 当前状态：打开后跳回抖音首页，未进入上传页
- 需要：账号名、抖音号、主页 URL、粉丝数、可发布形式（视频/图文）

### Medium

- 编辑器：https://medium.com/new-story
- 当前状态：跳转登录页
- 需要：登录后记录账号名、主页 URL、关注者数

### LinkedIn

- 发布入口：https://www.linkedin.com/feed/
- 当前状态：未登录
- 需要：登录后记录个人/公司主页 URL

## 统一登记格式

```json
{
  "platform": "xiaohongshu",
  "account_name": "sases",
  "account_id": "xht20201028",
  "profile_url": "https://www.xiaohongshu.com/user/profile/63eafd940000000026005a6a",
  "followers": 277,
  "status": "logged_in",
  "can_post": true,
  "supports_links": false,
  "fallback_text": "GitHub 搜索 SI-sases/sases"
}
```

## 发布规则

- 支持链接：X、Blogger、Medium、LinkedIn、gitcn
- 不支持可点击链接：小红书、抖音
- 不支持链接的平台统一写：

```text
GitHub 搜索：SI-sases/sases
Release：v1.0.0
文档：docs/self-hosting.md
```

## 本地 SASES 采集方式

1. 使用已登录的 Edge/Chromium 用户目录。
2. 打开各平台主页。
3. 读取账号名、账号 ID、主页 URL、粉丝数。
4. 截图保存到 `data/platform_profiles/<platform>/`。
5. 写入本清单，不保存密码/Cookie。
