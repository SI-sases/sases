import subprocess
import os

# 直接写死 Git 的绝对路径，绕过环境变量问题
git = r"C:\Program Files\Git\bin\git.exe"

print("1. 初始化全新的 Git 仓库...")
subprocess.run([git, "init"])

print("2. 关联远程 GitHub 仓库...")
subprocess.run([git, "remote", "add", "origin", "https://github.com/SI-sases/sases.git"])

print("3. 暂存所有干净代码（已通过 .gitignore 过滤大文件）...")
subprocess.run([git, "add", "."])

print("4. 提交...")
subprocess.run([git, "commit", "-m", "feat: 全新干净的仓库，包含所有合规文件和安全守则"])

print("5. 强制推送到 GitHub（因为是纯净源码，这次绝对秒传）...")
subprocess.run([git, "push", "-f", "-u", "origin", "main"])

print("✅ 大功告成！仓库已彻底重置！")
