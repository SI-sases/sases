import os
import shutil
from datetime import datetime

FP = "static/css/chat.css"
backup_dir = ".backups"
os.makedirs(backup_dir, exist_ok=True)
ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
backup = os.path.join(backup_dir, f"static__css__chat.css.{ts}.bak")
shutil.copy2(FP, backup)
print(f"备份: {backup}")

with open(FP, 'r', encoding='utf-8') as f:
    c = f.read()

# 在 .chat-input-area 前插入 param-bar 样式
anchor = "/* ===== 输入区 ===== */"

css_block = '''/* ===== 参数胶囊栏（v0.37.0） ===== */
.param-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px var(--space-sm) 4px;
  background: var(--bg-card);
  flex-wrap: wrap;
  flex-shrink: 0;
}

.param-pill {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 3px 9px;
  font-size: 12px;
  color: var(--text-secondary, #666);
  background: var(--bg-input);
  border-radius: 10px;
  cursor: pointer;
  user-select: none;
  transition: background 0.15s;
  white-space: nowrap;
}

.param-pill:hover {
  background: var(--bg-hover, #eaeaea);
}

.param-pill.param-modified {
  color: var(--color-primary);
  background: #e8f2ff;
}

.param-pill.param-unlimited {
  color: #ff9500;
  background: #fff4e5;
}

/* 参数选择面板 */
.param-menu {
  position: fixed;
  z-index: 3000;
  background: var(--bg-card, #fff);
  border: 0.5px solid var(--border-base, #ddd);
  border-radius: var(--radius-md, 8px);
  box-shadow: 0 4px 16px rgba(0,0,0,0.12);
  min-width: 110px;
  padding: 4px 0;
  display: none;
}

.param-menu.show {
  display: block;
}

.param-menu-item {
  padding: 9px 16px;
  font-size: 13px;
  cursor: pointer;
  color: var(--text-primary, #333);
}

.param-menu-item:hover {
  background: var(--bg-hover, #f5f5f5);
}

.param-menu-item.active {
  color: var(--color-primary);
  font-weight: 500;
}

.param-menu-item .param-desc {
  display: block;
  font-size: 11px;
  color: var(--text-secondary, #999);
  margin-top: 2px;
}

'''

if '.param-pill' not in c:
    if anchor in c:
        c = c.replace(anchor, css_block + anchor, 1)
        print("已插入 param-bar 样式")
    else:
        print("警告：找不到输入区锚点")
        raise SystemExit(1)
else:
    print("已存在 param-pill 样式，跳过")

with open(FP, 'w', encoding='utf-8') as f:
    f.write(c)
print(f"已写入，大小 {os.path.getsize(FP)} 字节")

print("\n完成！")
print("下一步：给 chat.js 加交互逻辑")