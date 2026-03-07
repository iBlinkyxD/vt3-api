from fastapi import Depends, HTTPException
from models.user import User
from utils.auth import get_current_user


def require_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    return current_user