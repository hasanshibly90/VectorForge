"""
Centerline (skeleton) tracing for line art, strokes, handwriting.

Produces stroke-based SVG paths instead of filled contours.
Ideal for: pen drawings, handwriting, engraving paths, CNC line work.

Uses morphological thinning (Zhang-Suen) to reduce shapes to 1px skeletons,
then traces the skeleton as SVG polylines.
"""

import cv2
import numpy as np
from pathlib import Path


def extract_skeleton(img_gray: np.ndarray) -> np.ndarray:
    """Reduce binary image to 1-pixel-wide skeleton using morphological thinning."""
    # Threshold to binary
    _, binary = cv2.threshold(img_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Morphological skeleton (Zhang-Suen thinning)
    skeleton = np.zeros_like(binary)
    element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    while True:
        eroded = cv2.erode(binary, element)
        dilated = cv2.dilate(eroded, element)
        diff = cv2.subtract(binary, dilated)
        skeleton = cv2.bitwise_or(skeleton, diff)
        binary = eroded.copy()
        if cv2.countNonZero(binary) == 0:
            break

    return skeleton


def skeleton_to_svg_paths(skeleton: np.ndarray, stroke_color: str = "#000000", stroke_width: float = 2.0) -> str:
    """Convert skeleton image to SVG polyline paths.

    Finds contours of the skeleton and converts each to a polyline.
    """
    h, w = skeleton.shape[:2]
    contours, _ = cv2.findContours(skeleton, cv2.RETR_LIST, cv2.CHAIN_APPROX_TC89_L1)

    paths = []
    for i, contour in enumerate(contours):
        if len(contour) < 3:
            continue
        # Simplify contour
        epsilon = 0.5
        approx = cv2.approxPolyDP(contour, epsilon, closed=False)
        if len(approx) < 2:
            continue

        points = approx.reshape(-1, 2)
        d_parts = [f"M{points[0][0]:.1f} {points[0][1]:.1f}"]
        for pt in points[1:]:
            d_parts.append(f"L{pt[0]:.1f} {pt[1]:.1f}")

        d = " ".join(d_parts)
        paths.append(
            f'  <path id="stroke_{i}" fill="none" stroke="{stroke_color}" '
            f'stroke-width="{stroke_width}" stroke-linecap="round" '
            f'stroke-linejoin="round" d="{d}"/>'
        )

    svg = (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">\n'
        + "\n".join(paths)
        + "\n</svg>"
    )
    return svg


def trace_centerline(
    input_path: str,
    output_path: str,
    stroke_color: str = "#000000",
    stroke_width: float = 2.0,
) -> str:
    """Full centerline tracing pipeline.

    1. Load image as grayscale
    2. Extract skeleton
    3. Convert to SVG polylines

    Returns: SVG string (also saved to output_path)
    """
    img = cv2.imread(input_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Could not read image: {input_path}")

    skeleton = extract_skeleton(img)
    svg = skeleton_to_svg_paths(skeleton, stroke_color, stroke_width)

    Path(output_path).write_text(svg, encoding="utf-8")
    return svg
