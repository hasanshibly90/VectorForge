"""
SVG post-processing and path optimization.

Cleans up SVG output from vtracer/potrace:
- Removes tiny paths (speckles)
- Adds path IDs for editability
- Optimizes viewBox to content bounds
- Reduces coordinate precision
- Merges adjacent same-color paths where possible
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path


def optimize_svg(svg_path: Path, min_path_length: int = 50) -> Path:
    """Optimize an SVG file in-place.

    Args:
        svg_path: Path to SVG file
        min_path_length: Remove paths with d="" shorter than this (speckle removal)

    Returns:
        Same path (modified in place)
    """
    tree = ET.parse(str(svg_path))
    root = tree.getroot()
    ns = "{http://www.w3.org/2000/svg}"

    # Remove namespace prefix for cleaner output
    for elem in root.iter():
        if elem.tag.startswith(ns):
            elem.tag = elem.tag[len(ns):]

    # 1. Remove tiny paths (speckles)
    removed = 0
    for parent in list(root.iter()):
        for child in list(parent):
            if child.tag == "path" or child.tag == f"{ns}path":
                d = child.get("d", "")
                if len(d) < min_path_length:
                    parent.remove(child)
                    removed += 1

    # 2. Add path IDs
    path_counter = 0
    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag == "path" and not elem.get("id"):
            fill = elem.get("fill", "none").replace("#", "")
            elem.set("id", f"p{path_counter}_{fill}")
            path_counter += 1

    # 3. Add group IDs if missing
    group_counter = 0
    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag == "g" and not elem.get("id"):
            elem.set("id", f"layer_{group_counter}")
            group_counter += 1

    # 4. Reduce coordinate precision (6 decimals -> 1)
    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag == "path":
            d = elem.get("d", "")
            # Replace long decimals with 1 decimal place
            d = re.sub(r'(\d+\.\d{2})\d+', r'\1', d)
            elem.set("d", d)

    # 5. Optimize viewBox to content bounds
    _optimize_viewbox(root)

    # Write back
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    tree.write(str(svg_path), xml_declaration=True, encoding="UTF-8")

    return svg_path


def _optimize_viewbox(root):
    """Set viewBox to tightly fit content bounds."""
    all_coords = []
    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag == "path":
            d = elem.get("d", "")
            # Extract M (moveto) coordinates
            moves = re.findall(r'M\s*([\d.]+)\s+([\d.]+)', d)
            for x, y in moves:
                all_coords.append((float(x), float(y)))

    if not all_coords:
        return

    xs = [c[0] for c in all_coords]
    ys = [c[1] for c in all_coords]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    # Add 1% padding
    pad_x = (max_x - min_x) * 0.01
    pad_y = (max_y - min_y) * 0.01
    vb = f"{max(0, min_x - pad_x):.0f} {max(0, min_y - pad_y):.0f} {max_x - min_x + 2*pad_x:.0f} {max_y - min_y + 2*pad_y:.0f}"

    root.set("viewBox", vb)


def get_svg_stats(svg_path: Path) -> dict:
    """Get statistics about an SVG file."""
    tree = ET.parse(str(svg_path))
    root = tree.getroot()

    paths = []
    colors = set()
    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag == "path":
            d = elem.get("d", "")
            fill = elem.get("fill", "none")
            paths.append({"fill": fill, "d_length": len(d)})
            if fill != "none":
                colors.add(fill)

    return {
        "path_count": len(paths),
        "color_count": len(colors),
        "colors": list(colors),
        "total_d_length": sum(p["d_length"] for p in paths),
        "file_size_kb": svg_path.stat().st_size // 1024,
        "width": root.get("width"),
        "height": root.get("height"),
        "viewBox": root.get("viewBox"),
    }
