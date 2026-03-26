#!/usr/bin/env python3
"""
CNC-Grade Raster -> Layered Vector Pipeline
============================================
Production pipeline using potrace for mathematically optimal Bezier curves.
Zero zigzag, zero noise, zero anti-alias artifacts.

Usage:
    # As module
    from vectorize_cnc import run_cnc_pipeline
    results = run_cnc_pipeline(
        input_path='logo.png',
        output_dir='./output',
        colors={
            'red': {'threshold': lambda r,g,b: (r > 120) & (g < 80) & (b < 80), 'hex': '#c80f12'},
            'white': {'threshold': lambda r,g,b: (r > 200) & (g > 200) & (b > 200), 'hex': '#ffffff'},
        },
        transparent_color='black',
    )

    # CLI
    python vectorize_cnc.py <image> [4K|8K]
    (CLI uses auto-detected colors -- module usage preferred for control)
"""

import subprocess
import sys
import re
import json
import numpy as np
from pathlib import Path
from typing import Optional

from PIL import Image, ImageFilter
from scipy import ndimage
from scipy.ndimage import gaussian_filter


# --- Resolution Map ----------------------------------------------------------

RESOLUTION_MAP = {
    "4K": (3840, 2160),
    "8K": (7680, 4320),
}


# --- Step 0: Auto-Crop to Design Content ------------------------------------

def _auto_crop(img: Image.Image, padding_pct: float = 0.02) -> Image.Image:
    """Crop image to actual design content, removing empty background borders.

    Detects background color from the 4 corners, then finds the bounding box
    where non-background pixels exist. Adds small padding. This eliminates
    stray rays, shadows, and gradients that AI image generators add at edges.
    """
    pixels = np.array(img)
    h, w = pixels.shape[:2]

    # Sample corners to detect background color (take median of corner pixels)
    corner_size = max(10, min(h, w) // 20)
    corners = np.concatenate([
        pixels[:corner_size, :corner_size].reshape(-1, 3),
        pixels[:corner_size, -corner_size:].reshape(-1, 3),
        pixels[-corner_size:, :corner_size].reshape(-1, 3),
        pixels[-corner_size:, -corner_size:].reshape(-1, 3),
    ])
    bg_color = np.median(corners, axis=0).astype(int)

    # Create mask of pixels that differ significantly from background
    diff = np.sqrt(np.sum((pixels.astype(float) - bg_color.astype(float)) ** 2, axis=2))
    content_mask = diff > 50  # threshold: 50 RGB euclidean distance from background

    # Find bounding box of content
    rows = np.any(content_mask, axis=1)
    cols = np.any(content_mask, axis=0)

    if not rows.any() or not cols.any():
        return img  # no content detected, return as-is

    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]

    # Add padding
    pad_h = int((rmax - rmin) * padding_pct)
    pad_w = int((cmax - cmin) * padding_pct)
    rmin = max(0, rmin - pad_h)
    rmax = min(h - 1, rmax + pad_h)
    cmin = max(0, cmin - pad_w)
    cmax = min(w - 1, cmax + pad_w)

    cropped = img.crop((cmin, rmin, cmax + 1, rmax + 1))
    new_w, new_h = cropped.size
    if new_w < w * 0.5 or new_h < h * 0.5:
        # Cropped too aggressively, keep original
        print(f"  Auto-crop skipped (would remove >50% of image)")
        return img

    print(f"  Cropped: {w}x{h} -> {new_w}x{new_h} (removed {((w*h - new_w*new_h) / (w*h) * 100):.0f}% border)")
    return cropped


# --- Step 1: Load & Upscale -------------------------------------------------

def load_and_upscale(input_path: str, target: str = "4K") -> Image.Image:
    """Load image and upscale to target resolution using Lanczos."""
    img = Image.open(input_path).convert("RGB")
    w0, h0 = img.size
    target_w, target_h = RESOLUTION_MAP[target]
    scale = max(target_w / w0, target_h / h0)

    if scale <= 1.0:
        print(f"  Image {w0}x{h0} already >= {target}. Keeping original.")
        return img

    new_w, new_h = int(w0 * scale), int(h0 * scale)
    print(f"  Upscaling: {w0}x{h0} -> {new_w}x{new_h} (x{scale:.2f})")
    return img.resize((new_w, new_h), Image.LANCZOS)


# --- Step 2: Median Filter --------------------------------------------------

def median_filter(img: Image.Image, kernel_size: int = 7) -> Image.Image:
    """Median filter dissolves anti-alias pixels before thresholding.

    This is the critical preprocessing step. The median filter replaces each
    pixel with the median of its NxN neighborhood, which snaps transition
    pixels to the dominant nearby color WITHOUT blurring actual edges.
    """
    print(f"  Median filter: kernel={kernel_size}")
    return img.filter(ImageFilter.MedianFilter(size=kernel_size))


# --- Step 3: Hard Threshold -------------------------------------------------

def hard_threshold(
    pixels: np.ndarray,
    color_defs: dict,
    transparent_color: Optional[str] = None,
) -> dict:
    """Apply hard thresholds to classify every pixel into a color layer.

    Args:
        pixels: (H, W, 3) uint8 RGB array
        color_defs: Dict of {name: {'threshold': lambda, 'hex': str}}
        transparent_color: Name of the color that becomes transparent (no layer).
                          Can also be a threshold lambda for direct definition.

    Returns:
        Dict of {name: boolean_mask} for each non-transparent color
    """
    r, g, b = pixels[:, :, 0], pixels[:, :, 1], pixels[:, :, 2]
    h, w = r.shape

    # Apply each threshold
    masks = {}
    assigned = np.zeros((h, w), dtype=bool)

    # Handle transparent region
    if transparent_color is not None:
        if callable(transparent_color):
            trans_mask = transparent_color(r, g, b)
        elif transparent_color in color_defs:
            trans_mask = color_defs[transparent_color]["threshold"](r, g, b)
        else:
            # Try common background colors
            bg_thresholds = {
                "black": lambda r, g, b: (r < 40) & (g < 40) & (b < 40),
                "white": lambda r, g, b: (r > 220) & (g > 220) & (b > 220),
            }
            if transparent_color.lower() in bg_thresholds:
                trans_mask = bg_thresholds[transparent_color.lower()](r, g, b)
            else:
                trans_mask = np.zeros((h, w), dtype=bool)
        assigned |= trans_mask

    # Apply named color thresholds
    for name, cdef in color_defs.items():
        if transparent_color and name == transparent_color:
            continue
        mask = cdef["threshold"](r, g, b) & ~assigned
        masks[name] = mask
        assigned |= mask
        pct = mask.sum() / (h * w) * 100
        print(f"  {name}: {pct:.1f}%")

    # Snap leftover pixels to nearest defined color
    leftover = ~assigned
    leftover_count = leftover.sum()
    if leftover_count > 0:
        print(f"  Leftover: {leftover_count} pixels ({leftover_count/(h*w)*100:.1f}%) -> snapping to nearest...")
        lo_pixels = pixels[leftover].astype(float)
        ly, lx = np.where(leftover)

        # Build center array from hex values
        active_names = [n for n in color_defs if n != transparent_color]
        centers = []
        for name in active_names:
            hex_c = color_defs[name]["hex"]
            centers.append([
                int(hex_c[1:3], 16),
                int(hex_c[3:5], 16),
                int(hex_c[5:7], 16),
            ])
        centers = np.array(centers, dtype=float)

        # Euclidean distance
        dists = np.sqrt(((lo_pixels[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2))
        nearest = dists.argmin(axis=1)

        for i, name in enumerate(active_names):
            match = nearest == i
            if match.any():
                masks[name][ly[match], lx[match]] = True

    return masks


# --- Step 4: Morphological Cleanup ------------------------------------------

def morphological_cleanup(
    mask: np.ndarray,
    name: str,
    min_component_px: int = 500,
    closing_iters: int = 3,
    opening_iters: int = 2,
) -> np.ndarray:
    """Remove specks, close gaps, and smooth edges on a binary mask.

    1. Label connected components -> remove those < min_component_px
    2. Binary closing (dilate->erode) -> fills small gaps in boundaries
    3. Binary opening (erode->dilate) -> smooths jagged edges
    4. Final closing -> restores any thinned features
    """
    struct = ndimage.generate_binary_structure(2, 2)  # 8-connectivity

    # Remove small components
    labeled, n = ndimage.label(mask, structure=struct)
    if n > 0:
        sizes = ndimage.sum(mask, labeled, range(1, n + 1))
        cleaned = np.zeros_like(mask)
        kept = 0
        for i, sz in enumerate(sizes):
            if sz >= min_component_px:
                cleaned[labeled == (i + 1)] = True
                kept += 1
        print(f"  {name}: {n} components -> kept {kept} (>={min_component_px}px)")
    else:
        cleaned = mask.copy()

    # Close gaps -> smooth -> close again
    cleaned = ndimage.binary_closing(cleaned, structure=struct, iterations=closing_iters)
    cleaned = ndimage.binary_opening(cleaned, structure=struct, iterations=opening_iters)
    cleaned = ndimage.binary_closing(cleaned, structure=struct, iterations=closing_iters)

    return cleaned


# --- Step 5: Resolve Overlaps & Fill Gaps ------------------------------------

def resolve_and_fill(masks: dict, shape: tuple) -> dict:
    """Ensure no pixel belongs to multiple layers, and fill unassigned gaps.

    Priority: first defined layer wins at overlaps.
    Gaps: assigned to nearest color via distance transform.
    IMPORTANT: When only 1 color layer exists, gap-fill is SKIPPED -- otherwise
    the entire background gets forced into the single design layer.
    """
    h, w = shape
    assigned = np.zeros((h, w), dtype=bool)
    ordered_names = list(masks.keys())

    # Priority pass: first layer wins
    for name in ordered_names:
        overlap = masks[name] & assigned
        if overlap.any():
            masks[name][overlap] = False
        assigned |= masks[name]

    # Fill gaps -- BUT only when 2+ color layers exist
    # With 1 layer, background pixels must stay as background (transparent)
    if len(masks) >= 2:
        unassigned = ~assigned
        gap_count = unassigned.sum()
        if gap_count > 0:
            # Distance transform from each layer
            distances = {}
            for name, mask in masks.items():
                distances[name] = ndimage.distance_transform_edt(~mask)

            gy, gx = np.where(unassigned)
            dist_stack = np.stack([distances[n][gy, gx] for n in ordered_names], axis=1)
            nearest = dist_stack.argmin(axis=1)

            for i, name in enumerate(ordered_names):
                match = nearest == i
                if match.any():
                    masks[name][gy[match], gx[match]] = True

            print(f"  Filled {gap_count} gap pixels via distance transform")
    else:
        print(f"  Single-layer design -- skipping gap-fill (background stays transparent)")

    return masks


# --- Step 6: Gaussian Edge Smooth --------------------------------------------

def smooth_mask_edges(mask: np.ndarray, sigma: float = 2.0) -> np.ndarray:
    """Gaussian blur the mask boundary then re-threshold.

    This converts pixel staircase edges into smooth contours that potrace
    can fit clean Bezier curves through. The 0.5 threshold keeps the
    boundary position accurate -- only the jaggedness is removed.
    """
    blurred = gaussian_filter(mask.astype(np.float64), sigma=sigma)
    return (blurred > 0.5).astype(bool)


# --- Step 7: Potrace Vectorization ------------------------------------------

def potrace_to_svg(
    mask: np.ndarray,
    color_hex: str,
    name: str,
    output_dir: Path,
    potrace_alphamax: float = 1.334,
    potrace_optimize: float = 2.0,
    potrace_turdsize: int = 100,
    potrace_bin: str = "potrace",
) -> str:
    """Trace a binary mask with potrace and produce flat-coordinate SVG.

    Potrace fits mathematically optimal cubic Bezier curves to the boundary.
    The transform from potrace's internal coordinates is baked directly into
    the path data -- the output SVG has zero <g transform> tags.
    """
    h, w = mask.shape

    # Potrace traces BLACK pixels -- invert our mask
    bw = np.where(mask, 0, 255).astype(np.uint8)

    tmp_pgm = output_dir / f"_tmp_{name}.pgm"
    tmp_svg = output_dir / f"_tmp_{name}_raw.svg"

    Image.fromarray(bw, "L").save(str(tmp_pgm))

    result = subprocess.run(
        [
            potrace_bin, str(tmp_pgm),
            "-s", "-o", str(tmp_svg),
            "-a", str(potrace_alphamax),
            "-O", str(potrace_optimize),
            "-t", str(potrace_turdsize),
            "--flat",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"  ERROR potrace {name}: {result.stderr}")
        tmp_pgm.unlink(missing_ok=True)
        return ""

    raw = tmp_svg.read_text()

    # Extract potrace's transform: translate(tx,ty) scale(sx,sy)
    t_match = re.search(
        r"translate\(([-\d.]+),([-\d.]+)\)\s*scale\(([-\d.]+),([-\d.]+)\)", raw
    )
    if t_match:
        tx, ty = float(t_match.group(1)), float(t_match.group(2))
        sx, sy = float(t_match.group(3)), float(t_match.group(4))
    else:
        tx, ty, sx, sy = 0, h, 1, -1

    # Extract all path d="" values
    path_ds = re.findall(r'd="([^"]*)"', raw)

    # Transform each path's coordinates from potrace space -> pixel space
    def transform_d(d):
        result_parts = []
        pos = 0
        chars = d.strip()

        while pos < len(chars):
            while pos < len(chars) and chars[pos] in " \t\n\r":
                pos += 1
            if pos >= len(chars):
                break

            cmd = chars[pos]
            pos += 1

            if cmd in "Zz":
                result_parts.append("Z")
                continue

            num_str = ""
            while pos < len(chars) and chars[pos] not in "MmCcLlZzHhVvSsQqTtAa":
                num_str += chars[pos]
                pos += 1

            nums = [float(n) for n in re.findall(r"-?[\d.]+(?:e[+-]?\d+)?", num_str)]

            if cmd == "M":
                out = []
                for j in range(0, len(nums), 2):
                    if j + 1 < len(nums):
                        x = nums[j] * sx + tx
                        y = nums[j + 1] * sy + ty
                        out.append(f"{x:.1f} {y:.1f}")
                result_parts.append(f"M{' '.join(out)}")

            elif cmd == "c":
                out = []
                for j in range(0, len(nums), 6):
                    if j + 5 < len(nums):
                        vals = [
                            nums[j] * sx, nums[j + 1] * sy,
                            nums[j + 2] * sx, nums[j + 3] * sy,
                            nums[j + 4] * sx, nums[j + 5] * sy,
                        ]
                        out.append(" ".join(f"{v:.1f}" for v in vals))
                result_parts.append(f"c{' '.join(out)}")

            elif cmd == "l":
                out = []
                for j in range(0, len(nums), 2):
                    if j + 1 < len(nums):
                        out.append(f"{nums[j]*sx:.1f} {nums[j+1]*sy:.1f}")
                result_parts.append(f"l{' '.join(out)}")

            elif cmd == "m":
                out = []
                for j in range(0, len(nums), 2):
                    if j + 1 < len(nums):
                        out.append(f"{nums[j]*sx:.1f} {nums[j+1]*sy:.1f}")
                result_parts.append(f"m{' '.join(out)}")

            else:
                result_parts.append(cmd + num_str)

        return " ".join(result_parts)

    flat_paths = [transform_d(d) for d in path_ds]

    # Build path XML
    path_xml = "\n".join(
        f'  <path fill="{color_hex}" stroke="none" d="{d}"/>' for d in flat_paths
    )

    # Save individual layer SVG
    layer_svg = (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg"\n'
        f'     width="{w}" height="{h}"\n'
        f'     viewBox="0 0 {w} {h}">\n'
        f"{path_xml}\n"
        f"</svg>"
    )

    layer_path = output_dir / "layers" / f"{name}.svg"
    layer_path.write_text(layer_svg, encoding="utf-8")

    # Cleanup
    tmp_pgm.unlink(missing_ok=True)
    tmp_svg.unlink(missing_ok=True)

    size_kb = layer_path.stat().st_size / 1024
    print(f"  {name}: {len(flat_paths)} paths -> {size_kb:.0f} KB")

    return path_xml


# --- Main Pipeline -----------------------------------------------------------

def run_cnc_pipeline(
    input_path: str,
    output_dir: str,
    colors: dict,
    transparent_color: Optional[str] = "black",
    target_resolution: str = "4K",
    dpi: int = 300,
    median_kernel: int = 7,
    gaussian_sigma: float = 2.5,
    gaussian_sigma_bmp: float = 3.5,
    min_component_px: int = 2000,
    potrace_turdsize: int = 200,
    potrace_bin: str = "potrace",
) -> dict:
    """
    Run the complete CNC-grade raster->vector pipeline.

    Args:
        input_path: Path to source raster image
        output_dir: Directory for all outputs
        colors: Dict defining each color layer:
            {
                'name': {
                    'threshold': lambda r,g,b: boolean_mask,
                    'hex': '#rrggbb',
                },
                ...
            }
        transparent_color: Color name or 'black'/'white' that becomes transparent.
            Set to None to keep all colors as layers.
        target_resolution: '4K' or '8K'
        dpi: DPI for BMP output (default 300)
        median_kernel: Median filter kernel size (default 7, must be odd)
        gaussian_sigma: Edge smoothing sigma for SVG tracing (default 2.5)
        gaussian_sigma_bmp: Stronger smoothing sigma for BMP/PNG raster output (default 3.5)
        min_component_px: Minimum component size in pixels (default 2000)
        potrace_turdsize: Potrace speckle filter threshold (default 200)

    Returns:
        Dict with paths to all generated files
    """
    input_path = Path(input_path)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "layers").mkdir(exist_ok=True)

    stem = input_path.stem
    # Clean up filename for output
    if len(stem) > 30:
        stem = stem[:30].rstrip("_")

    print(f"\n{'='*60}")
    print(f"  CNC-GRADE VECTOR PIPELINE")
    print(f"  Input:  {input_path.name}")
    print(f"  Target: {target_resolution} @ {dpi} DPI")
    print(f"  Layers: {', '.join(colors.keys())}")
    print(f"  Transparent: {transparent_color}")
    print(f"{'='*60}")

    # [1] Load & Upscale
    print(f"\n[1/7] Loading & upscaling...")
    img = load_and_upscale(str(input_path), target_resolution)

    # [1b] Auto-crop to design content
    # Detect background from corners, then crop to where non-background pixels exist
    print(f"  Auto-cropping to design content...")
    img = _auto_crop(img)

    # [2] Median Filter
    print(f"\n[2/7] Median filtering...")
    img = median_filter(img, median_kernel)
    pixels = np.array(img)
    h, w = pixels.shape[:2]

    # [3] Hard Threshold
    print(f"\n[3/7] Hard thresholding...")
    masks = hard_threshold(pixels, colors, transparent_color)

    # [4] Morphological Cleanup
    print(f"\n[4/7] Morphological cleanup...")
    for name in list(masks.keys()):
        masks[name] = morphological_cleanup(
            masks[name], name, min_component_px=min_component_px
        )

    # [5] Resolve overlaps & fill gaps
    print(f"\n[5/7] Resolving overlaps & gaps...")
    masks = resolve_and_fill(masks, (h, w))

    # [6] Gaussian smooth + Potrace
    print(f"\n[6/7] Smoothing edges (sigma={gaussian_sigma}) & tracing with potrace...")
    layer_svgs = {}
    layer_info = []

    # Sort layers: largest area first (bottom) -> smallest area last (top)
    sorted_names = sorted(masks.keys(), key=lambda n: masks[n].sum(), reverse=True)

    for name in sorted_names:
        mask = masks[name]
        smoothed = smooth_mask_edges(mask, sigma=gaussian_sigma)
        hex_color = colors[name]["hex"]
        path_xml = potrace_to_svg(
            smoothed, hex_color, f"{stem}_{name}", out,
            potrace_turdsize=potrace_turdsize,
            potrace_bin=potrace_bin,
        )
        layer_svgs[name] = path_xml
        area_pct = round(mask.sum() / (h * w) * 100, 1)
        layer_info.append({
            "name": name,
            "color": hex_color,
            "area_pct": area_pct,
            "svg_file": f"layers/{stem}_{name}.svg",
        })

    # [7] Export all formats
    print(f"\n[7/7] Exporting combined SVG, BMP, PNG...")

    # Combined SVG — layers ordered bottom (largest/dilated) to top (smallest/sharp)
    groups = "\n".join(
        f'  <g id="layer-{name}">\n{layer_svgs[name]}\n  </g>'
        for name in sorted_names
        if name in layer_svgs
    )
    combined = (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg"\n'
        f'     width="{w}" height="{h}"\n'
        f'     viewBox="0 0 {w} {h}">\n'
        f"  <!-- CNC-Grade Vector | Potrace optimal curves -->\n"
        f"{groups}\n"
        f"</svg>"
    )
    combined_path = out / f"{stem}_combined.svg"
    combined_path.write_text(combined, encoding="utf-8")

    # BMP: uses STRONGER Gaussian than SVG + second speck cleanup pass
    # This gives BMP edges quality closer to SVG's potrace curves
    print(f"  BMP: extra smoothing (sigma={gaussian_sigma_bmp}) + speck cleanup...")
    struct_bmp = ndimage.generate_binary_structure(2, 2)
    bmp_arr = np.full((h, w, 3), 255, dtype=np.uint8)
    for name, mask in masks.items():
        hex_c = colors[name]["hex"]
        r_c = int(hex_c[1:3], 16)
        g_c = int(hex_c[3:5], 16)
        b_c = int(hex_c[5:7], 16)
        # Stronger Gaussian for BMP
        bmp_smooth = smooth_mask_edges(mask, sigma=gaussian_sigma_bmp)
        # Second speck cleanup on the BMP-smoothed mask
        labeled_bmp, n_bmp = ndimage.label(bmp_smooth, structure=struct_bmp)
        if n_bmp > 0:
            sizes_bmp = ndimage.sum(bmp_smooth, labeled_bmp, range(1, n_bmp + 1))
            for i, sz in enumerate(sizes_bmp):
                if sz < min_component_px:
                    bmp_smooth[labeled_bmp == (i + 1)] = False
        bmp_arr[bmp_smooth] = [r_c, g_c, b_c]
    bmp_path = out / f"{stem}_300dpi.bmp"
    Image.fromarray(bmp_arr).save(str(bmp_path), format="BMP", dpi=(dpi, dpi))

    # Verify: zero stray pixels in border region
    border = np.zeros((h, w), dtype=bool)
    border[:50, :] = True; border[-50:, :] = True
    border[:, :50] = True; border[:, -50:] = True
    border_colored = (bmp_arr[border, 0] != 255) | (bmp_arr[border, 1] != 255) | (bmp_arr[border, 2] != 255)
    # Only count non-white pixels that aren't expected (crude check)
    border_stray = border_colored.sum()
    if border_stray > 0:
        print(f"  [WARN] Border has {border_stray} non-white pixels (may be expected if design reaches edge)")
    else:
        print(f"  [OK] Border clean: 0 stray pixels")

    # PNG (transparent background) -- also uses stronger smoothing
    png_arr = np.zeros((h, w, 4), dtype=np.uint8)
    for name, mask in masks.items():
        hex_c = colors[name]["hex"]
        r_c = int(hex_c[1:3], 16)
        g_c = int(hex_c[3:5], 16)
        b_c = int(hex_c[5:7], 16)
        png_smooth = smooth_mask_edges(mask, sigma=gaussian_sigma_bmp)
        # Same speck cleanup
        labeled_png, n_png = ndimage.label(png_smooth, structure=struct_bmp)
        if n_png > 0:
            sizes_png = ndimage.sum(png_smooth, labeled_png, range(1, n_png + 1))
            for i, sz in enumerate(sizes_png):
                if sz < min_component_px:
                    png_smooth[labeled_png == (i + 1)] = False
        png_arr[png_smooth] = [r_c, g_c, b_c, 255]
    png_path = out / f"{stem}_transparent.png"
    Image.fromarray(png_arr, "RGBA").save(str(png_path), dpi=(dpi, dpi))

    # Metadata JSON
    meta = {
        "source": stem,
        "engine": "potrace",
        "dimensions": {"width": w, "height": h},
        "dpi": dpi,
        "transparent": str(transparent_color) if transparent_color else None,
        "layers": layer_info,
    }
    meta_path = out / f"{stem}_layers.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    # Summary
    results = {
        "combined_svg": str(combined_path),
        "bmp": str(bmp_path),
        "png": str(png_path),
        "metadata": str(meta_path),
        "layers_dir": str(out / "layers"),
        "output_dir": str(out),
    }

    print(f"\n{'='*60}")
    print(f"  [DONE] CNC-GRADE PIPELINE COMPLETE")
    for f in sorted(out.rglob("*")):
        if f.is_file() and not f.name.startswith("_"):
            sz = f.stat().st_size
            u = "KB" if sz < 1024 * 1024 else "MB"
            v = sz / 1024 if u == "KB" else sz / (1024 * 1024)
            print(f"  {str(f.relative_to(out)):45s} {v:8.1f} {u}")
    print(f"{'='*60}")

    return results


# --- CLI ---------------------------------------------------------------------

if __name__ == "__main__":
    from sklearn.cluster import KMeans
    from collections import Counter

    if len(sys.argv) < 2:
        print("Usage: python vectorize_cnc.py <image_path> [4K|8K]")
        print("\nCLI mode auto-detects colors via KMeans.")
        print("For precise control, use as a Python module (see docstring).")
        sys.exit(1)

    img_path = sys.argv[1]
    resolution = sys.argv[2] if len(sys.argv) > 2 else "4K"

    # Auto-detect dominant colors
    print("Auto-detecting colors...")
    img = Image.open(img_path).convert("RGB")
    pixels = np.array(img).reshape(-1, 3)
    quantized = (pixels // 48) * 48
    counts = Counter(map(tuple, quantized))
    top_colors = counts.most_common(6)

    print("\nDetected palette:")
    for color, count in top_colors:
        pct = count / len(pixels) * 100
        hex_c = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
        print(f"  {hex_c} -> {pct:.1f}%")

    print("\nFor precise control, use the Python module API.")
    print("CLI auto-mode will use KMeans with 4 clusters.\n")

    # Simple CLI: use KMeans to find 4 colors, largest = transparent
    kmeans = KMeans(n_clusters=4, n_init=10, random_state=42)
    kmeans.fit(pixels[::10])  # subsample for speed
    centers = kmeans.cluster_centers_.astype(int)
    labels = kmeans.predict(pixels)
    counts = np.bincount(labels)
    largest = counts.argmax()

    color_defs = {}
    for i, center in enumerate(centers):
        if i == largest:
            continue
        name = f"color_{i}"
        hex_c = f"#{center[0]:02x}{center[1]:02x}{center[2]:02x}"
        # Create threshold: within 60 RGB distance of center
        c = center.copy()
        color_defs[name] = {
            "threshold": lambda r, g, b, c=c: (
                ((r.astype(int) - int(c[0])) ** 2 +
                 (g.astype(int) - int(c[1])) ** 2 +
                 (b.astype(int) - int(c[2])) ** 2) < 3600
            ),
            "hex": hex_c,
        }

    trans_center = centers[largest]
    trans_hex = f"#{trans_center[0]:02x}{trans_center[1]:02x}{trans_center[2]:02x}"
    print(f"Transparent (background): {trans_hex}")

    run_cnc_pipeline(
        input_path=img_path,
        output_dir=f"./cnc_output",
        colors=color_defs,
        transparent_color=lambda r, g, b, c=trans_center: (
            ((r.astype(int) - int(c[0])) ** 2 +
             (g.astype(int) - int(c[1])) ** 2 +
             (b.astype(int) - int(c[2])) ** 2) < 3600
        ),
        target_resolution=resolution,
    )
