import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Query, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.dependencies import get_current_user, get_optional_user
from app.core.exceptions import FileTooLargeError, NotFoundError, UnsupportedFormatError
from app.database import get_db
from app.models.conversion import Conversion, ConversionStatus
from app.models.user import User
from app.schemas.conversion import (
    BatchResponse,
    ColorAnalysisResponse,
    ColorMode,
    ConversionListResponse,
    ConversionResponse,
    ConversionSettings,
    LayerResponse,
    OutputFormat,
)
from app.services.storage import generate_upload_key, get_storage
from app.workers.conversion_worker import run_conversion

router = APIRouter(prefix="/conversions", tags=["conversions"])

ALLOWED_FORMATS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}


def _validate_file(file: UploadFile) -> str:
    ext = Path(file.filename or "unknown").suffix.lower()
    if ext not in ALLOWED_FORMATS:
        raise UnsupportedFormatError(ext)
    return ext


def _build_response(conv: Conversion) -> ConversionResponse:
    settings = get_settings()
    share_url = f"{settings.base_url}/api/s/{conv.share_token}" if conv.share_token else None

    # Build outputs dict with download URLs
    outputs = {}
    if conv.output_svg_path:
        outputs["combined_svg"] = f"/api/conversions/{conv.id}/download?format=svg"
    if conv.output_bmp_path:
        outputs["bmp"] = f"/api/conversions/{conv.id}/download?format=bmp"
    if conv.output_png_path:
        outputs["png"] = f"/api/conversions/{conv.id}/download?format=png"
    if conv.output_layers_json:
        outputs["layers_json"] = f"/api/conversions/{conv.id}/download?format=json"
    if conv.output_viewer_path:
        outputs["viewer"] = f"/api/conversions/{conv.id}/viewer"

    # Build layer list with individual download URLs
    if conv.layers_info:
        outputs["layer_svgs"] = [
            f"/api/conversions/{conv.id}/download?format=layer&layer={l['name']}"
            for l in conv.layers_info
        ]

    layers = []
    if conv.layers_info:
        layers = [
            LayerResponse(
                name=l["name"],
                color_hex=l["color_hex"],
                area_pct=l["area_pct"],
                svg_file=l["svg_file"],
            )
            for l in conv.layers_info
        ]

    return ConversionResponse(
        id=conv.id,
        status=conv.status,
        original_filename=conv.original_filename,
        original_format=conv.original_format,
        original_size_bytes=conv.original_size_bytes,
        settings=conv.settings_json,
        share_token=conv.share_token,
        share_url=share_url,
        processing_time_ms=conv.processing_time_ms,
        error_message=conv.error_message,
        engine_used=conv.engine_used,
        layers=layers,
        outputs=outputs,
        created_at=conv.created_at,
        completed_at=conv.completed_at,
    )


# ── Color Analysis ────────────────────────────────────────────────────

@router.post("/analyze-colors", response_model=ColorAnalysisResponse)
async def analyze_colors(
    file: UploadFile,
    max_colors: int = Form(default=10),
):
    """Analyze dominant colors in an uploaded image before conversion."""
    from app.services.converter import analyze_colors as _analyze

    ext = _validate_file(file)
    content = await file.read()

    # Save temp file
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        colors = _analyze(tmp_path, max_colors)
        total_pixels = sum(c["pixel_count"] for c in colors)

        # Recommendation
        n_significant = sum(1 for c in colors if c["percentage"] > 2)
        if n_significant <= 2:
            rec = "Simple image (2 colors). Best for monochrome/logo conversion."
        elif n_significant <= 4:
            rec = "Standard image (3-4 colors). Good for layered vector output."
        else:
            rec = "Complex image (5+ colors). Consider simplifying or using higher detail level."

        return ColorAnalysisResponse(
            colors=colors,
            total_pixels=total_pixels,
            recommendation=rec,
        )
    finally:
        tmp_path.unlink(missing_ok=True)


# ── Single Upload ─────────────────────────────────────────────────────

@router.post("", response_model=ConversionResponse, status_code=201)
async def create_conversion(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    colormode: ColorMode = Form(default=ColorMode.COLOR),
    detail_level: int = Form(default=5, ge=1, le=10),
    smoothing: int = Form(default=5, ge=1, le=10),
    output_formats: str = Form(default="svg"),
    custom_colors: str = Form(default=""),  # JSON: {colors: [{hex, name}], transparent: hex}
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    ext = _validate_file(file)
    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise FileTooLargeError(settings.max_upload_size_mb)

    formats = [OutputFormat(f.strip()) for f in output_formats.split(",") if f.strip()]
    job_id, upload_key = generate_upload_key(file.filename or "upload")
    storage = get_storage()
    upload_path = storage.get_path(upload_key)
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    upload_path.write_bytes(content)

    conversion_settings = ConversionSettings(
        colormode=colormode, detail_level=detail_level,
        smoothing=smoothing, output_formats=formats,
    )

    settings_data = conversion_settings.model_dump(mode="json")
    if custom_colors:
        settings_data["custom_colors"] = custom_colors

    conversion = Conversion(
        id=job_id, user_id=user.id if user else None,
        status=ConversionStatus.PENDING,
        original_filename=file.filename or "upload",
        original_format=ext.lstrip("."),
        original_size_bytes=len(content),
        input_path=upload_key,
        settings_json=settings_data,
    )
    db.add(conversion)
    await db.commit()
    await db.refresh(conversion)

    background_tasks.add_task(run_conversion, job_id)
    return _build_response(conversion)


# ── Batch Upload ──────────────────────────────────────────────────────

@router.post("/batch", response_model=BatchResponse, status_code=201)
async def create_batch_conversion(
    background_tasks: BackgroundTasks,
    files: list[UploadFile],
    colormode: ColorMode = Form(default=ColorMode.COLOR),
    detail_level: int = Form(default=5, ge=1, le=10),
    smoothing: int = Form(default=5, ge=1, le=10),
    output_formats: str = Form(default="svg"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    batch_id = str(uuid.uuid4())
    formats = [OutputFormat(f.strip()) for f in output_formats.split(",") if f.strip()]
    conversions = []

    for file in files:
        ext = _validate_file(file)
        content = await file.read()
        if len(content) > settings.max_upload_bytes:
            raise FileTooLargeError(settings.max_upload_size_mb)

        job_id, upload_key = generate_upload_key(file.filename or "upload")
        storage = get_storage()
        upload_path = storage.get_path(upload_key)
        upload_path.parent.mkdir(parents=True, exist_ok=True)
        upload_path.write_bytes(content)

        conversion_settings = ConversionSettings(
            colormode=colormode, detail_level=detail_level,
            smoothing=smoothing, output_formats=formats,
        )

        conversion = Conversion(
            id=job_id, user_id=user.id, batch_id=batch_id,
            status=ConversionStatus.PENDING,
            original_filename=file.filename or "upload",
            original_format=ext.lstrip("."),
            original_size_bytes=len(content),
            input_path=upload_key,
            settings_json=conversion_settings.model_dump(mode="json"),
        )
        db.add(conversion)
        conversions.append(conversion)

    await db.commit()
    for conv in conversions:
        await db.refresh(conv)
        background_tasks.add_task(run_conversion, conv.id)

    return BatchResponse(
        batch_id=batch_id,
        conversions=[_build_response(c) for c in conversions],
        total=len(conversions),
    )


# ── List & Get ────────────────────────────────────────────────────────

@router.get("", response_model=ConversionListResponse)
async def list_conversions(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * per_page
    total = await db.scalar(
        select(func.count()).where(Conversion.user_id == user.id)
    )
    result = await db.execute(
        select(Conversion).where(Conversion.user_id == user.id)
        .order_by(Conversion.created_at.desc()).offset(offset).limit(per_page)
    )
    return ConversionListResponse(
        conversions=[_build_response(c) for c in result.scalars().all()],
        total=total or 0, page=page, per_page=per_page,
    )


@router.get("/{conversion_id}", response_model=ConversionResponse)
async def get_conversion(
    conversion_id: str,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Conversion).where(Conversion.id == conversion_id)
    if user:
        query = query.where(Conversion.user_id == user.id)
    result = await db.execute(query)
    conversion = result.scalar_one_or_none()
    if not conversion:
        raise NotFoundError("Conversion not found")
    return _build_response(conversion)


# ── Download (all 5 formats + per-layer) ──────────────────────────────

@router.get("/{conversion_id}/download")
async def download_conversion(
    conversion_id: str,
    format: str = Query(default="svg", pattern="^(svg|bmp|png|json|dxf|layer|pdf|eps|gcode|original)$"),
    layer: str | None = Query(default=None),
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Conversion).where(Conversion.id == conversion_id)
    if user:
        query = query.where(Conversion.user_id == user.id)
    result = await db.execute(query)
    conversion = result.scalar_one_or_none()
    if not conversion:
        raise NotFoundError("Conversion not found")
    if conversion.status != ConversionStatus.COMPLETED:
        raise NotFoundError("Conversion not yet completed")

    storage = get_storage()
    stem = Path(conversion.original_filename).stem

    if format == "svg" and conversion.output_svg_path:
        file_path = storage.get_path(conversion.output_svg_path)
        return FileResponse(path=str(file_path), media_type="image/svg+xml", filename=f"{stem}_combined.svg")

    elif format == "bmp" and conversion.output_bmp_path:
        file_path = storage.get_path(conversion.output_bmp_path)
        return FileResponse(path=str(file_path), media_type="image/bmp", filename=f"{stem}_300dpi.bmp")

    elif format == "png" and conversion.output_png_path:
        file_path = storage.get_path(conversion.output_png_path)
        return FileResponse(path=str(file_path), media_type="image/png", filename=f"{stem}_transparent.png")

    elif format == "json" and conversion.output_layers_json:
        file_path = storage.get_path(conversion.output_layers_json)
        return FileResponse(path=str(file_path), media_type="application/json", filename=f"{stem}_layers.json")

    elif format == "layer" and layer and conversion.output_dir_path:
        layer_path = storage.get_path(f"{conversion.output_dir_path}/layers/{stem}_{layer}.svg")
        if layer_path.exists():
            return FileResponse(path=str(layer_path), media_type="image/svg+xml", filename=f"{stem}_{layer}.svg")
        raise NotFoundError(f"Layer '{layer}' not found")

    elif format == "dxf" and conversion.output_dxf_path:
        file_path = storage.get_path(conversion.output_dxf_path)
        return FileResponse(path=str(file_path), media_type="application/dxf", filename=f"{stem}.dxf")

    elif format == "pdf" and conversion.output_svg_path:
        from app.services.export_formats import svg_to_pdf
        svg_file = storage.get_path(conversion.output_svg_path)
        pdf_file = svg_file.parent / f"{stem}.pdf"
        if not pdf_file.exists():
            svg_to_pdf(svg_file, pdf_file)
        return FileResponse(path=str(pdf_file), media_type="application/pdf", filename=f"{stem}.pdf")

    elif format == "eps" and conversion.output_svg_path:
        from app.services.export_formats import svg_to_eps
        svg_file = storage.get_path(conversion.output_svg_path)
        eps_file = svg_file.parent / f"{stem}.eps"
        if not eps_file.exists():
            svg_to_eps(svg_file, eps_file)
        return FileResponse(path=str(eps_file), media_type="application/postscript", filename=f"{stem}.eps")

    elif format == "gcode" and conversion.output_svg_path:
        from app.services.export_formats import svg_to_gcode
        svg_file = storage.get_path(conversion.output_svg_path)
        gcode_file = svg_file.parent / f"{stem}.gcode"
        if not gcode_file.exists():
            svg_to_gcode(svg_file, gcode_file)
        return FileResponse(path=str(gcode_file), media_type="text/plain", filename=f"{stem}.gcode")

    elif format == "original":
        file_path = storage.get_path(conversion.input_path)
        if file_path.exists():
            ext = conversion.original_format
            media = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "bmp": "image/bmp", "tiff": "image/tiff", "webp": "image/webp"}.get(ext, "application/octet-stream")
            return FileResponse(path=str(file_path), media_type=media, filename=conversion.original_filename)

    raise NotFoundError(f"Output format '{format}' not available for this conversion")


# ── Download All (ZIP) ────────────────────────────────────────────────

@router.get("/{conversion_id}/download-all")
async def download_all(
    conversion_id: str,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Download all output files as a single ZIP archive."""
    import io
    import zipfile
    from fastapi.responses import StreamingResponse

    query = select(Conversion).where(Conversion.id == conversion_id)
    if user:
        query = query.where(Conversion.user_id == user.id)
    result = await db.execute(query)
    conversion = result.scalar_one_or_none()
    if not conversion or conversion.status != ConversionStatus.COMPLETED:
        raise NotFoundError("Conversion not found or not completed")

    storage = get_storage()
    stem = Path(conversion.original_filename).stem

    # Collect all output files
    files_to_zip: list[tuple[str, Path]] = []

    if conversion.output_svg_path:
        p = storage.get_path(conversion.output_svg_path)
        if p.exists():
            files_to_zip.append((f"{stem}_combined.svg", p))

    if conversion.output_bmp_path:
        p = storage.get_path(conversion.output_bmp_path)
        if p.exists():
            files_to_zip.append((f"{stem}_300dpi.bmp", p))

    if conversion.output_png_path:
        p = storage.get_path(conversion.output_png_path)
        if p.exists():
            files_to_zip.append((f"{stem}_transparent.png", p))

    if conversion.output_layers_json:
        p = storage.get_path(conversion.output_layers_json)
        if p.exists():
            files_to_zip.append((f"{stem}_layers.json", p))

    if conversion.output_viewer_path:
        p = storage.get_path(conversion.output_viewer_path)
        if p.exists():
            files_to_zip.append(("layer_viewer.html", p))

    # Add per-layer SVGs
    if conversion.output_dir_path and conversion.layers_info:
        layers_dir = storage.get_path(f"{conversion.output_dir_path}/layers")
        if layers_dir.exists():
            for svg_file in layers_dir.glob("*.svg"):
                files_to_zip.append((f"layers/{svg_file.name}", svg_file))

    if not files_to_zip:
        raise NotFoundError("No output files found")

    # Create ZIP in memory
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, path in files_to_zip:
            zf.write(str(path), name)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{stem}_vectorforge.zip"'},
    )


# ── Layer Viewer ──────────────────────────────────────────────────────

@router.get("/{conversion_id}/viewer")
async def get_viewer(
    conversion_id: str,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Conversion).where(Conversion.id == conversion_id)
    if user:
        query = query.where(Conversion.user_id == user.id)
    result = await db.execute(query)
    conversion = result.scalar_one_or_none()
    if not conversion or not conversion.output_viewer_path:
        raise NotFoundError("Viewer not available")

    storage = get_storage()
    viewer_path = storage.get_path(conversion.output_viewer_path)
    if not viewer_path.exists():
        raise NotFoundError("Viewer file not found")

    html = viewer_path.read_text(encoding="utf-8")
    return HTMLResponse(content=html)
