"""
Conversion engine — wraps the CNC-grade potrace pipeline AND vtracer as a fast fallback.

Each conversion produces a versioned output folder with ALL 5 output files:
  {name}_combined.svg      — All color layers merged
  {name}_300dpi.bmp         — 300 DPI print-ready bitmap
  {name}_transparent.png    — RGBA with alpha transparency
  {name}_layers.json        — Layer metadata
  layers/{name}_{color}.svg — Individual per-layer SVGs
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image
from collections import Counter

from app.schemas.conversion import ConversionSettings


@dataclass
class LayerInfo:
    name: str
    color_hex: str
    area_pct: float
    svg_file: str


@dataclass
class ConversionResult:
    combined_svg_path: Path | None = None
    bmp_path: Path | None = None
    png_path: Path | None = None
    layers_json_path: Path | None = None
    layer_svg_paths: list[Path] = field(default_factory=list)
    viewer_html_path: Path | None = None
    layers: list[LayerInfo] = field(default_factory=list)
    processing_time_ms: int = 0


def analyze_colors(input_path: Path, max_colors: int = 15) -> list[dict]:
    """Analyze dominant colors in an image with guaranteed hue coverage.

    Two-pass approach:
    1. Standard quantization to find dominant colors by pixel count
    2. Hue-family scan to ensure NO visually distinct color is ever missed
       (catches red text at 1%, blue accents at 0.5%, etc.)
    """
    img = Image.open(input_path).convert("RGB")
    pixels = np.array(img).reshape(-1, 3)
    total = len(pixels)

    # Pass 1: Standard quantization (16px buckets for finer detection)
    quantized = (pixels // 16) * 16
    counts = Counter(map(tuple, quantized))

    results = []
    for color, count in counts.most_common(max_colors):
        pct = count / total * 100
        if pct < 0.3:
            break
        hex_c = f"#{int(color[0]):02x}{int(color[1]):02x}{int(color[2]):02x}"
        results.append({
            "rgb": [int(color[0]), int(color[1]), int(color[2])],
            "hex": hex_c,
            "percentage": round(float(pct), 1),
            "pixel_count": int(count),
        })

    # Pass 2: Ensure every distinct hue family is represented
    # This prevents "missing red text" and similar issues permanently
    hue_families = {
        "red":    {"test": lambda r,g,b: r > 150 and g < 100 and b < 100, "found": False},
        "green":  {"test": lambda r,g,b: g > 120 and r < 100 and b < 100, "found": False},
        "blue":   {"test": lambda r,g,b: b > 150 and r < 100 and g < 100, "found": False},
        "yellow": {"test": lambda r,g,b: r > 150 and g > 120 and b < 80, "found": False},
        "orange": {"test": lambda r,g,b: r > 180 and g > 80 and g < 160 and b < 60, "found": False},
        "purple": {"test": lambda r,g,b: r > 100 and b > 100 and g < 80, "found": False},
        "cyan":   {"test": lambda r,g,b: g > 120 and b > 120 and r < 80, "found": False},
        "pink":   {"test": lambda r,g,b: r > 180 and g < 130 and b > 100, "found": False},
    }

    # Check which hue families are already in results
    for c in results:
        r, g, b = c["rgb"]
        for name, fam in hue_families.items():
            if fam["test"](r, g, b):
                fam["found"] = True

    # Scan image for missing hue families
    # Subsample for speed (every 20th pixel)
    subsample = pixels[::20]
    for name, fam in hue_families.items():
        if fam["found"]:
            continue
        # Count pixels matching this hue family
        matches = sum(1 for p in subsample if fam["test"](int(p[0]), int(p[1]), int(p[2])))
        pct = (matches * 20) / total * 100  # Scale back from subsample
        if pct >= 0.5:  # At least 0.5% of image
            # Find the median color of matching pixels
            matching_pixels = np.array([p for p in subsample if fam["test"](int(p[0]), int(p[1]), int(p[2]))])
            if len(matching_pixels) > 0:
                median_color = np.median(matching_pixels, axis=0).astype(int)
                hex_c = f"#{int(median_color[0]):02x}{int(median_color[1]):02x}{int(median_color[2]):02x}"
                results.append({
                    "rgb": [int(median_color[0]), int(median_color[1]), int(median_color[2])],
                    "hex": hex_c,
                    "percentage": round(float(pct), 1),
                    "pixel_count": int(pct * total / 100),
                })

    # Sort by percentage descending
    results.sort(key=lambda x: x["percentage"], reverse=True)
    return results


def _auto_detect_colors(input_path: Path) -> tuple[dict, str]:
    """Auto-detect color layers from an image using KMeans + merge similar clusters.

    Key improvements over naive KMeans:
    1. Start with few clusters (3-4) to avoid splitting real colors
    2. Merge clusters within 120 RGB distance (aggressively kills anti-alias edge colors)
    3. Snap near-white to #ffffff, near-black to #000000
    4. Use tight thresholds for CNC-grade output
    """
    from sklearn.cluster import KMeans

    img = Image.open(input_path).convert("RGB")
    pixels = np.array(img).reshape(-1, 3)

    # Use MORE clusters to catch small color groups (like red text on a logo)
    # then merge by hue-family, not just distance
    n_clusters = min(12, max(4, len(set(map(tuple, (pixels[::50] // 48) * 48))) // 2))
    kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
    kmeans.fit(pixels[::10])
    centers = kmeans.cluster_centers_.astype(int)
    labels_sub = kmeans.predict(pixels[::10])
    counts = np.bincount(labels_sub, minlength=len(centers))

    def _hue_family(c):
        """Classify a color into a hue family for smart merging."""
        r, g, b = int(c[0]), int(c[1]), int(c[2])
        if r > 200 and g > 200 and b > 200: return "white"
        if r < 50 and g < 50 and b < 50: return "black"
        if r > 150 and g < 100 and b < 100: return "red"
        if g > 150 and r < 100 and b < 100: return "green"
        if b > 150 and r < 100 and g < 100: return "blue"
        if r > 150 and g > 120 and b < 80: return "yellow"
        if r > 100 and g > 100 and b > 100 and max(r,g,b) - min(r,g,b) < 40: return "gray"
        return f"other_{r//64}_{g//64}_{b//64}"

    # Merge clusters within SAME hue family + close distance
    merged = []
    used = set()
    for i in range(len(centers)):
        if i in used:
            continue
        group = [i]
        family_i = _hue_family(centers[i])
        for j in range(i + 1, len(centers)):
            if j in used:
                continue
            family_j = _hue_family(centers[j])
            dist = np.sqrt(np.sum((centers[i].astype(float) - centers[j].astype(float)) ** 2))
            # Merge if: same family OR very close distance
            if family_i == family_j or dist < 50:
                group.append(j)
                used.add(j)
        used.add(i)
        total_count = sum(counts[k] for k in group)
        avg_center = np.average([centers[k] for k in group], weights=[counts[k] for k in group], axis=0).astype(int)
        merged.append({"center": avg_center, "count": total_count})

    # Sort by count (largest first = background)
    merged.sort(key=lambda x: x["count"], reverse=True)

    # Snap colors to pure values
    def snap_color(c):
        r, g, b = int(c[0]), int(c[1]), int(c[2])
        if r > 200 and g > 200 and b > 200:
            return np.array([255, 255, 255])
        if r < 40 and g < 40 and b < 40:
            return np.array([0, 0, 0])
        return c

    for m in merged:
        m["center"] = snap_color(m["center"])

    # Name colors
    def name_color(c):
        r, g, b = int(c[0]), int(c[1]), int(c[2])
        if r > 200 and g > 200 and b > 200: return "white"
        if r < 40 and g < 40 and b < 40: return "black"
        if r > 120 and g < 80 and b < 80: return "red"
        if g > 120 and r < 80 and b < 80: return "green"
        if b > 120 and r < 80 and g < 80: return "blue"
        if r > 150 and g > 120 and b < 80: return "yellow"
        return f"color_{r:02x}{g:02x}{b:02x}"

    # Background = largest cluster
    bg = merged[0]
    total_pixels = sum(m["count"] for m in merged)

    # Drop tiny clusters (< 5% of image) — these are always anti-alias edge artifacts
    design_colors = [
        m for m in merged[1:]
        if m["count"] / total_pixels > 0.01
    ]
    dropped = len(merged) - 1 - len(design_colors)
    if dropped > 0:
        print(f"  Dropped {dropped} tiny color clusters (< 5% of pixels)")

    # Build color definitions with TIGHT thresholds
    color_defs = {}
    names_seen = set()
    for m in design_colors:
        c = m["center"]
        name = name_color(c)
        # Ensure unique name
        base = name
        n = 1
        while name in names_seen:
            name = f"{base}_{n}"
            n += 1
        names_seen.add(name)

        hex_c = f"#{int(c[0]):02x}{int(c[1]):02x}{int(c[2]):02x}"
        center = c.copy()
        color_defs[name] = {
            "threshold": lambda r, g, b, c=center: (
                ((r.astype(int) - int(c[0])) ** 2 +
                 (g.astype(int) - int(c[1])) ** 2 +
                 (b.astype(int) - int(c[2])) ** 2) < 2500
            ),
            "hex": hex_c,
        }

    # Transparent = background
    bg_center = bg["center"].copy()
    transparent_color = lambda r, g, b, c=bg_center: (
        ((r.astype(int) - int(c[0])) ** 2 +
         (g.astype(int) - int(c[1])) ** 2 +
         (b.astype(int) - int(c[2])) ** 2) < 2500
    )

    return color_defs, transparent_color


def _snap_to_palette(img: np.ndarray, centers: np.ndarray) -> np.ndarray:
    """Snap every pixel to the nearest color in the palette."""
    h, w = img.shape[:2]
    flat = img.reshape(-1, 3).astype(np.float32)
    dists = ((flat[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
    nearest = dists.argmin(axis=1)
    return centers[nearest].astype(np.uint8).reshape(h, w, 3)


def _snap_to_hue_families(img: np.ndarray) -> np.ndarray:
    """Group ALL pixels by hue family and snap each family to ONE representative color.

    This is THE key function for clean vectorization:
    - All yellow/gold shades → one yellow
    - All green shades → one green
    - All red shades → one red
    - All black/dark shades → one black
    - All white/light shades → one white
    - Remaining → nearest family

    Works on both flat AND gradient images because it groups by HUE, not by exact color.
    """
    h, w = img.shape[:2]
    pixels = img.reshape(-1, 3)
    r, g, b = pixels[:, 0].astype(int), pixels[:, 1].astype(int), pixels[:, 2].astype(int)

    # Define hue families — generous ranges to catch gradient variations
    # Key: yellow/gold/orange/brown all merge into "warm" to handle ribbon gradients
    families = {
        "white":  (r > 200) & (g > 200) & (b > 200),
        "black":  (r < 60) & (g < 60) & (b < 60),
        "gray":   (np.abs(r - g) < 25) & (np.abs(r - b) < 25) & (r >= 60) & (r <= 200),
        "red":    (r > 130) & (g < 90) & (b < 90),
        "green":  (g > 80) & (r < g) & (b < g),
        "blue":   (b > 120) & (r < 100) & (g < 100),
        "warm":   (r > 100) & (g > 50) & (b < 120) & (r > b) & (r > g * 0.7),  # yellow+gold+orange+brown
        "purple": (r > 70) & (b > 70) & (g < 70),
        "cyan":   (g > 80) & (b > 80) & (r < 80),
        "pink":   (r > 150) & (b > 70) & (g < 120),
    }

    # Find the representative color (median) for each family
    palette = []
    palette_names = []
    total = len(pixels)
    bg_index = -1  # Track which palette entry is background

    for name, mask in families.items():
        count = mask.sum()
        if count > total * 0.005:  # At least 0.5% of image
            family_pixels = pixels[mask]
            median_color = np.median(family_pixels, axis=0).astype(int)

            # Snap common colors to pure values
            if name == "white":
                median_color = np.array([255, 255, 255])
            elif name == "black":
                median_color = np.array([0, 0, 0])

            # Rule: if any family > 30% of pixels, it's the background
            # Lock it to pure white/black so design pixels don't leak into it
            if count > total * 0.30:
                if name == "white" or name == "gray":
                    median_color = np.array([255, 255, 255])
                    bg_index = len(palette)
                elif name == "black":
                    median_color = np.array([0, 0, 0])
                    bg_index = len(palette)

            palette.append(median_color.astype(np.float32))
            palette_names.append(name)

    if len(palette) < 2:
        return img  # Not enough families detected, return as-is

    # Assign EVERY pixel to nearest palette color
    centers = np.array(palette, dtype=np.float32)
    flat = pixels.astype(np.float32)
    dists = ((flat[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)

    # If background detected, increase its distance penalty so design pixels
    # don't accidentally get assigned to background
    if bg_index >= 0:
        dists[:, bg_index] *= 1.5  # Make background 50% harder to match

    nearest = dists.argmin(axis=1)
    result = centers[nearest].astype(np.uint8).reshape(h, w, 3)

    return result


def _detect_gradients(img: np.ndarray) -> bool:
    """Detect if an image contains significant gradient regions.

    Simple and reliable: count total unique colors in the image.
    - Flat logo/icon: < 500 unique colors (after 16-level quantization)
    - Gradient/photo: > 500 unique colors (continuous color transitions)

    This works because flat-color images have sharp boundaries with very
    few unique color values, while gradients create thousands of shades.
    """
    # Subsample for speed (every 5th pixel)
    sub = img[::5, ::5]
    # Quantize to 16-level buckets
    quantized = (sub // 16) * 16
    unique_colors = len(set(map(tuple, quantized.reshape(-1, 3))))
    # Flat logos: 3-30 unique colors. Gradient images: 50+.
    # JPEG compression adds noise, so real-world gradient images have 100+.
    return unique_colors > 50


def _map_settings_to_pipeline(settings: ConversionSettings) -> dict:
    """Map user-facing settings to potrace pipeline parameters."""
    # Detail level: higher = keep smaller components, more detail
    # Range: detail 1 -> aggressive cleanup, detail 10 -> keep fine details
    min_component = max(2000, 5000 - (settings.detail_level * 300))  # 4700 -> 2000
    turdsize = max(100, 400 - (settings.detail_level * 30))  # 370 -> 100

    # Smoothing maps to gaussian_sigma
    sigma = 1.5 + (settings.smoothing * 0.2)  # 1.7 -> 3.5
    sigma_bmp = sigma + 1.0

    # Corner detection: lower alphamax = sharper corners, higher = smoother
    # High detail wants sharp corners, high smoothing wants round corners
    alphamax = max(0.5, 1.334 - (settings.detail_level - 5) * 0.08 + (settings.smoothing - 5) * 0.06)
    # Optimize: higher = more aggressive curve simplification
    optimize = max(0.5, 2.0 - (settings.detail_level - 5) * 0.1)

    return {
        "min_component_px": min_component,
        "potrace_turdsize": turdsize,
        "potrace_alphamax": round(alphamax, 3),
        "potrace_optimize": round(optimize, 2),
        "gaussian_sigma": round(sigma, 1),
        "gaussian_sigma_bmp": round(sigma_bmp, 1),
        "target_resolution": "4K",
    }


async def convert_raster_to_vector(
    input_path: Path,
    output_dir: Path,
    settings: ConversionSettings,
    color_defs: dict | None = None,
    transparent_color=None,
    custom_colors_hex: list[str] | None = None,
) -> ConversionResult:
    """Convert raster image to vector.

    Strategy:
    - COLOR mode: vtracer (native multi-color, O(n), stacked output)
    - BINARY mode: potrace (optimal Bezier for CNC/laser, 2-color)

    Both produce: combined SVG, 300dpi BMP, transparent PNG, JSON metadata.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    stem = input_path.stem
    if len(stem) > 30:
        stem = stem[:30].rstrip("_")

    if settings.colormode.value == "binary":
        # Binary mode: use potrace CNC pipeline for optimal 2-color Bezier output
        import subprocess
        potrace_bin = "potrace"
        for candidate in ["potrace", str(Path(__file__).resolve().parent.parent.parent / "potrace.exe")]:
            try:
                subprocess.run([candidate, "--version"], capture_output=True, timeout=5)
                potrace_bin = candidate
                break
            except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
                continue
        result = await _convert_with_potrace(
            input_path, output_dir, settings, stem, color_defs, transparent_color, potrace_bin
        )
    else:
        # Color mode: use vtracer for native multi-color vectorization
        result = await _convert_with_vtracer_full(
            input_path, output_dir, settings, stem, custom_colors_hex=custom_colors_hex
        )

    elapsed = time.perf_counter() - start
    result.processing_time_ms = int(elapsed * 1000)
    return result


async def _convert_with_potrace(
    input_path: Path,
    output_dir: Path,
    settings: ConversionSettings,
    stem: str,
    color_defs: dict | None = None,
    transparent_color=None,
    potrace_bin: str = "potrace",
) -> ConversionResult:
    """Use the CNC-grade potrace pipeline from vectorize_cnc.py."""
    from app.services.vectorize_cnc import run_cnc_pipeline

    result = ConversionResult()

    # Auto-detect colors if not provided
    if color_defs is None:
        color_defs, transparent_color = _auto_detect_colors(input_path)

    # Map user settings to pipeline params
    params = _map_settings_to_pipeline(settings)

    # Run the full pipeline
    pipeline_result = run_cnc_pipeline(
        input_path=str(input_path),
        output_dir=str(output_dir),
        colors=color_defs,
        transparent_color=transparent_color,
        target_resolution=params["target_resolution"],
        gaussian_sigma=params["gaussian_sigma"],
        gaussian_sigma_bmp=params["gaussian_sigma_bmp"],
        min_component_px=params["min_component_px"],
        potrace_turdsize=params["potrace_turdsize"],
        potrace_alphamax=params.get("potrace_alphamax", 1.334),
        potrace_optimize=params.get("potrace_optimize", 2.0),
        potrace_bin=potrace_bin,
    )

    # Map pipeline outputs to result
    combined_svg = output_dir / f"{stem}_combined.svg"
    if combined_svg.exists():
        result.combined_svg_path = combined_svg

    bmp = output_dir / f"{stem}_300dpi.bmp"
    if bmp.exists():
        result.bmp_path = bmp

    png = output_dir / f"{stem}_transparent.png"
    if png.exists():
        result.png_path = png

    layers_json = output_dir / f"{stem}_layers.json"
    if layers_json.exists():
        result.layers_json_path = layers_json
        meta = json.loads(layers_json.read_text())
        for layer in meta.get("layers", []):
            result.layers.append(LayerInfo(
                name=layer["name"],
                color_hex=layer["color"],
                area_pct=layer["area_pct"],
                svg_file=layer["svg_file"],
            ))

    # Collect layer SVGs
    layers_dir = output_dir / "layers"
    if layers_dir.exists():
        result.layer_svg_paths = sorted(layers_dir.glob("*.svg"))

    # Generate viewer HTML
    try:
        from app.services.generate_viewer import generate_viewer
        viewer_path = generate_viewer(str(output_dir))
        if viewer_path.exists():
            result.viewer_html_path = viewer_path
    except Exception:
        pass  # Viewer is optional

    return result


async def _convert_with_vtracer_full(
    input_path: Path,
    output_dir: Path,
    settings: ConversionSettings,
    stem: str,
    custom_colors_hex: list[str] | None = None,
) -> ConversionResult:
    """Primary engine: raw vtracer trace + SVG color grouping post-process.

    Strategy:
    1. Upscale image for better resolution
    2. Trace with vtracer (native multi-color)
    3. Group colors by hue family in SVG output
    4. Snap near-white/near-black to pure values

    This preserves tracing quality while producing clean color layers.
    """
    import vtracer

    result = ConversionResult()
    d = settings.detail_level
    s = settings.smoothing

    # Step 1: Upscale + light bilateral filter for smoother tracing
    # Upscale: more pixels = smoother curve boundaries
    # Bilateral: smooths pixel staircase at edges WITHOUT blurring text/details
    import cv2
    upscale_target = 4800  # 3x the typical 1600px input
    with Image.open(input_path) as img:
        rgb = img.convert("RGB")
        w, h = rgb.size
        scale = upscale_target / max(w, h)
        if scale > 1.0:
            new_w, new_h = int(w * scale), int(h * scale)
            rgb = rgb.resize((new_w, new_h), Image.LANCZOS)

        # Bilateral filter on upscaled image — smooths pixel boundaries
        img_array = np.array(rgb)
        bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        smoothed = cv2.bilateralFilter(bgr, 5, 40, 40)
        rgb_smoothed = cv2.cvtColor(smoothed, cv2.COLOR_BGR2RGB)

        png_path = output_dir / "input_upscaled.png"
        Image.fromarray(rgb_smoothed).save(str(png_path), "PNG")
        input_path = png_path

    # Step 2: Trace RAW image with vtracer
    # ALWAYS use stacked mode — fills entire canvas with no gaps.
    # Params tuned for SMOOTH curves suitable for CNC cutting.
    filter_speckle = max(2, 8 - d)               # Higher = removes more tiny specks
    color_precision = min(8, max(5, d))           # Color accuracy
    layer_difference = max(4, 20 - d * 2)         # Lower = fewer gaps
    corner_threshold = max(60, 40 + s * 10)       # HIGHER = smoother corners (was 20+s*7)
    length_threshold = max(3.0, 2.0 + s * 0.8)   # LONGER segments = smoother (was 1.0+s*0.4)
    splice_threshold = max(40, 20 + s * 8)        # HIGHER = smoother splices (was 10+s*5)
    path_precision = min(8, max(3, d))
    max_iterations = min(15, max(8, d + 3))
    hierarchical = "stacked"

    combined_svg = output_dir / f"{stem}_combined.svg"

    vtracer.convert_image_to_svg_py(
        image_path=str(input_path),
        out_path=str(combined_svg),
        colormode="color",
        hierarchical=hierarchical,
        mode="spline",
        filter_speckle=filter_speckle,
        color_precision=color_precision,
        layer_difference=layer_difference,
        corner_threshold=corner_threshold,
        length_threshold=length_threshold,
        splice_threshold=splice_threshold,
        max_iterations=max_iterations,
        path_precision=path_precision,
    )

    # Step 3: Post-process SVG — group colors by hue family
    from app.services.svg_color_grouper import group_svg_colors
    try:
        _, layer_info = group_svg_colors(combined_svg, max_groups=12)
    except Exception:
        layer_info = []

    # Path smoothing disabled — was destroying SVG paths.
    # The RDP+Bezier refit approach needs more R&D before production use.
    # vtracer's native spline output is acceptable for now.

    result.combined_svg_path = combined_svg

    # Build layer list from grouper output
    layers = [
        LayerInfo(
            name=li["name"],
            color_hex=li["color"],
            area_pct=li["area_pct"],
            svg_file=f"{stem}_combined.svg",
        )
        for li in layer_info
        if li["area_pct"] >= 0.5
    ][:20]
    result.layers = layers

    # Step 4: Generate BMP and PNG from ORIGINAL input (not preprocessed)
    with Image.open(input_path) as img:
        rgb = img.convert("RGB")
        w, h = rgb.size
        bmp_path = output_dir / f"{stem}_300dpi.bmp"
        rgb.save(str(bmp_path), format="BMP", dpi=(300, 300))
        result.bmp_path = bmp_path
        rgba = img.convert("RGBA")
        png_path = output_dir / f"{stem}_transparent.png"
        rgba.save(str(png_path), dpi=(300, 300))
        result.png_path = png_path

    # Step 5: Write metadata JSON
    meta = {
        "source": stem,
        "engine": "vtracer",
        "dimensions": {"width": w, "height": h},
        "dpi": 300,
        "layers": [
            {"name": l.name, "color": l.color_hex, "area_pct": l.area_pct, "svg_file": l.svg_file}
            for l in layers
        ],
    }
    layers_json = output_dir / f"{stem}_layers.json"
    layers_json.write_text(json.dumps(meta, indent=2))
    result.layers_json_path = layers_json

    # Step 6: Generate HTML viewer
    try:
        from app.services.generate_viewer import generate_viewer
        viewer_path = generate_viewer(str(output_dir))
        if viewer_path.exists():
            result.viewer_html_path = viewer_path
    except Exception:
        pass

    return result


def _nameColor(rgb: list) -> str:
    """Name a color based on RGB values."""
    r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])
    if r > 200 and g > 200 and b > 200: return "white"
    if r < 40 and g < 40 and b < 40: return "black"
    if r > 150 and g < 80 and b < 80: return "red"
    if g > 150 and r < 80 and b < 80: return "green"
    if b > 150 and r < 80 and g < 80: return "blue"
    if r > 180 and g > 150 and b < 80: return "yellow"
    if r > 180 and g > 100 and b < 60: return "orange"
    if r > 100 and g > 100 and b > 100 and r < 200: return "gray"
    return f"color_{r:02x}{g:02x}{b:02x}"
