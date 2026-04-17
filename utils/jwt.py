import os
from dotenv import load_dotenv

from jose import jwt
from datetime import datetime, timedelta

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

def create_access_token(user_id: int, session_version: int = 1):
    expire = datetime.utcnow() + timedelta(hours=24)

    payload = {
        "user_id": user_id,
        "session_version": session_version,
        "exp": expire
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)