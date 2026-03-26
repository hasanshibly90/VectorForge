from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ColorMode(str, Enum):
    COLOR = "color"
    BINARY = "binary"


class OutputFormat(str, Enum):
    SVG = "svg"
    DXF = "dxf"


class ConversionSettings(BaseModel):
    colormode: ColorMode = ColorMode.COLOR
    detail_level: int = Field(default=5, ge=1, le=10)
    smoothing: int = Field(default=5, ge=1, le=10)
    output_formats: list[OutputFormat] = [OutputFormat.SVG]


class LayerResponse(BaseModel):
    name: str
    color_hex: str
    area_pct: float
    svg_file: str


class ConversionResponse(BaseModel):
    id: str
    status: str
    original_filename: str
    original_format: str
    original_size_bytes: int
    settings: dict
    share_token: str | None
    share_url: str | None = None
    processing_time_ms: int | None
    error_message: str | None
    engine_used: str | None = None
    layers: list[LayerResponse] = []
    outputs: dict = {}  # {combined_svg, bmp, png, layers_json, viewer_html, layer_svgs}
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class ConversionListResponse(BaseModel):
    conversions: list[ConversionResponse]
    total: int
    page: int
    per_page: int


class BatchResponse(BaseModel):
    batch_id: str
    conversions: list[ConversionResponse]
    total: int


class ShareResponse(BaseModel):
    share_url: str
    share_token: str


class ColorAnalysisResponse(BaseModel):
    colors: list[dict]
    total_pixels: int
    recommendation: str
