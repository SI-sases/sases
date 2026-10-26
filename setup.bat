@echo off
echo ==== SASES 环境安装 ====

python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt

echo.
echo ==== 下载本地 Embedding 模型 ====
python download_model.py

echo.
echo ==== 初始化数据库 ====
python core/db.py

echo.
echo ==== 安装完成 ====
echo 请复制 .env.example 为 .env 并填入 API Key
pause