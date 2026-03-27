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


def analyze_colors(input_path: Path, max_colors: int = 10) -> list[dict]:
    """Analyze dominant colors in an image for threshold definition."""
    img = Image.open(input_path).convert("RGB")
    pixels = np.array(img).reshape(-1, 3)
    quantized = (pixels // 32) * 32
    counts = Counter(map(tuple, quantized))
    total = len(pixels)

    results = []
    for color, count in counts.most_common(max_colors):
        pct = count / total * 100
        hex_c = f"#{int(color[0]):02x}{int(color[1]):02x}{int(color[2]):02x}"
        results.append({
            "rgb": [int(color[0]), int(color[1]), int(color[2])],
            "hex": hex_c,
            "percentage": round(float(pct), 1),
            "pixel_count": int(count),
        })
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
        result = await _convert_with_vtracer_full(input_path, output_dir, settings, stem)

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
) -> ConversionResult:
    """Primary engine: vtracer for full-color native vectorization.

    vtracer handles multi-color images natively — no manual color separation,
    no KMeans, no morphological cleanup needed. O(n) algorithm, stacked output.
    """
    import vtracer
    import xml.etree.ElementTree as ET
    from collections import Counter

    result = ConversionResult()

    # Ensure PNG input (vtracer works best with PNG)
    if input_path.suffix.lower() not in (".png", ".bmp"):
        png_path = output_dir / "input.png"
        with Image.open(input_path) as img:
            img.save(png_path, "PNG")
        input_path = png_path

    # Map user settings to vtracer parameters
    # Detail: higher = more detail (lower speckle filter, higher precision)
    filter_speckle = max(2, 12 - settings.detail_level)  # 10->2, 1->11
    color_precision = max(3, min(8, settings.detail_level))  # 3->8
    layer_difference = max(10, 40 - settings.detail_level * 3)  # 37->10

    # Smoothing: higher = smoother curves
    corner_threshold = max(20, 30 + settings.smoothing * 8)  # 38->110
    length_threshold = max(2.0, settings.smoothing * 1.2)  # 1.2->12
    splice_threshold = max(20, settings.smoothing * 6)  # 6->60

    combined_svg = output_dir / f"{stem}_combined.svg"

    vtracer.convert_image_to_svg_py(
        image_path=str(input_path),
        out_path=str(combined_svg),
        colormode="color",
        hierarchical="stacked",
        mode="spline",
        filter_speckle=filter_speckle,
        color_precision=color_precision,
        layer_difference=layer_difference,
        corner_threshold=corner_threshold,
        length_threshold=length_threshold,
        splice_threshold=splice_threshold,
        max_iterations=10,
        path_precision=3,
    )
    result.combined_svg_path = combined_svg

    # Parse SVG to extract layer info (colors + paths)
    layers = []
    try:
        tree = ET.parse(str(combined_svg))
        root = tree.getroot()
        ns = "{http://www.w3.org/2000/svg}"
        all_paths = root.findall(f".//{ns}path") or root.findall(".//path")

        # Count colors
        color_counts = Counter()
        for p in all_paths:
            fill = p.get("fill", "").upper()
            if fill and fill != "NONE":
                color_counts[fill] += len(p.get("d", ""))

        total_d = sum(color_counts.values()) or 1
        for color, d_len in color_counts.most_common():
            r = int(color[1:3], 16) if len(color) == 7 else 0
            g = int(color[3:5], 16) if len(color) == 7 else 0
            b = int(color[5:7], 16) if len(color) == 7 else 0
            name = _nameColor([r, g, b])
            layers.append(LayerInfo(
                name=name,
                color_hex=color.lower(),
                area_pct=round(d_len / total_d * 100, 1),
                svg_file=f"{stem}_combined.svg",
            ))
    except Exception:
        pass

    result.layers = layers

    # Generate BMP (300 DPI) and PNG (transparent) from input
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

    # Generate HTML layer viewer
    try:
        from app.services.generate_viewer import generate_viewer
        viewer_path = generate_viewer(str(output_dir))
        if viewer_path.exists():
            result.viewer_html_path = viewer_path
    except Exception:
        pass

    # Write metadata JSON
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
