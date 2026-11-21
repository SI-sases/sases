# tests/ui/README.md
# UI 快照测试（骨架）

只测 5 个关键页，不追求全站。

## 1. 采集

```powershell
python tests/ui/capture.py --base http://127.0.0.1:8001 --out tests/ui/baseline
```

需要登录态的页面，先用测试账号在 `/static/_ui_preview.html` 类页面里写入 token，再截图。
（后续可加 `--token` 自动生成预览页。）

## 2. 对比

```powershell
python tests/ui/compare.py --baseline tests/ui/baseline --current tests/ui/current
```

- 像素差 < 0.5% 通过
- 超阈值输出 `*.diff.png`
- 动态区域（时间/随机 id）用 `--mask x,y,w,h` 排除

## 3. 更新基线

```powershell
python tests/ui/capture.py --out tests/ui/baseline --update
```

更新必须人工 review，并提交到 git。

## 4. 交互快照（优先）

视觉只兜底布局；交互用 DOM + trace 断言：

```python
send("把 README 标题改一下")
wait_for("run_end")
assert progress_card_visible()
assert tool_card_contains("README.md")
assert trace_has("step_done")
```

选择器加 `data-testid`，不要用 nth-child。
