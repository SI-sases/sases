@echo off
cd /d C:\Users\xiaomai\sases
call venv312\Scripts\activate
python -m uvicorn app_full:app --reload --port 8001