p = 'launcher/ui/main_window.py'
with open(p, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("=== L400 - L415 ===")
for i in range(399, 415):
    if i < len(lines):
        print(f"{i+1} | {lines[i].rstrip()}")