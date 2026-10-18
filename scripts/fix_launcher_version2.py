import ast, re

PATH = "launcher/ui/main_window.py"

with open(PATH, encoding="utf-8") as f:
    content = f.read()

# 找到旧的 _load_version_info 方法并替换
old_method_pattern = r"    def _load_version_info\(self\):.*?self\.version_label\.setText\(txt\)\n"
new_method = '''    def _load_version_info(self):
        import json
        import urllib.request
        # 禁用代理，防止访问本地端口被代理软件拦截
        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)
        
        url = f"http://127.0.0.1:{self._chosen_port}/version"
        try:
            req = urllib.request.Request(url)
            with opener.open(req, timeout=3) as r:
                data = json.loads(r.read().decode())
            txt = (
                f"版本：{data.get('commit','?')} ({data.get('branch','?')}) | "
                f"Schema：{data.get('schema','?')} | "
                f"节点：{data.get('node_id','?')} | "
                f"端口：{data.get('port','?')}"
            )
        except Exception as e:
            txt = f"版本：不可用 [URL: {url}] ({e})"
        self.version_label.setText(txt)
'''

content = re.sub(old_method_pattern, new_method, content, flags=re.DOTALL)

with open(PATH, "w", encoding="utf-8") as f:
    f.write(content)

try:
    ast.parse(content)
    print("语法检查通过")
    print("已将 _load_version_info 替换为禁用代理的版本")
except SyntaxError as e:
    print(f"语法错误: {e}")
