# -*- coding: utf-8 -*-
"""C1: 给 COMMANDER_SYSTEM_PROMPT 追加 plan 和 answer 三段式铁律"""
F = "core/services/swarm/prompts.py"
c = open(F, encoding="utf-8").read()

MARK = "【plan 输出格式铁律（v2，必读）】"
if MARK in c:
    print("[SKIP] 已存在")
    exit(0)

# 追加内容：放在 COMMANDER_SYSTEM_PROMPT 的 """ 结束符之前
NEW_RULES = """

【plan 输出格式铁律（v2，必读）】
当你的 plan 生成 steps 后，必须额外输出 human_summary 字段（给用户看的人话版）。
human_summary 严格三段式：

【分析】
- 用户要什么（1 句话）
- 你查到了什么（带 file:line，如 core/services/model_service.py:67）
- 风险点（改了会影响什么）

【方案】
- 分几步，每步一句话（不要贴 JSON）
- 影响文件数

【建议】
- 先做哪步 + 为什么
- 做完怎么验证（如"刷新浏览器看 XX 是否出现"）
- 可选下一步

【answer 输出铁律（v2，必读）】
answer 的 content 也必须三段式：【分析】【方案】【建议】。
- 禁止只写"已定位三处现状，下一步..."这类占位
- 【分析】段必须带 file:line
- 【方案】段必须写"下一步用哪个工具改哪个文件的哪一行"
- 【建议】段必须写"用户需要做什么验证"

【反例（禁止输出）】
"已完成侦察，下一步按缺口修复"
"已定位 delete_model / deleteModel / DELETE 路由 / 前端按钮四处实现"
"见上一步读取结果与 grep 结果"
"OK 执行已结束"

【正例（必须这样）】
【分析】
- core/services/model_service.py:67 的 delete_model 只删 model_configs，没清 messages
- 风险：改这里会级联影响 3 张表

【方案】
- 下一步用 smart_edit 改 model_service.py:67-92，改成先删 messages → 再删 conversations → 最后删 model_configs
- 影响 1 个文件

【建议】
- 你刷新智能体列表，看删除后是否真的消失
- 如果消失，再做第 2 批（统一状态码）
"""

# 找 COMMANDER_SYSTEM_PROMPT 的结束 """（最后一个）
start_marker = 'COMMANDER_SYSTEM_PROMPT = """'
i = c.find(start_marker)
if i < 0:
    print("[ERR] 未找到 COMMANDER_SYSTEM_PROMPT")
    exit(1)
# 找 i 之后的第一个 """（结束符）
j = c.find('"""', i + len(start_marker))
if j < 0:
    print("[ERR] 未找到结束三引号")
    exit(1)

# 插入到 """ 之前
c2 = c[:j] + NEW_RULES + c[j:]
open(F, "w", encoding="utf-8").write(c2)
import ast
ast.parse(c2)
print("[OK] C1 prompt 铁律已追加，语法通过")
print("[INFO] 文件大小:", len(c2))