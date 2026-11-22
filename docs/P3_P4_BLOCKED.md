# P3 / P4 能力审计（blocked）

## P3 video_edit

目标：

```text
一个 video_edit 领域入口
项目文件 / JSON job / FFmpeg / MCP
不做截图点时间线
```

本机检查：

```text
ffmpeg  -> None
ffprobe -> None
ffplay  -> None
C:\ffmpeg\bin\ffmpeg.exe           不存在
C:\Program Files\ffmpeg\bin\ffmpeg.exe 不存在
```

MCP / 视频工具仓库：

```text
未配置
```

结论：

```text
blocked
没有新增 video_edit 工具
不写假实现
```

恢复条件：

```text
安装 FFmpeg 或接入视频 MCP
```

---

## P4 cua / 桌面操作

目标：

```text
一个 cua 入口
Windows-MCP / MCP / DSH CUA provider
不从零写原生 Windows 驱动
```

本机检查：

```text
Windows-MCP 未安装
MCP 未配置
DSH CUA provider 未挂载
```

结论：

```text
blocked
没有新增 cua 工具
没有写原生驱动
```

恢复条件：

```text
配置 Windows-MCP 或 DSH CUA provider
```

---

## 结论

```text
P3 = blocked
P4 = blocked
```

SASES 不为“看起来有功能”而新增假工具。
