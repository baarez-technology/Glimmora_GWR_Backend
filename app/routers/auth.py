import pyotp
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.auth import (
    LoginRequest, MagicLinkVerifyRequest, MFAVerifyRequest,
    RefreshRequest, TokenResponse, TempTokenResponse, RegisterRequest, UserOut,
)
from app.services.auth_service import (
    get_user_by_email, create_user, verify_password,
    create_access_token, create_refresh_token, create_temp_token, decode_token,
    verify_magic_link_token, get_user_by_id,
)
from app.models.witness import Witness
from sqlalchemy import select

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_email(db, body.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = await create_user(db, body.email, body.password, body.role, body.full_name)
    return user


@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, body.email)
    if not user or not verify_password(body.password, user.password_hash or ""):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    # Adjudicators require MFA second step
    if user.role == "adjudicator" and user.mfa_secret:
        temp = create_temp_token(user.id)
        return TempTokenResponse(temp_token=temp, requires_mfa=True)

    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id),
        role=user.role,
    )


@router.post("/mfa/verify", response_model=TokenResponse)
async def verify_mfa(body: MFAVerifyRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(body.temp_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid temp token")

    if payload.get("type") != "temp_mfa":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user = await get_user_by_id(db, payload["sub"])
    if not user or not user.mfa_secret:
        raise HTTPException(status_code=401, detail="MFA not configured")

    totp = pyotp.TOTP(user.mfa_secret)
    if not totp.verify(body.code, valid_window=1):
        raise HTTPException(status_code=401, detail="Invalid MFA code")

    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id),
        role=user.role,
    )


@router.post("/magic-link/verify", response_model=TokenResponse)
async def verify_magic_link(body: MagicLinkVerifyRequest, db: AsyncSession = Depends(get_db)):
    witness_id = verify_magic_link_token(body.token)
    if not witness_id:
        raise HTTPException(status_code=401, detail="Invalid or expired magic link")

    result = await db.execute(select(Witness).where(Witness.id == witness_id))
    witness = result.scalar_one_or_none()
    if not witness:
        raise HTTPException(status_code=404, detail="Witness not found")

    # Create or get witness user account
    from app.services.auth_service import get_user_by_email
    user = await get_user_by_email(db, witness.email)
    if not user:
        import uuid
        from app.models.user import User
        user = User(
            id=str(uuid.uuid4()),
            email=witness.email,
            full_name=witness.full_name,
            role="witness",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return TokenResponse(
        access_token=create_access_token(user.id, "witness"),
        refresh_token=create_refresh_token(user.id),
        role="witness",
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user = await get_user_by_id(db, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id),
        role=user.role,
    )
