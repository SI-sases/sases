from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/users", tags=["users"])

_USERS = {
    1: {"id": 1, "username": "alice", "display_name": "Alice", "bio": "Hello, I am Alice.", "avatar_url": "https://example.com/avatars/alice.png"},
    2: {"id": 2, "username": "bob", "display_name": "Bob", "bio": "Bob's public profile.", "avatar_url": "https://example.com/avatars/bob.png"},
}


def _public_card(user):
    return {
        "id": user["id"],
        "username": user["username"],
        "display_name": user["display_name"],
        "bio": user["bio"],
        "avatar_url": user["avatar_url"],
    }


@router.get("/{user_id}/card")
def get_user_card(user_id: int):
    user = _USERS.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _public_card(user)


@router.get("/{user_id}")
def get_user_public_info(user_id: int):
    user = _USERS.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _public_card(user)
