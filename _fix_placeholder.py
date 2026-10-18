# _fix_placeholder.py
# 给 executor_service.py 加 {{stepN.field}} 字段提取支持
p = 'core/services/executor_service.py'
c = open(p, encoding='utf-8').read()

# 改动 1：replace_match 内部加字段提取
old1 = '''    def replace_match(match):
        step_num = int(match.group(1))
        if step_num in previous_outputs:'''

new1 = '''    def replace_match(match):
        step_num = int(match.group(1))
        field = match.group(2) if match.re.groups >= 2 else None
        if field and step_num in previous_outputs:
            try:
                import json as _json_ph
                _raw = previous_outputs[step_num]
                data = _json_ph.loads(_raw) if isinstance(_raw, str) else _raw
                if isinstance(data, dict) and field in data:
                    return str(data[field])
            except Exception:
                pass
            return match.group(0)
        if step_num in previous_outputs:'''

assert old1 in c, 'old1 未匹配'
c = c.replace(old1, new1, 1)

# 改动 2：双花括号正则
old2 = r"re.sub(r'\{\{step(\d+)\}\}'"
new2 = r"re.sub(r'\{\{step(\d+)(?:\.([A-Za-z_][A-Za-z0-9_]*))?\}\}'"
assert old2 in c, 'old2 未匹配'
c = c.replace(old2, new2, 1)

# 改动 3：单花括号正则
old3 = r"re.sub(r'\{step(\d+)\}'"
new3 = r"re.sub(r'\{step(\d+)(?:\.([A-Za-z_][A-Za-z0-9_]*))?\}'"
assert old3 in c, 'old3 未匹配'
c = c.replace(old3, new3, 1)

open(p, 'w', encoding='utf-8').write(c)
print('替换完成')

# 验证
import ast
ast.parse(open(p, encoding='utf-8').read())
print('语法 OK')

c2 = open(p, encoding='utf-8').read()
print('field 变量:', '✅' if 'field = match.group(2)' in c2 else '❌')
print('字段正则:', '✅' if r'(?:\.([A-Za-z_][A-Za-z0-9_]*))?' in c2 else '❌')
