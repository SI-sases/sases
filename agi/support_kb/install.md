# 安装与启动

## 要求

- Windows 10/11 64 位
- 解压后双击 `SASES启动器.exe`
- 首次启动需要允许防火墙/管理员权限

## 解压后目录

```text
SASES启动器.exe
python-embed\
launcher\
scripts\
core\
static\
wireguard\
```

## 启动失败

1. 确认解压完整，不是直接在压缩包里运行
2. 查看 `logs\` 最新日志
3. 确认 8001 端口未被占用
4. 尝试 `启动控制台.bat` 查看报错

## 不要做

- 不要把 `users.db` 和 `.env` 发给别人
- 不要从非官方来源下载覆盖包
