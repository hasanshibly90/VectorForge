"""
Image preprocessing pipeline for vectorization.

Provides modular preprocessing steps that can be composed based on
image type and quality requirements. Each function takes and returns
a numpy array (RGB uint8), making them chainable.

Usage:
    from app.services.preprocessing import preprocess_for_vectorization
    processed = preprocess_for_vectorization(img_array, preset="logo")
"""

import cv2
import numpy as np
from PIL import Image
from typing import Literal


# ── Presets ────────────────────────────────────────────────────────────

PRESETS = {
    "photo": {
        "denoise": True,
        "denoise_strength": 7,
        "contrast": "clahe",
        "clahe_clip": 2.0,
        "clahe_grid": 8,
        "sharpen": False,
        "upscale_target": 2048,
        "bilateral": False,
    },
    "artwork": {
        "denoise": True,
        "denoise_strength": 5,
        "contrast": "clahe",
        "clahe_clip": 1.5,
        "clahe_grid": 8,
        "sharpen": True,
        "sharpen_amount": 0.5,
        "upscale_target": 3072,
        "bilateral": True,
        "bilateral_d": 9,
        "bilateral_sigma_color": 75,
        "bilateral_sigma_space": 75,
    },
    "logo": {
        "denoise": False,
        "contrast": "clahe",
        "clahe_clip": 1.0,
        "clahe_grid": 4,
        "sharpen": True,
        "sharpen_amount": 0.8,
        "upscale_target": 4096,
        "bilateral": True,
        "bilateral_d": 5,
        "bilateral_sigma_color": 50,
        "bilateral_sigma_space": 50,
    },
}


# ── Core preprocessing functions ───────────────────────────────────────

def denoise(img: np.ndarray, strength: int = 7) -> np.ndarray:
    """Remove noise while preserving edges using Non-Local Means."""
    return cv2.fastNlMeansDenoisingColored(img, None, strength, strength, 7, 21)


def enhance_contrast_clahe(
    img: np.ndarray,
    clip_limit: float = 2.0,
    tile_grid_size: int = 8,
) -> np.ndarray:
    """Apply CLAHE (Contrast Limited Adaptive Histogram Equalization).

    Works in LAB color space to enhance luminance without distorting colors.
    """
    lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_grid_size, tile_grid_size))
    l = clahe.apply(l)
    lab = cv2.merge([l, a, b])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)


def bilateral_filter(
    img: np.ndarray,
    d: int = 9,
    sigma_color: float = 75,
    sigma_space: float = 75,
) -> np.ndarray:
    """Edge-preserving smoothing. Removes noise while keeping sharp edges.

    Critical for logos and text — smooths color regions without blurring boundaries.
    """
    bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    filtered = cv2.bilateralFilter(bgr, d, sigma_color, sigma_space)
    return cv2.cvtColor(filtered, cv2.COLOR_BGR2RGB)


def sharpen(img: np.ndarray, amount: float = 0.5) -> np.ndarray:
    """Unsharp mask sharpening. Enhances edges for cleaner tracing."""
    blurred = cv2.GaussianBlur(img, (0, 0), 3)
    sharpened = cv2.addWeighted(img, 1.0 + amount, blurred, -amount, 0)
    return np.clip(sharpened, 0, 255).astype(np.uint8)


def upscale_lanczos(img: np.ndarray, target_max: int = 4096) -> np.ndarray:
    """Upscale image to target max dimension using Lanczos interpolation."""
    h, w = img.shape[:2]
    if max(h, w) >= target_max:
        return img
    scale = target_max / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)


def reduce_colors(img: np.ndarray, n_colors: int = 8) -> np.ndarray:
    """Reduce image to n_colors using K-means color quantization.

    This is a preprocessing step to simplify images before tracing.
    Produces clean flat-color regions ideal for vectorization.
    """
    h, w = img.shape[:2]
    pixels = img.reshape(-1, 3).astype(np.float32)

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    _, labels, centers = cv2.kmeans(
        pixels, n_colors, None, criteria, 10, cv2.KMEANS_PP_CENTERS
    )

    centers = np.uint8(centers)
    quantized = centers[labels.flatten()]
    return quantized.reshape(h, w, 3)


def auto_crop_content(img: np.ndarray, padding_pct: float = 0.02) -> np.ndarray:
    """Crop to content by detecting background from corners."""
    h, w = img.shape[:2]
    corner_size = max(10, min(h, w) // 20)

    corners = np.concatenate([
        img[:corner_size, :corner_size].reshape(-1, 3),
        img[:corner_size, -corner_size:].reshape(-1, 3),
        img[-corner_size:, :corner_size].reshape(-1, 3),
        img[-corner_size:, -corner_size:].reshape(-1, 3),
    ])
    bg_color = np.median(corners, axis=0).astype(int)

    diff = np.sqrt(np.sum((img.astype(float) - bg_color.astype(float)) ** 2, axis=2))
    content_mask = diff > 40

    rows = np.any(content_mask, axis=1)
    cols = np.any(content_mask, axis=0)
    if not rows.any() or not cols.any():
        return img

    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]

    pad_h = int((rmax - rmin) * padding_pct)
    pad_w = int((cmax - cmin) * padding_pct)
    rmin = max(0, rmin - pad_h)
    rmax = min(h - 1, rmax + pad_h)
    cmin = max(0, cmin - pad_w)
    cmax = min(w - 1, cmax + pad_w)

    cropped = img[rmin:rmax + 1, cmin:cmax + 1]
    if cropped.shape[0] < h * 0.4 or cropped.shape[1] < w * 0.4:
        return img  # Too aggressive, keep original

    return cropped


# ── Main preprocessing pipeline ────────────────────────────────────────

def preprocess_for_vectorization(
    img: np.ndarray,
    preset: Literal["photo", "artwork", "logo"] = "artwork",
    custom_config: dict | None = None,
) -> np.ndarray:
    """Apply full preprocessing pipeline based on preset.

    Args:
        img: RGB uint8 numpy array
        preset: One of "photo", "artwork", "logo"
        custom_config: Override individual preset values

    Returns:
        Preprocessed RGB uint8 numpy array
    """
    config = {**PRESETS.get(preset, PRESETS["artwork"])}
    if custom_config:
        config.update(custom_config)

    # Step 1: Auto-crop to content (remove border artifacts)
    img = auto_crop_content(img)

    # Step 2: Upscale to target resolution
    img = upscale_lanczos(img, config.get("upscale_target", 3072))

    # Step 3: Denoise (if enabled)
    if config.get("denoise"):
        img = denoise(img, config.get("denoise_strength", 7))

    # Step 4: Bilateral filter (edge-preserving smoothing)
    if config.get("bilateral"):
        img = bilateral_filter(
            img,
            d=config.get("bilateral_d", 9),
            sigma_color=config.get("bilateral_sigma_color", 75),
            sigma_space=config.get("bilateral_sigma_space", 75),
        )

    # Step 5: Contrast enhancement
    contrast_mode = config.get("contrast")
    if contrast_mode == "clahe":
        img = enhance_contrast_clahe(
            img,
            clip_limit=config.get("clahe_clip", 2.0),
            tile_grid_size=config.get("clahe_grid", 8),
        )

    # Step 6: Sharpening
    if config.get("sharpen"):
        img = sharpen(img, config.get("sharpen_amount", 0.5))

    return img


def preprocess_and_save(
    input_path: str,
    output_path: str,
    preset: Literal["photo", "artwork", "logo"] = "artwork",
) -> str:
    """Preprocess an image file and save the result as PNG.

    Returns the output path.
    """
    img = np.array(Image.open(input_path).convert("RGB"))
    processed = preprocess_for_vectorization(img, preset=preset)
    Image.fromarray(processed).save(output_path, "PNG")
    return output_path
