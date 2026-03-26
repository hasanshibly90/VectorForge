import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.conversion import Conversion


def generate_share_token() -> str:
    """Generate a random 16-char URL-safe token."""
    return secrets.token_urlsafe(12)


async def create_share_link(
    db: AsyncSession,
    conversion_id: str,
    user_id: str,
) -> tuple[str, str]:
    """Create or return existing share link for a conversion.
    Returns (share_token, share_url).
    """
    result = await db.execute(
        select(Conversion).where(
            Conversion.id == conversion_id,
            Conversion.user_id == user_id,
        )
    )
    conversion = result.scalar_one_or_none()
    if not conversion:
        raise ValueError("Conversion not found")

    if not conversion.share_token:
        conversion.share_token = generate_share_token()
        await db.commit()
        await db.refresh(conversion)

    settings = get_settings()
    share_url = f"{settings.base_url}/api/s/{conversion.share_token}"
    return conversion.share_token, share_url


async def get_shared_conversion(
    db: AsyncSession,
    token: str,
) -> Conversion | None:
    """Look up a conversion by its share token."""
    result = await db.execute(
        select(Conversion).where(Conversion.share_token == token)
    )
    return result.scalar_one_or_none()
