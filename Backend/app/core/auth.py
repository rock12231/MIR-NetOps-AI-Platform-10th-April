from typing import Optional
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

from app.core.models import User

api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

async def get_current_active_user(authorization: Optional[str] = Security(api_key_header)) -> User:
    """
    Dependency that returns the current user based on the Authorization header.
    
    This is a simplified authentication system that:
    1. Accepts any non-empty token as valid
    2. Creates usernames based on part of the token
    3. Falls back to 'anonymous' user if no token is provided
    
    In a production environment, this should be replaced with proper authentication.
    
    Args:
        authorization: The Authorization header value (optional)
        
    Returns:
        User: The current user model
    """
    if not authorization:
        # Return a default user for unauthenticated requests
        return User(username="anonymous", disabled=False)
        
    # Handle Bearer token format
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    
    if token:
        # Create a username based on part of the token
        return User(username=f"user_{token[:8]}", disabled=False)
    
    return User(username="anonymous", disabled=False)