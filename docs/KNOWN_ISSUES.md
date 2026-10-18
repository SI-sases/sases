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


4. \## 问题 4：ENABLE\_xxx 开关在代码里不存在
5. 
6. 首次发现：2026-10-18（L1 上服务器前检查）
7. 现象：扫描 220 个文件，未找到 ENABLE\_GAME / ENABLE\_PATTERN\_SYNC / ENABLE\_KB\_SYNC / ENABLE\_CROSS\_NODE\_CREDIT 的读取逻辑
8. 影响：L1 阶段无法通过 .env 关闭游戏、知识库同步、冲突检测、跨节点积分，后台定时任务会继续跑，烧 API、写库、污染日志
9. 根因：这四个开关只写在文档和 .env 示例里，代码从未实现
10. 状态：待修复（在 l1-server 分支处理，不在 main 上动）
11. 
12. 处理位置（l1-server 分支）：
13. \- 游戏模块：bootstrap.py 里 yunchong\_routes / pet\_routes / base\_routes 的注册
14. \- 知识库同步：hive 相关的 knowledge 广播
15. \- 冲突检测：periodic\_hlc\_health 定时任务
16. \- 跨节点积分：credit\_anchor 定时任务

