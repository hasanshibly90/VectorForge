from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversion import Conversion, ConversionStatus
from app.schemas.billing import UsageResponse


async def get_usage(
    db: AsyncSession,
    user_id: str,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
) -> UsageResponse:
    """Get conversion usage stats for a user in a given period."""
    if period_end is None:
        period_end = datetime.now(UTC)
    if period_start is None:
        # Default to current month
        period_start = period_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    base_query = select(func.count()).where(
        Conversion.user_id == user_id,
        Conversion.created_at >= period_start,
        Conversion.created_at <= period_end,
    )

    total = await db.scalar(base_query)
    successful = await db.scalar(
        base_query.where(Conversion.status == ConversionStatus.COMPLETED)
    )
    failed = await db.scalar(
        base_query.where(Conversion.status == ConversionStatus.FAILED)
    )

    return UsageResponse(
        period_start=period_start,
        period_end=period_end,
        total_conversions=total or 0,
        successful_conversions=successful or 0,
        failed_conversions=failed or 0,
    )


async def get_usage_history(
    db: AsyncSession,
    user_id: str,
    months: int = 6,
) -> list[UsageResponse]:
    """Get monthly usage history."""
    history = []
    now = datetime.now(UTC)

    for i in range(months):
        end = (now.replace(day=1) - timedelta(days=i * 28)).replace(day=1)
        if i == 0:
            end = now
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            month = now.month - i
            year = now.year
            while month <= 0:
                month += 12
                year -= 1
            start = datetime(year, month, 1)
            if i == 1:
                end = now.replace(day=1) - timedelta(seconds=1)
            else:
                next_month = month + 1
                next_year = year
                if next_month > 12:
                    next_month = 1
                    next_year += 1
                end = datetime(next_year, next_month, 1) - timedelta(seconds=1)

        usage = await get_usage(db, user_id, start, end)
        history.append(usage)

    return history
