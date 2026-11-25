# SASES 发布内容与平台方案

## 统一链接

- GitHub 仓库：https://github.com/SI-sases/sases
- v1.0.0 Release：https://github.com/SI-sases/sases/releases/tag/v1.0.0
- 源码资产：https://github.com/SI-sases/sases/releases/download/v1.0.0/sases-v1.0.0-source.tar.gz
- Docker 部署文档：https://github.com/SI-sases/sases/blob/main/docs/self-hosting.md
- 英文文章：https://github.com/SI-sases/sases/blob/main/docs/deploy-your-own-agi.md

不能放链接的平台，统一使用下面这行，读者可自行搜索：

```text
GitHub 搜索：SI-sases/sases
Release 标签：v1.0.0
部署文档：docs/self-hosting.md
```

---

## 小红书详细方案

### 当前状态

- 标题：云服务器部署属于自己的AGI
- 状态：审核通过，已公开
- 发布时间：2026-11-25 18:58
- 封面：深色卡片，标题 + SASES 自托管实验

### 置顶评论

```text
仓库地址：GitHub 搜索 SI-sases/sases
Release：v1.0.0
部署文档：docs/self-hosting.md
不含任何内部节点和密钥，纯公开自托管方案。
```

### 正文结构

1. 开头：为什么要在自己的云服务器上部署 AGI
2. 准备：Ubuntu + Docker + 模型 Key
3. 三步：clone、配置 .env、docker compose up
4. 验证：/version、注册登录、重启数据还在
5. 结尾：仓库地址用文字给出，不放外链

### 标题备选

- 云服务器部署属于自己的AGI
- 用 Docker 在云服务器跑一套自己的 AGI
- 不依赖平台：自托管 AGI 部署实录

### 标签

```text
#AGI #SASES #云服务器 #Docker #自托管 #AI工具 #独立开发
```

### 发布节奏

- D0：主笔记（已完成）
- D1：评论区补充“常见问题”
- D2：发第二篇“Docker 部署踩坑”
- D7：发“v1.0.0 Release 更新”
- 每周：一条部署/使用场景

### 数据观察

- 收藏率优先于点赞
- 评论里问“怎么部署”的，统一回复仓库地址
- 不在正文写服务器 IP、密钥、内部拓扑

---

## 抖音图文/视频文案

抖音不放外链，用文字给出仓库。

### 标题

```text
在云服务器上部署一套自己的 AGI
```

### 文案

```text
这次在干净的 Ubuntu 云服务器上，用 Docker 跑通了一套自己的 AGI 服务。

三步：
1. 准备 Ubuntu + Docker
2. 拉取 SASES 仓库
3. docker compose up

验证了 /version、注册登录、重启后数据还在。

仓库：GitHub 搜索 SI-sases/sases
Release：v1.0.0
文档：docs/self-hosting.md

#AGI #SASES #云服务器 #Docker #自托管
```

### 画面

- 封面：`D:\xhs_agi_cover.png`
- 第二张：终端 `docker compose up`
- 第三张：`/version` 返回
- 第四张：仓库地址文字

---

## Medium 文章

标题：

```text
Deploy Your Own AGI on a Cloud Server
```

正文：

```text
SASES is a self-hosted, privacy-first AI system. This guide shows how to run your own AGI-style assistant on a Linux cloud server with Docker, HTTPS, and a model API key.

What you need: Ubuntu 22.04 or 24.04, 2 vCPU and 4 GB RAM, 20 GB disk, a domain, and a model API key.

Quick start:

git clone https://github.com/SI-sases/sases.git
cd sases/deploy/docker
cp .env.example .env
docker compose up -d --build

The service listens on 127.0.0.1:8001. Put HTTPS in front with Caddy or Nginx.

Create the first account, configure the model key, and verify /version.

Back up data/ and .env before upgrading. Never commit keys or databases.

Full guide: https://github.com/SI-sases/sases/blob/main/docs/deploy-your-own-agi.md
Release: https://github.com/SI-sases/sases/releases/tag/v1.0.0
```

Tags:

```text
AGI, Self-Hosted, Docker, AI, Cloud
```

---

## LinkedIn 文案

```text
We just open-sourced SASES v1.0.0: a self-hosted, privacy-first AGI system.

It runs on a clean Ubuntu server with Docker Compose, keeps the database and model key under your control, and ships with a deployment guide and a source release.

Repo: https://github.com/SI-sases/sases
Release: https://github.com/SI-sases/sases/releases/tag/v1.0.0

#AGI #SelfHosted #Docker #AI
```

---

## 已发布记录

- X / Twitter：已发布
- 小红书：审核通过，已公开
- Blogger：已发布
- gitcn.org：已提交，待版主审批
- GitHub v1.0.0 Release：已发布，含源码资产
- 抖音：待登录创作者中心后发布
- Medium：待登录后发布
- LinkedIn：待登录后发布
