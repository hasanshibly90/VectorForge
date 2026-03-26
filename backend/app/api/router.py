from fastapi import APIRouter

from app.api import auth, billing, conversions, share, webhooks

api_router = APIRouter(prefix="/api")

api_router.include_router(auth.router)
api_router.include_router(conversions.router)
api_router.include_router(share.router)
api_router.include_router(webhooks.router)
api_router.include_router(billing.router)
