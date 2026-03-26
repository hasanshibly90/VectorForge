import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import Webhook

logger = logging.getLogger(__name__)


def _sign_payload(payload: dict, secret: str) -> str:
    """Create HMAC-SHA256 signature for webhook payload."""
    body = json.dumps(payload, sort_keys=True, default=str)
    return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()


async def fire_webhooks(
    db: AsyncSession,
    user_id: str,
    event: str,
    payload: dict,
) -> None:
    """Send webhook notifications for a given event."""
    result = await db.execute(
        select(Webhook).where(
            Webhook.user_id == user_id,
            Webhook.is_active == True,
        )
    )
    webhooks = result.scalars().all()

    for webhook in webhooks:
        if event not in webhook.events:
            continue

        body = {
            "event": event,
            "timestamp": datetime.now(UTC).isoformat(),
            "data": payload,
        }
        signature = _sign_payload(body, webhook.secret)

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    webhook.url,
                    json=body,
                    headers={
                        "X-Webhook-Signature": signature,
                        "Content-Type": "application/json",
                    },
                )
        except Exception as e:
            logger.warning(f"Webhook delivery failed for {webhook.url}: {e}")
