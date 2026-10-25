# core/api_routes/knowledge_routes.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from ..auth_service import SECRET_KEY
from ..services import knowledge_service

router = APIRouter(prefix="/knowledge", tags=["knowledge"])
security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload.get("sub"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.get("/my-docs")
async def list_my_docs(user_id: int = Depends(get_current_user)):
    from ..services import project_service
    docs = project_service.list_user_documents(user_id)
    return {"documents": docs}


@router.get("/my-docs/{source_file:path}")
async def get_my_doc(source_file: str, user_id: int = Depends(get_current_user)):
    from ..services import project_service
    doc = project_service.get_user_document(user_id, source_file)
    if not doc:
        raise HTTPException(status_code=404, detail="not found")
    return doc


@router.delete("/my-docs/{source_file:path}")
async def delete_my_doc(source_file: str, user_id: int = Depends(get_current_user)):
    from ..services import project_service
    n = project_service.delete_user_document(user_id, source_file)
    if n == 0:
        raise HTTPException(status_code=404, detail="not found")
    return {"status": "deleted", "chunks": n}



@router.get("/list")
async def list_knowledge(user_id: int = Depends(get_current_user)):
    knowledge = knowledge_service.get_user_knowledge(user_id)
    return {"knowledge": knowledge}
