# 大文件拆分操作手册

## 标准流程（已验证 3 次）

### 第 1 步：grep 确认两个边界
- 要拆的代码块起始行
- 紧随其后的下一段代码起始行

### 第 2 步：run_python 切片写入
start = 起始行号 - 1
end = 下一段起始行号 - 1
block = '\n'.join(src[start:end])
assert last_non_empty == '};'
assert '下一段特征' not in block
write_file('新文件', block + '\n')

### 第 3 步：主文件加裸 import
import './新文件.js';

### 第 4 步：从后往前删旧代码
delete_block，每次删一个，从最后一个函数开始

### 第 5 步：verify_syntax 两个文件

## 已知陷阱
1. 三者会盲写行号 → 必须 assert 强制检查
2. 末行可能是空行 → 取最后一个非空行判断
3. 从前往后删会行号偏移 → 必须从后往前
4. 不要加 `window.xxx = xxx` 挂载 → 原文已是 `window.xxx = function`
