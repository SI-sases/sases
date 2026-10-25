"""一键生成所有文档"""
import subprocess
import os

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

scripts = [
    'scripts/gen_db_doc.py',
    'scripts/gen_api_doc.py',
    'scripts/gen_health_doc.py',
]

for s in scripts:
    print(f'\n=== 运行 {s} ===')
    r = subprocess.run(['python', s], capture_output=True)
    # Windows 中文系统输出是 GBK
    try:
        out = r.stdout.decode('utf-8', errors='ignore')
    except Exception:
        out = r.stdout.decode('gbk', errors='ignore')
    print(out[-500:] if out else '')
    if r.returncode != 0:
        print(f'[失败] {s}')
        err = r.stderr.decode('utf-8', errors='ignore')
        print(err[:500])

print('\n所有文档生成完成')