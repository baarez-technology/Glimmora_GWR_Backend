from typing import Optional, AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.auth_service import decode_token, get_user_by_id
from app.models.user import User

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user = await get_user_by_id(db, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


async def require_organizer(user: User = Depends(get_current_user)) -> User:
    if user.role not in ("organizer", "adjudicator"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organizer access required")
    return user


async def require_adjudicator(user: User = Depends(get_current_user)) -> User:
    if user.role != "adjudicator":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Adjudicator access required")
    return user
