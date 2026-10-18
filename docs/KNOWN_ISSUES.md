# SASES 已知问题清单

## 问题 1：指挥员幻觉不存在的工具

* 首次出现：run 383（2026-10-16）
* 现象：指挥员生成 file\_write 步骤，但系统无此工具
* 影响：首次执行失败，需重拆
* 临时缓解：重拆机制自动修复
* 根因：提示词未强调"创建文件用 file\_patch + create\_if\_missing"
* 状态：待修复（生成层，可通过 prompt 优化）

## 问题 2：precheck warning 不阻止执行

* 首次出现：run 383（2026-10-16）
* 现象：precheck 输出 "position 非法 replace"，但执行器仍执行
* 影响：侥幸成功，但语义混乱
* 根因：precheck warning 未升级为 error
* 状态：待修复（代码层，需人工）

## 问题 3：position 非法值被容忍

* 首次出现：run 383（2026-10-16）
* 现象：position: "replace" 被当作 create 模式处理
* 影响：语义模糊，未来可能出 bug
* 根因：file\_patch 对 position 校验宽松
* 状态：待修复（代码层，需人工）

## 修复优先级

1. 问题 2（最高，因为影响所有 precheck）
2. 问题 1（中，影响首次成功率）
3. 问题 3（低，当前无实际影响）



## 2026-10-18：openGroupRedPacket 补拆永久放弃

**背景**：尝试用 delete\_block dry\_run + answer + file\_patch 补拆 openGroupRedPacket 到 group\_redpacket\_ui.js。

**失败原因**：三者无法正确使用嵌套占位符链。正确链路是：

1. dry\_run 返回 {ok, block, ...}
2. answer({{step1.block}}) → 返回 {success, answer, length}
3. file\_patch(new\_content={{step2.answer}}) → 才是纯函数代码

三者一直用 {{step2}}（完整 JSON）或手动复制，从未正确用 {{step2.answer}}。

**结论**：openGroupRedPacket 保留在主文件，不再尝试拆分。功能正常，只是和 openGroupRedPacketDialog 分散在两个文件。

**相关 tag**：v0.46.0（恢复点）



## 2026-10-18 v0.47.0 修复项

1. **split\_block 自动补 window. 前缀**：拆分时扫描主文件函数名，切片里的裸调用自动加 window. 前缀。用户不再遇到拆分后“点了没反应”。
2. **decider 移除高误报词**：从 \_suspicious\_kws 移除“下一步”“未做”“待做”，LLM prompt 同步移除“下一步”。减少误判导致的空转。
3. **answer 完成信号快速判定**：answer 含“已完成/已迁移/语法通过”等信号 + 有成功工具 + 无失败步骤 → 直接判完成，不再看可疑词。



1. \## 问题 4：ENABLE\_xxx 开关在代码里不存在
2. 
3. 首次发现：2026-10-18（L1 上服务器前检查）
4. 现象：扫描 220 个文件，未找到 ENABLE\_GAME / ENABLE\_PATTERN\_SYNC / ENABLE\_KB\_SYNC / ENABLE\_CROSS\_NODE\_CREDIT 的读取逻辑
5. 影响：L1 阶段无法通过 .env 关闭游戏、知识库同步、冲突检测、跨节点积分，后台定时任务会继续跑，烧 API、写库、污染日志
6. 根因：这四个开关只写在文档和 .env 示例里，代码从未实现
7. 状态：待修复（在 l1-server 分支处理，不在 main 上动）
8. 
9. 处理位置（l1-server 分支）：
10. \- 游戏模块：bootstrap.py 里 yunchong\_routes / pet\_routes / base\_routes 的注册
11. \- 知识库同步：hive 相关的 knowledge 广播
12. \- 冲突检测：periodic\_hlc\_health 定时任务
13. \- 跨节点积分：credit\_anchor 定时任务


14. \## 问题 5：verify\_ui 缺 playwright 依赖
15. 
16. 现象：干净环境启动报 `Failed to load module verify\_ui: No module named 'playwright'`
17. 影响：三者调用 verify\_ui 时失败，其他工具正常
18. 根因：harness\_modules/verify\_ui/ 存在，但 playwright 不在 requirements.txt
19. 状态：待处理（L1 阶段建议移除该工具，或加 try/except 优雅降级）
20. 
21. \## 问题 6：bge-small-zh-onnx 模型目录缺失
22. 
23. 现象：干净环境启动报 `模型加载失败: 模型目录不存在: ./bge-small-zh-onnx`
24. 影响：embedding 降级为关键词匹配，检索精度下降，功能不崩
25. 根因：模型目录约 90MB，未进 git
26. 状态：待处理（打包 portable 时复制进去，或配置 DashScope API Key 替代）


27. \## 问题 7：测试环境共享 localStorage 导致外键失败
28. 
29. 现象：sases-clean 在 8001 启动，浏览器复用主环境的 token，发消息报 `FOREIGN KEY constraint failed`，因为新库 users 表为空。
30. 影响：同一端口跑多个实例时，浏览器缓存互相污染。
31. 根因：token 存在 localStorage，同源同端口共享。
32. 处理：
33. \- 测试时用无痕窗口，或清 localStorage
34. \- 或 sases-clean 用 8011 端口（`set SASES\_PORT=8011`）
35. \- 广州那台如果是新机器，不会有此问题；但如果他之前打开过主环境，也会有。
36. 状态：已知，非代码 bug，测试方法规避。


37. \## 问题 8：干净环境 HLC 字段缺失
38. 
39. 现象：sases-clean 启动后，发消息日志出现 `\[hlc] write\_hlc 附加失败: no such column: hlc\_ts`，`hlc-health` 脚本报错。
40. 影响：HLC 相关功能（冲突检测、读己之写）不工作，核心消息收发不受影响。
41. 根因：B2 地基的 `hlc\_ts` / `origin\_node` / `shard\_key` 字段是通过迁移脚本加的，`core/db.py` 的 `init\_db()` 里没有。
42. 状态：待修复（l1-server 分支，或在 db.py 里补字段）


43. \## 问题 9：干净环境首次发消息时 assistant 不存在
44. 
45. 现象：sases-clean 注册新用户后直接发消息，前端报“找不到绑定的智能体模型”，后端日志 `agent\_id='sases\_assistant\_1'`，但 `model\_configs` 表为空。
46. 影响：新用户首次使用必须先点“智能体” tab 触发自动创建，否则发消息失败。
47. 根因：`agent\_service.py` 在 `list\_my\_agents` 时创建 assistant，但 `send\_message` 没有兜底创建。
48. 状态：待修复（可在 send\_message 里加兜底，或前端登录后自动调一次 agents/list）


49. \## 问题 9：干净环境首次发消息时 assistant 不存在
50. 
51. 现象：sases-clean 注册新用户后直接发消息，前端报“找不到绑定的智能体模型”，`model\_configs` 表为空。
52. 影响：新用户首次使用必须先访问“智能体”列表触发自动创建，或在发消息前手动插入。
53. 根因：`agent\_service.py` 在 `list\_my\_agents` 时创建 `sases\_assistant\_{user\_id}`，但 `send\_message` 没有兜底创建。
54. 临时处理：手动插入 `sases\_assistant\_{user\_id}`。
55. 正式修复（l1-server 分支）：在 `send\_message` 开头加兜底，或登录成功后自动调一次 `list\_my\_agents`。
56. 状态：待修复。


57. \## 问题 10：Windows WebSocket 断开时报 ConnectionResetError
58. 
59. 现象：浏览器刷新或关闭标签页时，后端日志出现 `ConnectionResetError: \[WinError 10054]`。
60. 影响：不影响功能，前端自动重连，但日志刷屏。
61. 根因：Windows asyncio 的 ProactorEventLoop 在连接被强制关闭时，清理逻辑抛异常。
62. 状态：待处理（l1-server 阶段加 try/except，或切换 SelectorEventLoop）


63. \## 问题 12：干净环境手动插入的 assistant 字段不全，导致 NoneType.lower() 崩溃
64. 
65. 现象：手动插入 sases\_assistant\_1 后发消息，返回 `模型调用失败：'NoneType' object has no attribute 'lower'`。
66. 影响：即使 API Key 有效，也无法调用模型。
67. 根因：手动 INSERT 只填了 id/user\_id/name/model\_type，缺少 provider/model\_name 等字段，代码读取后做 .lower() 时崩溃。
68. 状态：待修复（l1-server 分支，应在创建 assistant 时填全字段；或代码里对 None 做兜底）


69. \## 问题 13：干净环境首次部署需要两个手动步骤
70. 
71. 现象：`git clone` + `python core/db.py` 后，服务能启动，但发消息失败，因为：
72. 1\. `hlc\_ts` 等字段不存在 → 需跑 `migrate\_hlc\_groundwork.py`
73. 2\. `sases\_assistant\_1` 不存在 → 需访问智能体列表或手动插入
74. 
75. 影响：新用户/新服务器首次部署会卡在“发消息报错”。
76. 根因：`init\_db()` 不包含 B2 迁移字段和 assistant 预置。
77. 状态：待修复（l1-server 分支：db.py 加字段 + 登录后自动创建 assistant）


78. \## 问题 14：同一用户多标签页导致 WS 频繁断连
79. 
80. 现象：开多个标签页时，Console 反复出现 `\[user-ws] closed, will reconnect in 3s`，服务端日志有 `ConnectionResetError: \[WinError 10054]`。
81. 影响：前端自动重连，功能不阻塞，但消息实时性延迟约 3 秒。
82. 根因：ws\_hub 对同一 user\_id 只保留一个连接，新连接覆盖旧连接；旧连接被关闭时 Windows asyncio 抛异常。
83. 状态：待处理（l1-server 阶段：ws\_hub 支持同一用户多连接，或前端限制单标签页连接）

## 问题 16：多实例同时跑时 periodic\_git\_push 会争抢推送
84. 
85. 现象：主环境和 sases-clean 都跑 run\_forever.py，每小时都 `git push origin main`，可能互相覆盖。
86. 影响：git 历史混乱，或推送失败刷日志。
87. 根因：periodic\_git\_push 没有判断“当前实例是否应该推送”。
88. 状态：待处理（l1-server 阶段加 ENABLE\_GIT\_PUSH 开关，默认只在主节点开）

