"""运行 diagnose_libs.py，把输出捕获到 docs/EXECUTION_HEALTH.md"""
import io
import sys
import os
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO)

_buf = io.StringIO()
_orig = sys.stdout
sys.stdout = _buf

try:
    with open('scripts/diagnose_libs.py', encoding='utf-8') as f:
        code = f.read()
    exec(compile(code, 'diagnose_libs.py', 'exec'), {'__name__': '__main__'})
finally:
    sys.stdout = _orig

captured = _buf.getvalue()
ts = datetime.now().strftime('%Y-%m-%d %H:%M')

md_lines = []
md_lines.append('# SASES 执行质量诊断')
md_lines.append('')
md_lines.append('生成时间：' + ts)
md_lines.append('')
md_lines.append('> 本文档由 `scripts/gen_health_doc.py` 自动生成')
md_lines.append('> 运行命令：`python scripts/gen_health_doc.py`')
md_lines.append('> 建议频率：每周一次，或每次功能上线后')
md_lines.append('')
md_lines.append('## 诊断输出')
md_lines.append('')
md_lines.append('```')
md_lines.append(captured)
md_lines.append('```')
md_lines.append('')
md_lines.append('## 如何解读')
md_lines.append('')
md_lines.append('| 指标 | 含义 | 优化方向 |')
md_lines.append('|------|------|---------|')
md_lines.append('| 失败去重比 | 失败命令种类 / 失败总数 | 比值越低，重复失败越多，越值得优化 |')
md_lines.append('| TOP 10 覆盖率 | TOP 10 失败命令占全部失败的比例 | > 50%，说明失败高度集中 |')
md_lines.append('| 安全拒绝次数 | blocked 状态的次数 | 过高说明策略太严 |')
md_lines.append('| 文件不存在 | 查询类失败的常见原因 | 三者应先 dir_tree 确认 |')
md_lines.append('')
md_lines.append('## 后续动作')
md_lines.append('')
md_lines.append('- 若 file_patch 失败率高 → 工具手册补充"锚点技巧"')
md_lines.append('- 若安全拒绝多 → 检查权限设计')
md_lines.append('- 若某类失败突然增多 → 检查近期代码改动')
md_lines.append('')

os.makedirs('docs', exist_ok=True)
with open('docs/EXECUTION_HEALTH.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(md_lines))

print(captured)
print('\n已写入 docs/EXECUTION_HEALTH.md')