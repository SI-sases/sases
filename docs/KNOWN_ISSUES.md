# SASES 已知问题清单

## 问题 1：指挥员幻觉不存在的工具
- 首次出现：run 383（2026-10-16）
- 现象：指挥员生成 file_write 步骤，但系统无此工具
- 影响：首次执行失败，需重拆
- 临时缓解：重拆机制自动修复
- 根因：提示词未强调"创建文件用 file_patch + create_if_missing"
- 状态：待修复（生成层，可通过 prompt 优化）

## 问题 2：precheck warning 不阻止执行
- 首次出现：run 383（2026-10-16）
- 现象：precheck 输出 "position 非法 replace"，但执行器仍执行
- 影响：侥幸成功，但语义混乱
- 根因：precheck warning 未升级为 error
- 状态：待修复（代码层，需人工）

## 问题 3：position 非法值被容忍
- 首次出现：run 383（2026-10-16）
- 现象：position: "replace" 被当作 create 模式处理
- 影响：语义模糊，未来可能出 bug
- 根因：file_patch 对 position 校验宽松
- 状态：待修复（代码层，需人工）

## 修复优先级
1. 问题 2（最高，因为影响所有 precheck）
2. 问题 1（中，影响首次成功率）
3. 问题 3（低，当前无实际影响）


## 2026-10-18：openGroupRedPacket 补拆永久放弃

**背景**：尝试用 delete_block dry_run + answer + file_patch 补拆 openGroupRedPacket 到 group_redpacket_ui.js。

**失败原因**：三者无法正确使用嵌套占位符链。正确链路是：
1. dry_run 返回 {ok, block, ...}
2. answer({{step1.block}}) → 返回 {success, answer, length}
3. file_patch(new_content={{step2.answer}}) → 才是纯函数代码

三者一直用 {{step2}}（完整 JSON）或手动复制，从未正确用 {{step2.answer}}。

**结论**：openGroupRedPacket 保留在主文件，不再尝试拆分。功能正常，只是和 openGroupRedPacketDialog 分散在两个文件。

**相关 tag**：v0.46.0（恢复点）
