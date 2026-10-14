\# SASES 项目上下文交接



\## 当前状态

\- 项目阶段：功能整合与体验优化

\- 已完成：核心三架构（种子/阿波罗/根脉络）、积分体系、群聊、交易市场、国际化（主要界面）

\- 当前执行：修复关键缺陷阶段

\- 下一步：修复红包领取、智能体左滑真实接入、XSS 防护



\## 最近完成

\- 前端模块化重构：拆分 main.js、me.js、chat.js 为独立模块

\- 后端服务层与路由层分离

\- 消息分页加载与轮询

\- 长按菜单（引用/帮我回复）

\- 国际化框架与核心界面覆盖



\## 当前问题

\- 红包领取未完全实现（前后端只有基础，未完成领取闭环）

\- 智能体左滑删除/共享仍为模拟操作

\- 部分消息使用 innerHTML，存在 XSS 风险

\- 中英文覆盖尚未全覆盖，部分硬编码中文



\## 关键文件

\- 后端入口：app\_full.py

\- 应用工厂：core/bootstrap.py

\- 数据库初始化：core/db.py

\- 服务层：core/services/

\- 路由层：core/api\_routes/

\- 前端入口：static/index.html

\- 前端模块：static/modules/

&#x20; - main.js（导航、登录、二级页面控制）

&#x20; - me.js 及拆出的 me\_profile.js、model\_management.js、wallet.js、knowledge.js、contributions.js、settings.js

&#x20; - chat.js（含分页、轮询、长按、引用）

&#x20; - group\_chat.js（群聊）

&#x20; - contacts.js（智能体列表，含左滑、搜索、拼音分组）

&#x20; - messages.js（会话列表）

&#x20; - api.js（统一 API 客户端）

&#x20; - i18n.js（国际化字典）



\## 常用命令

\- 启动服务：`python -m uvicorn app\_full:app --reload --port 8001`

\- 运行测试：`python -m pytest tests/ -v`



\## 技术栈

\- 后端：FastAPI + SQLite

\- 前端：原生 ES Modules（无构建工具）

\- 认证：JWT

\- 通信：REST API + 简单轮询（5秒）

\- 部署：本地单机运行，暂未容器化

