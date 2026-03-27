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
        "denoise_strength": 10,
        "contrast": None,
        "sharpen": False,
        "upscale_target": 2048,
        "bilateral": True,
        "bilateral_d": 9,
        "bilateral_sigma_color": 75,
        "bilateral_sigma_space": 75,
        "quantize_colors": 0,       # 0 = no quantization for photos
    },
    "artwork": {
        "denoise": True,
        "denoise_strength": 5,
        "contrast": None,
        "sharpen": False,
        "upscale_target": 2048,     # Was 3072 — too slow
        "bilateral": True,
        "bilateral_d": 7,
        "bilateral_sigma_color": 60,
        "bilateral_sigma_space": 60,
        "quantize_colors": 16,
    },
    "logo": {
        "denoise": False,           # Logos don't need denoise (already clean)
        "contrast": None,
        "sharpen": False,
        "upscale_target": 2048,     # 2048 is enough (was 4096 — too slow)
        "bilateral": True,
        "bilateral_d": 5,           # Smaller kernel = faster
        "bilateral_sigma_color": 50,
        "bilateral_sigma_space": 50,
        "quantize_colors": 12,
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
    """Apply CLAHE in LAB color space. Use sparingly — amplifies JPEG noise."""
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
    """Edge-preserving smoothing. Smooths color regions without blurring boundaries."""
    bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    filtered = cv2.bilateralFilter(bgr, d, sigma_color, sigma_space)
    return cv2.cvtColor(filtered, cv2.COLOR_BGR2RGB)


def sharpen(img: np.ndarray, amount: float = 0.5) -> np.ndarray:
    """Unsharp mask sharpening."""
    blurred = cv2.GaussianBlur(img, (0, 0), 3)
    sharpened = cv2.addWeighted(img, 1.0 + amount, blurred, -amount, 0)
    return np.clip(sharpened, 0, 255).astype(np.uint8)


def upscale_lanczos(img: np.ndarray, target_max: int = 4096) -> np.ndarray:
    """Upscale to target max dimension using Lanczos interpolation."""
    h, w = img.shape[:2]
    if max(h, w) >= target_max:
        return img
    scale = target_max / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)


def reduce_colors(img: np.ndarray, n_colors: int = 12) -> np.ndarray:
    """Reduce image to n flat colors using K-means in LAB color space.

    LAB produces perceptually better quantization than RGB.
    This is THE critical step for clean vectorization of gradient images.
    """
    h, w = img.shape[:2]

    # Convert to LAB for perceptual clustering
    lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
    pixels = lab.reshape(-1, 3).astype(np.float32)

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5)
    _, labels, centers = cv2.kmeans(
        pixels, n_colors, None, criteria, 10, cv2.KMEANS_PP_CENTERS
    )

    # Map back to RGB
    centers_lab = np.uint8(centers)
    quantized_lab = centers_lab[labels.flatten()].reshape(h, w, 3)
    quantized_rgb = cv2.cvtColor(quantized_lab, cv2.COLOR_LAB2RGB)
    return quantized_rgb


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
        return img
    return cropped


def remove_background(img: np.ndarray, threshold: int = 30) -> np.ndarray:
    """Detect and replace background with pure white.

    Detects background color from corners, replaces all similar pixels.
    This cleans up off-white, cream, or slightly colored backgrounds.
    """
    h, w = img.shape[:2]
    corner_size = max(10, min(h, w) // 20)
    corners = np.concatenate([
        img[:corner_size, :corner_size].reshape(-1, 3),
        img[:corner_size, -corner_size:].reshape(-1, 3),
        img[-corner_size:, :corner_size].reshape(-1, 3),
        img[-corner_size:, -corner_size:].reshape(-1, 3),
    ])
    bg_color = np.median(corners, axis=0).astype(float)
    diff = np.sqrt(np.sum((img.astype(float) - bg_color) ** 2, axis=2))
    bg_mask = diff < threshold
    result = img.copy()
    result[bg_mask] = [255, 255, 255]
    return result


def morphological_cleanup(img: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    """Remove small noise spots using morphological opening.

    Opening = erosion then dilation. Removes small bright spots on dark bg
    and small dark spots on bright bg.
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    cleaned = cv2.morphologyEx(bgr, cv2.MORPH_OPEN, kernel)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)
    return cv2.cvtColor(cleaned, cv2.COLOR_BGR2RGB)


# ── Main preprocessing pipeline ────────────────────────────────────────

def preprocess_for_vectorization(
    img: np.ndarray,
    preset: Literal["photo", "artwork", "logo"] = "artwork",
    custom_config: dict | None = None,
) -> np.ndarray:
    """Apply full preprocessing pipeline based on preset.

    Pipeline order:
    1. Auto-crop to content
    2. Upscale to target resolution
    3. Denoise (Non-Local Means)
    4. Bilateral filter (edge-preserving smoothing)
    5. Background cleanup (replace near-bg with pure white)
    6. Color quantization (reduce to N flat colors)
    7. Morphological cleanup (remove tiny noise spots)
    """
    config = {**PRESETS.get(preset, PRESETS["artwork"])}
    if custom_config:
        config.update(custom_config)

    # 1. Auto-crop
    img = auto_crop_content(img)

    # 2. Upscale
    img = upscale_lanczos(img, config.get("upscale_target", 3072))

    # 3. Denoise
    if config.get("denoise"):
        img = denoise(img, config.get("denoise_strength", 7))

    # 4. Bilateral filter
    if config.get("bilateral"):
        img = bilateral_filter(
            img,
            d=config.get("bilateral_d", 9),
            sigma_color=config.get("bilateral_sigma_color", 75),
            sigma_space=config.get("bilateral_sigma_space", 75),
        )

    # 5. Background cleanup
    img = remove_background(img, threshold=30)

    # 6. Color quantization (THE critical step for gradients)
    n_colors = config.get("quantize_colors", 0)
    if n_colors > 0:
        img = reduce_colors(img, n_colors)

    # 7. Morphological cleanup (after quantization)
    if n_colors > 0:
        img = morphological_cleanup(img, kernel_size=3)

    # 8. Optional contrast (disabled by default — amplifies JPEG noise)
    if config.get("contrast") == "clahe":
        img = enhance_contrast_clahe(
            img, config.get("clahe_clip", 1.5), config.get("clahe_grid", 8)
        )

    # 9. Optional sharpening (disabled by default)
    if config.get("sharpen"):
        img = sharpen(img, config.get("sharpen_amount", 0.5))

    return img


def preprocess_and_save(
    input_path: str,
    output_path: str,
    preset: Literal["photo", "artwork", "logo"] = "artwork",
) -> str:
    """Preprocess an image file and save as PNG."""
    img = np.array(Image.open(input_path).convert("RGB"))
    processed = preprocess_for_vectorization(img, preset=preset)
    Image.fromarray(processed).save(output_path, "PNG")
    return output_path
