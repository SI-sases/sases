# 可用于测试的工具清单

> 审核员出题时的参考手册。触发 L2 深度审核时，审核员 LLM 会读取本清单。

## 语法测试

### verify_syntax
- **参数**：`file_path`（相对路径）
- **返回值**：`{syntax_ok: bool, errors: [...]}`
- **适用**：任何 `.py` / `.js` 改动后必跑
- **示例**：
{"type": "verify_syntax", "params": {"file_path": "core/services/swarm/reviewer_deep.py"}}

text

## 功能测试

### run_python
- **参数**：`code`（Python 代码字符串，≤5000 字符）
- **返回值**：执行结果或异常
- **适用**：验证具体函数的输入输出
- **示例**：
{"type": "run_python", "params": {"code": "from core.utils.helper import add; assert add(1,2)==3"}}

text

## 输出验证

### file_read
- **参数**：`file_path` + `offset`（可选）+ `max_lines`（可选）
- **返回值**：文件内容
- **适用**：验证改动后的具体行
- **示例**：
{"type": "file_read", "params": {"file_path": "core/xxx.py", "offset": 10, "max_lines": 5}}

text

## 命令测试

### command
- **参数**：`command`（单行命令字符串）
- **返回值**：`{status: success|failed, output, exit_code}`
- **适用**：跑已有测试文件、跑 linter
- **示例**：
{"type": "command", "params": {"command": "python -m pytest tests/test_xxx.py -v"}}

text

## 出题原则（审核员 LLM 必读）

1. **改了 .py → 必跑 verify_syntax**
2. **改了具体函数 → 必跑一个 assert 验证该函数**
3. **有对应测试文件 → 必跑该测试文件**
4. **无法验证的改动（如改注释）→ 输出空数组 `[]`**
5. **最多 3 步**：超过 3 步说明改动太大，应退回指挥员重拆
6. **不要假设环境里有不存在的测试文件**
