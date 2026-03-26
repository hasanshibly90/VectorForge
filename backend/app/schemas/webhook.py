from pydantic import BaseModel, HttpUrl
from datetime import datetime


class WebhookCreateRequest(BaseModel):
    url: str
    events: list[str] = ["conversion.completed", "conversion.failed"]


class WebhookUpdateRequest(BaseModel):
    url: str | None = None
    events: list[str] | None = None
    is_active: bool | None = None


class WebhookResponse(BaseModel):
    id: str
    url: str
    events: list[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
