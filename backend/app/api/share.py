from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.dependencies import get_current_user
from app.core.exceptions import NotFoundError
from app.database import get_db
from app.models.conversion import ConversionStatus
from app.models.user import User
from app.schemas.conversion import ConversionResponse, ShareResponse
from app.services.share import create_share_link, get_shared_conversion
from app.services.storage import get_storage

router = APIRouter(tags=["sharing"])


@router.post("/conversions/{conversion_id}/share", response_model=ShareResponse)
async def share_conversion(
    conversion_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        token, url = await create_share_link(db, conversion_id, user.id)
    except ValueError:
        raise NotFoundError("Conversion not found")

    return ShareResponse(share_token=token, share_url=url)


@router.get("/s/{token}")
async def get_shared(token: str, db: AsyncSession = Depends(get_db)):
    conversion = await get_shared_conversion(db, token)
    if not conversion:
        raise NotFoundError("Shared link not found or expired")

    settings = get_settings()
    return ConversionResponse(
        id=conversion.id,
        status=conversion.status,
        original_filename=conversion.original_filename,
        original_format=conversion.original_format,
        original_size_bytes=conversion.original_size_bytes,
        settings=conversion.settings_json,
        share_token=conversion.share_token,
        share_url=f"{settings.base_url}/api/s/{conversion.share_token}",
        processing_time_ms=conversion.processing_time_ms,
        error_message=conversion.error_message,
        created_at=conversion.created_at,
        completed_at=conversion.completed_at,
    )


@router.get("/s/{token}/download")
async def download_shared(
    token: str,
    format: str = Query(default="svg", pattern="^(svg|dxf)$"),
    db: AsyncSession = Depends(get_db),
):
    conversion = await get_shared_conversion(db, token)
    if not conversion:
        raise NotFoundError("Shared link not found or expired")

    if conversion.status != ConversionStatus.COMPLETED:
        raise NotFoundError("Conversion not yet completed")

    storage = get_storage()
    if format == "dxf" and conversion.output_dxf_path:
        file_path = storage.get_path(conversion.output_dxf_path)
        media_type = "application/dxf"
        filename = Path(conversion.original_filename).stem + ".dxf"
    elif conversion.output_svg_path:
        file_path = storage.get_path(conversion.output_svg_path)
        media_type = "image/svg+xml"
        filename = Path(conversion.original_filename).stem + ".svg"
    else:
        raise NotFoundError("Output file not found")

    return FileResponse(path=str(file_path), media_type=media_type, filename=filename)
