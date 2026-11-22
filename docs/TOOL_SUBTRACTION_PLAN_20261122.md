# SASES 减法优化执行方案

> 原则：工具做减法，能力做加法；入口做减法，路由做加法。
> 本文件由指挥官维护，SASES 按任务单执行。

---

## 一、审计纠正

SASES 第一版审计按 `harness_modules/` 目录数统计：

```text
35 个目录 / 约 3,154 token
```

实际模型可见工具来自 `harness_runtime.list_tools()`：

```text
23 个
```

目录里有些工具是 extension，本来就不进 schema。  
因此第一版“隐藏 12 个、省 820 token”是高估。

真实情况：

```text
可见 23
实际隐藏 6
省约 382 token
```

隐藏的 6 个：

```text
base64-codec
fake_async
json-formatter
string-utils
text-stats
unit-converter
```

---

## 二、Phase 1 已完成

新增：

```text
core/services/tool_visibility.py
```

- `HIDDEN_DEFAULT`：同时兼容 `_` 和 `-` 两种 id
- `visible(tools)`：只过滤 schema，不删除实现
- `SASES_TOOL_HIDE=off`：一键回退全量

接入：

```text
core/services/agent_loop.py  _tool_schemas()
core/services/fast_agent.py  schema 构建
```

效果：

| 指标 | 改前 | 改后 |
|---|---:|---:|
| 可见工具 | 23 | 17 |
| schema token | 约 2,700 | 约 2,300 |
| 删除实现 | 0 | 0 |
| 回退开关 | — | `SASES_TOOL_HIDE=off` |

SASES 执行时曾误删 `fast_agent.run_fast` 函数头，指挥官已修复。  
这说明减法任务也必须强制 `verify_syntax`，不能只看报告。

---

## 三、Phase 2：继续减 5 个入口

实际执行结果：

```text
runtime 可见 23
实际隐藏 10
剩余 13
schema 2,497 -> 1,471 token
节省 1,026（-41.1%）
```

新增隐藏：

```text
http_async
smart_edit
verify_claim
verify_patch
split_block（磁盘有，runtime 未加载）
```

说明：

- `split_block` 不在 runtime，加入隐藏集合但本轮无实际效果
- 没有为了凑 12 再去隐藏 `web_fetch` / `read_user_doc`，因为它们不可替代
- `verify_patch` 被隐藏后，`fast_agent._READ_TOOLS` 的白名单是冗余，不影响运行

目标从“12 个”修正为：

```text
13 个是当前合理值
12 个只能靠隐藏 web_fetch/read_user_doc，不建议
```


---

## 四、Phase 3：API 不再全量注入

旧文档的 `api_registry` 全量注入方案不再使用。

目标：

```text
api_registry 只做数据库
模型每轮不看全部 API
需要时 search_apis / search_tools 返回 top 5 紧凑名片
```

不要做：

```text
每轮 build_context 读取全部 description + params_schema
```

如果当前已没有全量注入，本阶段只保留表结构，不再新增注入代码。

---

## 五、Phase 4：桌面 UI 只保留一个 cua 工具

参考 DSH CUA：

- 一个 `cua` 工具
- 应用/窗口对象
- 显式 AX tree（maxElements/maxDepth）
- 只对显式窗口截图
- 截图走附件，不返回 base64
- 优先 UIA/AX，截图作兜底

不要注册：

```text
ui_screenshot
ui_click
ui_type
ui_key
ui_scroll
```

这些会让 schema 和动作选择爆炸。

---

## 六、i18n 重跑目标

SASES 第一次用了 20 步，主要因为：

- 逐个 manifest/file_read
- main.js 分 3 段读
- 没有批量 patch
- JS 语法错误没有自动拦截

重跑目标：

```text
Step 1 并行读 3 个 i18n 文件 + grep main 关键块
Step 2 改 i18n.js
Step 3 改 i18n_en.js + main.js
Step 4 verify_syntax 三个文件
Step 5 失败才修
Step 6 最终报告
```

验收：

```text
≤ 8 步
verify_syntax 全绿
中英文 key 278/278
html lang 正确
无中文兜底
```

---

## 七、SASES 执行规则

1. 先审计，再改
2. 一次只做一类减法
3. 不删除实现，只隐藏入口
4. 每个任务必须 `verify_syntax`
5. 超过步数预算就返回失败，不谎报完成
6. 指挥官只做任务单、审查、修复它引入的回归，不替它完成主任务

---

## 八、参考

- [DSH Computer Use](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/computer-use.md)
- [Tarsier AX tree](https://pypi.org/project/tarsier-ai/0.5.1/)
- [Windows-MCP](https://github.com/CursorTouch/Windows-MCP)
- [Microsoft UFO](https://github.com/microsoft/UFO)
- [Agent-S](https://github.com/simular-ai/Agent-S)
- [UI-TARS Desktop](https://github.com/bytedance/UI-TARS-desktop)
- [Kinocut](https://pypi.org/project/kinocut/1.16.1/)
