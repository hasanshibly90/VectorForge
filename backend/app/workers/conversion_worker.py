import logging
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from app.database import async_session
from app.models.conversion import Conversion, ConversionStatus
from app.schemas.conversion import ConversionSettings
from app.services.converter import convert_raster_to_vector
from app.services.storage import get_result_dir, get_storage
from app.services.webhook_sender import fire_webhooks

logger = logging.getLogger(__name__)


async def run_conversion(conversion_id: str) -> None:
    """Execute a conversion job. Runs as a background task."""
    async with async_session() as db:
        result = await db.execute(
            select(Conversion).where(Conversion.id == conversion_id)
        )
        conversion = result.scalar_one_or_none()
        if not conversion:
            logger.error(f"Conversion {conversion_id} not found")
            return

        conversion.status = ConversionStatus.PROCESSING
        await db.commit()

        storage = get_storage()

        try:
            input_path = storage.get_path(conversion.input_path)
            result_dir_key = get_result_dir(conversion.id)
            result_dir = storage.get_path(result_dir_key)
            result_dir.mkdir(parents=True, exist_ok=True)

            settings = ConversionSettings(**conversion.settings_json)

            # Run CNC-grade pipeline (potrace) or vtracer fallback
            conv_result = await convert_raster_to_vector(
                input_path=input_path,
                output_dir=result_dir,
                settings=settings,
            )

            # Populate all output paths
            conversion.output_dir_path = result_dir_key

            if conv_result.combined_svg_path and conv_result.combined_svg_path.exists():
                conversion.output_svg_path = f"{result_dir_key}/{conv_result.combined_svg_path.name}"

            if conv_result.bmp_path and conv_result.bmp_path.exists():
                conversion.output_bmp_path = f"{result_dir_key}/{conv_result.bmp_path.name}"

            if conv_result.png_path and conv_result.png_path.exists():
                conversion.output_png_path = f"{result_dir_key}/{conv_result.png_path.name}"

            if conv_result.layers_json_path and conv_result.layers_json_path.exists():
                conversion.output_layers_json = f"{result_dir_key}/{conv_result.layers_json_path.name}"

            if conv_result.viewer_html_path and conv_result.viewer_html_path.exists():
                conversion.output_viewer_path = f"{result_dir_key}/{conv_result.viewer_html_path.name}"

            # Store layer info
            conversion.layers_info = [
                {
                    "name": l.name,
                    "color_hex": l.color_hex,
                    "area_pct": l.area_pct,
                    "svg_file": l.svg_file,
                }
                for l in conv_result.layers
            ]

            # Detect which engine was used from metadata
            if conv_result.layers_json_path and conv_result.layers_json_path.exists():
                import json
                meta = json.loads(conv_result.layers_json_path.read_text())
                conversion.engine_used = meta.get("engine", "potrace")
            else:
                conversion.engine_used = "vtracer"

            conversion.status = ConversionStatus.COMPLETED
            conversion.processing_time_ms = conv_result.processing_time_ms
            conversion.completed_at = datetime.now(UTC)
            conversion.is_billed = True

            await db.commit()

            # Fire webhooks
            if conversion.user_id:
                await fire_webhooks(db, conversion.user_id, "conversion.completed", {
                    "conversion_id": conversion.id,
                    "original_filename": conversion.original_filename,
                    "processing_time_ms": conversion.processing_time_ms,
                    "engine": conversion.engine_used,
                    "layers": conversion.layers_info,
                    "status": "completed",
                })

            logger.info(
                f"Conversion {conversion_id} completed in {conv_result.processing_time_ms}ms "
                f"({conversion.engine_used}, {len(conv_result.layers)} layers)"
            )

        except Exception as e:
            logger.exception(f"Conversion {conversion_id} failed: {e}")
            conversion.status = ConversionStatus.FAILED
            conversion.error_message = str(e)
            conversion.completed_at = datetime.now(UTC)
            await db.commit()

            if conversion.user_id:
                await fire_webhooks(db, conversion.user_id, "conversion.failed", {
                    "conversion_id": conversion.id,
                    "original_filename": conversion.original_filename,
                    "error": str(e),
                    "status": "failed",
                })
