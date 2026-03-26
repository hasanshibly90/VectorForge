from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.billing import UsageHistoryResponse, UsageResponse
from app.services.billing import get_usage, get_usage_history

router = APIRouter(tags=["billing"])


@router.get("/usage", response_model=UsageResponse)
async def current_usage(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_usage(db, user.id)


@router.get("/usage/history", response_model=UsageHistoryResponse)
async def usage_history(
    months: int = Query(default=6, ge=1, le=24),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    history = await get_usage_history(db, user.id, months)
    return UsageHistoryResponse(history=history)
