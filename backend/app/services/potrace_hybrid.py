"""
Potrace Hybrid Engine — per-color-layer potrace tracing.

Produces CNC-grade mathematically optimal Bezier curves by:
1. Detecting color families in the image (hue-based)
2. Creating a binary mask for each color family
3. Upscaling + Gaussian smoothing each mask
4. Tracing each mask with potrace (optimal Bezier fitting)
5. Combining all layers into one SVG

This produces the HIGHEST quality vector output possible —
smoother than vtracer at any setting.
"""

import subprocess
import re
import json
import numpy as np
from pathlib import Path
from PIL import Image
from scipy import ndimage
from scipy.ndimage import gaussian_filter


def _find_potrace() -> str | None:
    """Find potrace binary."""
    for candidate in ["potrace", str(Path(__file__).resolve().parent.parent.parent / "potrace.exe")]:
        try:
            subprocess.run([candidate, "--version"], capture_output=True, timeout=5)
            return candidate
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            continue
    return None


def _detect_color_families(img: np.ndarray, min_pct: float = 0.5) -> list[dict]:
    """Detect dominant hue families in image."""
    h, w = img.shape[:2]
    pixels = img.reshape(-1, 3)
    r, g, b = pixels[:, 0].astype(int), pixels[:, 1].astype(int), pixels[:, 2].astype(int)
    total = len(pixels)

    families = {
        "white":  (r > 200) & (g > 200) & (b > 200),
        "black":  (r < 60) & (g < 60) & (b < 60),
        "gray":   (np.abs(r - g) < 25) & (np.abs(r - b) < 25) & (r >= 60) & (r <= 200),
        "red":    (r > 130) & (g < 90) & (b < 90),
        "green":  (g > 80) & (r < g) & (b < g),
        "blue":   (b > 120) & (r < 100) & (g < 100),
        "warm":   (r > 100) & (g > 50) & (b < 120) & (r > b) & (r > g * 0.7),
        "purple": (r > 70) & (b > 70) & (g < 70),
        "cyan":   (g > 80) & (b > 80) & (r < 80),
        "pink":   (r > 150) & (b > 70) & (g < 120),
    }

    detected = []
    for name, mask_flat in families.items():
        count = mask_flat.sum()
        pct = count / total * 100
        if pct >= min_pct:
            family_pixels = pixels[mask_flat]
            median_color = np.median(family_pixels, axis=0).astype(int)
            if name == "white":
                median_color = np.array([255, 255, 255])
            elif name == "black":
                median_color = np.array([0, 0, 0])

            hex_c = f"#{int(median_color[0]):02x}{int(median_color[1]):02x}{int(median_color[2]):02x}"
            mask_2d = mask_flat.reshape(h, w)
            detected.append({
                "name": name,
                "hex": hex_c,
                "rgb": median_color.tolist(),
                "pct": round(pct, 1),
                "mask": mask_2d,
            })

    # Sort by percentage (largest = background)
    detected.sort(key=lambda x: x["pct"], reverse=True)
    return detected


def _trace_mask_with_potrace(
    mask: np.ndarray,
    color_hex: str,
    name: str,
    output_dir: Path,
    potrace_bin: str,
    sigma: float = 2.5,
    alphamax: float = 1.334,
    turdsize: int = 100,
) -> str:
    """Trace a binary mask with potrace. Returns SVG path XML."""
    h, w = mask.shape

    # Gaussian smooth the mask edges for smoother Bezier curves
    smoothed = gaussian_filter(mask.astype(np.float64), sigma=sigma)
    smoothed = (smoothed > 0.5).astype(np.uint8)

    # Remove small components
    struct = ndimage.generate_binary_structure(2, 2)
    labeled, n = ndimage.label(smoothed, structure=struct)
    if n > 0:
        sizes = ndimage.sum(smoothed, labeled, range(1, n + 1))
        for i, sz in enumerate(sizes):
            if sz < turdsize:
                smoothed[labeled == (i + 1)] = 0

    # Potrace traces BLACK pixels — invert
    bw = np.where(smoothed, 0, 255).astype(np.uint8)

    tmp_pgm = output_dir / f"_tmp_{name}.pgm"
    tmp_svg = output_dir / f"_tmp_{name}_raw.svg"

    Image.fromarray(bw, "L").save(str(tmp_pgm))

    result = subprocess.run(
        [potrace_bin, str(tmp_pgm),
         "-s", "-o", str(tmp_svg),
         "-a", str(alphamax),
         "-O", "2.0",
         "-t", str(turdsize),
         "--flat"],
        capture_output=True, text=True, timeout=60,
    )

    if result.returncode != 0:
        tmp_pgm.unlink(missing_ok=True)
        return ""

    raw = tmp_svg.read_text()

    # Extract potrace transform
    t_match = re.search(
        r"translate\(([-\d.]+),([-\d.]+)\)\s*scale\(([-\d.]+),([-\d.]+)\)", raw
    )
    if t_match:
        tx, ty = float(t_match.group(1)), float(t_match.group(2))
        sx, sy = float(t_match.group(3)), float(t_match.group(4))
    else:
        tx, ty, sx, sy = 0, h, 1, -1

    # Extract and transform paths
    path_ds = re.findall(r'd="([^"]*)"', raw)

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
    path_xml = "\n".join(
        f'  <path fill="{color_hex}" stroke="none" d="{d}"/>' for d in flat_paths if d.strip()
    )

    # Cleanup temp files
    tmp_pgm.unlink(missing_ok=True)
    tmp_svg.unlink(missing_ok=True)

    return path_xml


def potrace_hybrid_convert(
    input_path: str,
    output_dir: str,
    upscale_target: int = 6400,
    gaussian_sigma: float = 2.5,
    potrace_alphamax: float = 1.334,
    potrace_turdsize: int = 100,
    min_color_pct: float = 0.5,
) -> dict:
    """Full potrace hybrid pipeline.

    Returns dict with paths to output files.
    """
    potrace_bin = _find_potrace()
    if not potrace_bin:
        raise RuntimeError("potrace binary not found")

    input_path = Path(input_path)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "layers").mkdir(exist_ok=True)

    stem = input_path.stem
    if len(stem) > 30:
        stem = stem[:30].rstrip("_")

    # Load and upscale
    img = Image.open(input_path).convert("RGB")
    w0, h0 = img.size
    scale = upscale_target / max(w0, h0)
    if scale > 1.0:
        img = img.resize((int(w0 * scale), int(h0 * scale)), Image.LANCZOS)

    pixels = np.array(img)
    h, w = pixels.shape[:2]

    # Detect color families
    families = _detect_color_families(pixels, min_pct=min_color_pct)
    if not families:
        raise ValueError("No color families detected")

    # Background = largest family
    bg_family = families[0]
    design_families = families[1:]

    # Assign unmatched pixels to nearest family
    r, g, b = pixels[:, :, 0].astype(int), pixels[:, :, 1].astype(int), pixels[:, :, 2].astype(int)
    assigned = np.zeros((h, w), dtype=bool)
    for f in families:
        assigned |= f["mask"]

    if not assigned.all():
        unassigned_y, unassigned_x = np.where(~assigned)
        if len(unassigned_y) > 0:
            unassigned_pixels = pixels[~assigned].astype(float)
            centers = np.array([f["rgb"] for f in families], dtype=float)
            dists = np.sqrt(((unassigned_pixels[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2))
            nearest = dists.argmin(axis=1)
            for i, f in enumerate(families):
                match = nearest == i
                if match.any():
                    ys = unassigned_y[match]
                    xs = unassigned_x[match]
                    f["mask"][ys, xs] = True

    # Trace each design family with potrace
    layer_svgs = {}
    layer_info = []

    for f in design_families:
        path_xml = _trace_mask_with_potrace(
            f["mask"], f["hex"], f"{stem}_{f['name']}", out,
            potrace_bin, sigma=gaussian_sigma,
            alphamax=potrace_alphamax, turdsize=potrace_turdsize,
        )
        if path_xml:
            layer_svgs[f["name"]] = path_xml
            layer_info.append({
                "name": f["name"],
                "color": f["hex"],
                "area_pct": f["pct"],
                "svg_file": f"layers/{stem}_{f['name']}.svg",
            })

            # Save individual layer SVG
            layer_svg = (
                f'<?xml version="1.0" encoding="UTF-8"?>\n'
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">\n'
                f"{path_xml}\n</svg>"
            )
            (out / "layers" / f"{stem}_{f['name']}.svg").write_text(layer_svg, encoding="utf-8")

    # Combined SVG — background first, then design layers
    groups = "\n".join(
        f'  <g id="layer-{name}">\n{svg}\n  </g>'
        for name, svg in layer_svgs.items()
    )

    # Add white background rectangle
    combined = (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">\n'
        f'  <!-- Potrace Hybrid | CNC-Grade Bezier Curves -->\n'
        f'  <rect width="{w}" height="{h}" fill="{bg_family["hex"]}"/>\n'
        f"{groups}\n"
        f"</svg>"
    )

    combined_path = out / f"{stem}_combined.svg"
    combined_path.write_text(combined, encoding="utf-8")

    # BMP + PNG
    bmp_path = out / f"{stem}_300dpi.bmp"
    Image.fromarray(pixels).save(str(bmp_path), format="BMP", dpi=(300, 300))

    png_arr = np.zeros((h, w, 4), dtype=np.uint8)
    for f in design_families:
        rc, gc, bc = f["rgb"]
        png_arr[f["mask"]] = [rc, gc, bc, 255]
    png_path = out / f"{stem}_transparent.png"
    Image.fromarray(png_arr, "RGBA").save(str(png_path), dpi=(300, 300))

    # Metadata
    meta = {
        "source": stem,
        "engine": "potrace-hybrid",
        "dimensions": {"width": w, "height": h},
        "dpi": 300,
        "transparent": bg_family["name"],
        "layers": layer_info,
    }
    meta_path = out / f"{stem}_layers.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    return {
        "combined_svg": str(combined_path),
        "bmp": str(bmp_path),
        "png": str(png_path),
        "metadata": str(meta_path),
        "layers_dir": str(out / "layers"),
    }
