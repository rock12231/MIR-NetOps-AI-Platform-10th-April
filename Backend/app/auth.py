from typing import Optional
from fastapi import Security
from fastapi.security import APIKeyHeader

from app.models import User

api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

async def get_current_active_user(authorization: Optional[str] = Security(api_key_header)) -> User:
    if not authorization:
        # Return a default user for unauthenticated requests
        return User(username="anonymous", disabled=False)
    # Mock authentication: accept any non-empty token as valid
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    if token:
        return User(username=f"user_{token[:8]}", disabled=False)
    return User(username="anonymous", disabled=False)