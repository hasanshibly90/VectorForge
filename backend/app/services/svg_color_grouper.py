"""
SVG Color Grouping Post-Processor.

After vtracer traces an image (producing 100-500+ colors from gradients),
this module groups similar colors into clean layers and recolors paths.

Strategy: work on the OUTPUT (SVG), not the INPUT (image).
This preserves tracing quality while producing clean color layers.
"""

import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
import numpy as np


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert '#RRGGBB' to (R, G, B) tuple."""
    h = hex_color.lstrip("#").upper()
    if len(h) == 6:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return 0, 0, 0


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02X}{g:02X}{b:02X}"


def _hue_family(r: int, g: int, b: int) -> str:
    """Classify RGB into a hue family."""
    if r > 200 and g > 200 and b > 200: return "white"
    if r < 60 and g < 60 and b < 60: return "black"
    if abs(r - g) < 25 and abs(r - b) < 25 and 60 <= r <= 200: return "gray"
    if r > 130 and g < 90 and b < 90: return "red"
    if g > 80 and r < g and b < g: return "green"
    if b > 120 and r < 100 and g < 100: return "blue"
    if r > 100 and g > 50 and b < 120 and r > b: return "warm"
    if r > 70 and b > 70 and g < 70: return "purple"
    if g > 80 and b > 80 and r < 80: return "cyan"
    if r > 150 and b > 70 and g < 120: return "pink"
    return "other"


def group_svg_colors(
    svg_path: Path,
    output_path: Path | None = None,
    max_groups: int = 12,
) -> tuple[Path, list[dict]]:
    """Group similar colors in an SVG file into clean layers.

    1. Parse all paths and their fill colors
    2. Group fills by hue family (warm, green, red, black, white, etc.)
    3. Within each family, find the most representative color (weighted median)
    4. Recolor all paths in that family to the representative color
    5. Write cleaned SVG

    Args:
        svg_path: Input SVG file
        output_path: Output SVG file (defaults to overwriting input)
        max_groups: Maximum number of color groups

    Returns:
        (output_path, layer_info_list)
    """
    if output_path is None:
        output_path = svg_path

    tree = ET.parse(str(svg_path))
    root = tree.getroot()
    ns = "{http://www.w3.org/2000/svg}"

    # Collect all paths with their fill colors
    paths_by_color = defaultdict(list)
    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag == "path":
            fill = (elem.get("fill") or "").strip().upper()
            if fill and fill != "NONE":
                paths_by_color[fill].append(elem)

    if not paths_by_color:
        return output_path, []

    # Group colors by hue family
    family_groups = defaultdict(list)  # family -> [(hex, path_count, total_d_length)]
    for hex_color, paths in paths_by_color.items():
        r, g, b = _hex_to_rgb(hex_color)
        family = _hue_family(r, g, b)
        total_d = sum(len(p.get("d", "")) for p in paths)
        family_groups[family].append({
            "hex": hex_color,
            "rgb": (r, g, b),
            "paths": paths,
            "weight": total_d,
        })

    # For each family, compute the weighted median color
    layer_info = []
    color_remap = {}  # old_hex -> new_hex

    for family, members in family_groups.items():
        total_weight = sum(m["weight"] for m in members)
        if total_weight == 0:
            continue

        # Weighted average color for this family
        avg_r = sum(m["rgb"][0] * m["weight"] for m in members) / total_weight
        avg_g = sum(m["rgb"][1] * m["weight"] for m in members) / total_weight
        avg_b = sum(m["rgb"][2] * m["weight"] for m in members) / total_weight

        # Snap common families to pure colors
        if family == "white":
            avg_r, avg_g, avg_b = 255, 255, 255
        elif family == "black":
            avg_r, avg_g, avg_b = 0, 0, 0

        new_hex = _rgb_to_hex(int(avg_r), int(avg_g), int(avg_b))

        # Map all old colors in this family to the new representative color
        total_paths = 0
        for m in members:
            color_remap[m["hex"]] = new_hex
            total_paths += len(m["paths"])

        # Calculate area percentage (by path data length)
        all_d_total = sum(sum(len(p.get("d", "")) for p in ps) for ps in paths_by_color.values())
        area_pct = round(total_weight / max(1, all_d_total) * 100, 1)

        layer_info.append({
            "name": family,
            "color": new_hex.lower(),
            "area_pct": area_pct,
            "path_count": total_paths,
            "original_colors": len(members),
        })

    # Apply color_remap: recolor all paths to their family representative
    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag == "path":
            fill = (elem.get("fill") or "").strip().upper()
            if fill in color_remap:
                elem.set("fill", color_remap[fill])

    # Write modified SVG
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    tree.write(str(output_path), xml_declaration=True, encoding="UTF-8")

    layer_info.sort(key=lambda x: x["area_pct"], reverse=True)
    return output_path, layer_info
