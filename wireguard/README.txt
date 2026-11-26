把 WireGuard 安装包放在本目录：

  wireguard-installer.exe
  或 wireguard-amd64-*.msi

启动器激活 CDK 后会自动检测：
- 已安装：直接导入隧道配置
- 未安装：使用本目录安装包静默安装

自动通道：
- 启动器生成客户端密钥
- 向 /node/tunnel/config 请求节点专属参数
- 写入 wireguard/wg0.conf
- 导入 WireGuard 隧道

如果已有手写 wg0.conf，启动器会优先使用本地文件。

注意：安装驱动需要管理员权限。
