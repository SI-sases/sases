import uvicorn
from core.bootstrap import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run("app_full:app", host="0.0.0.0", port=8001)
