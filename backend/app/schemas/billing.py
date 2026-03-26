from pydantic import BaseModel
from datetime import datetime


class UsageResponse(BaseModel):
    period_start: datetime
    period_end: datetime
    total_conversions: int
    successful_conversions: int
    failed_conversions: int


class UsageHistoryResponse(BaseModel):
    history: list[UsageResponse]
