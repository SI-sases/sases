# scripts/patch_anchor.py
p = 'harness_modules/file_patch/main.py'
c = open(p, encoding='utf-8').read()

old = '''    new_text = "\\n".join(lines)
    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(new_text)

    return {'''

new = '''    new_text = "\\n".join(lines)
    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(new_text)

    # v2.9.1: 写后读回校验
    with open(abs_path, "r", encoding="utf-8") as f:
        _chk = f.read()
    if _chk != new_text:
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(original)
        raise ValueError(f"写入校验失败：{safe_path} 实际写入内容与预期不符（可能被截断），已自动回滚。")

    return {'''

if old not in c:
    print('FAIL: 找不到要替换的代码块')
else:
    c = c.replace(old, new)
    open(p, 'w', encoding='utf-8').write(c)
    print('OK: _mode_anchor 写后校验已添加')
