with open('harness_modules/run_python/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i, line in enumerate(lines):
        if 'exec' in line or 'subprocess' in line or 'open(' in line or 'write' in line:
            print(f"{i+1} | {line.rstrip()}")