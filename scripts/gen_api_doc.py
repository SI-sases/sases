"""扫描 core/api_routes/*.py，生成 docs/API_INDEX.md"""
import os
import re

ROUTES_DIR = 'core/api_routes'
OUT = 'docs/API_INDEX.md'


def parse_routes(filepath):
    """解析一个路由文件的 @router.xxx 装饰器"""
    with open(filepath, encoding='utf-8') as f:
        lines = f.readlines()

    routes = []
    prefix = ''
    current_router = ''

    for i, line in enumerate(lines):
        # 提取 router 前缀
        m = re.search(r'APIRouter\(prefix="([^"]*)"', line)
        if m:
            prefix = m.group(1)

        # 提取 @router.xxx("path")
        m = re.search(r'@(\w+)\.(get|post|put|delete|patch)\("([^"]*)"', line)
        if m:
            router_var = m.group(1)
            method = m.group(2).upper()
            path = m.group(3)
            # 下一行的函数名
            func_name = ''
            if i + 1 < len(lines):
                fm = re.search(r'(?:async\s+)?def\s+(\w+)', lines[i + 1])
                if fm:
                    func_name = fm.group(1)
            # 尝试找 docstring
            doc = ''
            for j in range(i + 2, min(i + 8, len(lines))):
                if '"""' in lines[j]:
                    doc = lines[j].strip().strip('"""').strip()
                    break
            routes.append({
                'method': method,
                'path': prefix + path if not path.startswith('/') else prefix + path,
                'func': func_name,
                'doc': doc
            })
    return routes


def main():
    if not os.path.isdir(ROUTES_DIR):
        print(f'目录不存在: {ROUTES_DIR}')
        return

    files = sorted([f for f in os.listdir(ROUTES_DIR) if f.endswith('.py') and f != '__init__.py'])

    md_lines = []
    md_lines.append('# SASES API 接口清单\n')
    md_lines.append(f'共 {len(files)} 个路由文件\n')

    total_routes = 0
    for fname in files:
        filepath = os.path.join(ROUTES_DIR, fname)
        routes = parse_routes(filepath)
        if not routes:
            continue
        total_routes += len(routes)
        md_lines.append(f'\n## {fname} ({len(routes)} 个接口)\n')
        md_lines.append('| 方法 | 路径 | 函数 | 说明 |\n')
        md_lines.append('|------|------|------|------|\n')
        for r in routes:
            doc = r['doc'].replace('|', '/') if r['doc'] else ''
            md_lines.append(f"| {r['method']} | `{r['path']}` | {r['func']} | {doc} |\n")

    md_lines.insert(2, f'共 {total_routes} 个接口\n')

    os.makedirs('docs', exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        f.writelines(md_lines)

    print(f'生成 {OUT}')
    print(f'共 {len(files)} 个文件，{total_routes} 个接口')


if __name__ == '__main__':
    main()