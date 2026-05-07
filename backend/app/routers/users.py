from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.middleware.auth import require_current_user
from app.models.user import User

router = APIRouter(prefix="/api/v1/users", tags=["users"])


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    auto_execute: bool

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    auto_execute: bool | None = None


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: dict = Depends(require_current_user),
    db: AsyncSession = Depends(get_session),
) -> UserResponse:
    result = await db.execute(select(User).where(User.id == current_user["user_id"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        auto_execute=user.auto_execute,
    )


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UserUpdate,
    current_user: dict = Depends(require_current_user),
    db: AsyncSession = Depends(get_session),
) -> UserResponse:
    result = await db.execute(select(User).where(User.id == current_user["user_id"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if body.auto_execute is not None:
        user.auto_execute = body.auto_execute

    await db.commit()
    await db.refresh(user)
    return UserResponse(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        auto_execute=user.auto_execute,
    )
