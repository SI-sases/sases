import os, shutil, urllib.request, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_DIR = os.path.join(ROOT, "build_portable")
EMBED_URL = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip"

def build():
    print("1. 清理旧目录...")
    if os.path.exists(BUILD_DIR):
        # 强制清除可能被占用的 .git 目录
        git_dir = os.path.join(BUILD_DIR, ".git")
        if os.path.exists(git_dir):
            import stat
            def on_rm_error(func, path, exc_info):
                os.chmod(path, stat.S_IWRITE)
                func(path)
            shutil.rmtree(git_dir, onerror=on_rm_error)
        try:
            shutil.rmtree(BUILD_DIR)
        except Exception as e:
            print(f"常规删除失败，尝试静默强杀: {e}")
            os.system(f'rmdir /s /q "{BUILD_DIR}"')
    os.makedirs(BUILD_DIR)

    print("2. 下载并解压 Python Embeddable...")
    embed_zip = os.path.join(BUILD_DIR, "python-embed.zip")
    urllib.request.urlretrieve(EMBED_URL, embed_zip)
    with zipfile.ZipFile(embed_zip, 'r') as z:
        z.extractall(os.path.join(BUILD_DIR, "python-embed"))
    os.remove(embed_zip)

    pth_file = os.path.join(BUILD_DIR, "python-embed", "python312._pth")
    if os.path.exists(pth_file):
        with open(pth_file, "a", encoding="utf-8") as f:
            f.write("\nLib\\site-packages\n")

    print("3. 复制项目文件...")
    items_to_copy = ["core", "static", "harness_modules", "launcher", "scripts", "LICENSE", "COMMERCIAL.md", "THIRD_PARTY_LICENSES.md", "app_full.py", "requirements.txt", "LICENSE", "COMMERCIAL.md", "THIRD_PARTY_LICENSES.md"]
    for item in items_to_copy:
        src = os.path.join(ROOT, item)
        if os.path.exists(src):
            if os.path.isdir(src):
                shutil.copytree(src, os.path.join(BUILD_DIR, item))
            else:
                shutil.copy2(src, os.path.join(BUILD_DIR, item))

    print("4. 复制本地依赖包 (venv312/Lib/site-packages)...")
    venv_site = os.path.join(ROOT, "venv312", "Lib", "site-packages")
    embed_site = os.path.join(BUILD_DIR, "python-embed", "Lib", "site-packages")
    os.makedirs(embed_site, exist_ok=True)
    if os.path.exists(venv_site):
        shutil.copytree(venv_site, embed_site, dirs_exist_ok=True)

    print("5. 将打包好的启动器 EXE 复制到根目录...")
    src_exe = os.path.join(ROOT, "launcher", "dist", "SASES启动器.exe")
    if os.path.exists(src_exe):
        shutil.copy2(src_exe, os.path.join(BUILD_DIR, "SASES启动器.exe"))
    else:
        print("⚠️ 警告: 未找到 launcher/dist/SASES启动器.exe，请先运行 build_launcher_exe.py")

    print("6. 生成备用启动脚本...")
    bat_content = "@echo off\nstart python-embed\\pythonw.exe launcher\\launcher.py\n"
    with open(os.path.join(BUILD_DIR, "启动SASES.bat"), "w", encoding="gbk") as f:
        f.write(bat_content)

    print("7. 压缩成 zip...")
    output_zip = os.path.join(ROOT, "static", "downloads", "sases-portable.zip")
    os.makedirs(os.path.dirname(output_zip), exist_ok=True)
    if os.path.exists(output_zip):
        os.remove(output_zip)
    shutil.make_archive(output_zip.replace(".zip", ""), 'zip', BUILD_DIR)
    print(f"✅ 打包成功！文件已保存至: {output_zip}")

if __name__ == "__main__":
    build()
