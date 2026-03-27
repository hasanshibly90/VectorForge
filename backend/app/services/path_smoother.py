"""
SVG Path Smoother — reduces anchor points and smooths curves.

Post-processes SVG paths by:
1. Sampling points along each path
2. Simplifying with Ramer-Douglas-Peucker algorithm
3. Refitting as smooth cubic Bezier curves

This produces CNC-quality smooth paths with fewer anchor points.
"""

import math
import re
from pathlib import Path

import numpy as np
from svgpathtools import parse_path, CubicBezier, Line, Path as SVGPath


def _rdp_simplify(points: list[tuple[float, float]], epsilon: float) -> list[tuple[float, float]]:
    """Ramer-Douglas-Peucker point simplification."""
    if len(points) <= 2:
        return points

    # Find point with max distance from line between first and last
    start = np.array(points[0])
    end = np.array(points[-1])
    line_vec = end - start
    line_len = np.linalg.norm(line_vec)

    if line_len < 1e-10:
        return [points[0], points[-1]]

    line_unit = line_vec / line_len

    max_dist = 0
    max_idx = 0
    for i in range(1, len(points) - 1):
        pt = np.array(points[i])
        proj = np.dot(pt - start, line_unit)
        proj_pt = start + proj * line_unit
        dist = np.linalg.norm(pt - proj_pt)
        if dist > max_dist:
            max_dist = dist
            max_idx = i

    if max_dist > epsilon:
        left = _rdp_simplify(points[:max_idx + 1], epsilon)
        right = _rdp_simplify(points[max_idx:], epsilon)
        return left[:-1] + right
    else:
        return [points[0], points[-1]]


def _fit_cubic_beziers(points: list[tuple[float, float]]) -> list[CubicBezier]:
    """Fit smooth cubic Bezier curves through a set of points."""
    if len(points) < 2:
        return []
    if len(points) == 2:
        p0 = complex(*points[0])
        p3 = complex(*points[1])
        mid = (p0 + p3) / 2
        return [CubicBezier(p0, mid, mid, p3)]

    beziers = []
    for i in range(len(points) - 1):
        p0 = complex(*points[i])
        p3 = complex(*points[i + 1])

        # Calculate control points for smooth curve
        if i > 0:
            prev = complex(*points[i - 1])
            tangent_in = (p3 - prev) / 4
        else:
            tangent_in = (p3 - p0) / 3

        if i < len(points) - 2:
            nxt = complex(*points[i + 2])
            tangent_out = (nxt - p0) / 4
        else:
            tangent_out = (p3 - p0) / 3

        p1 = p0 + tangent_in
        p2 = p3 - tangent_out

        beziers.append(CubicBezier(p0, p1, p2, p3))

    return beziers


def smooth_svg_paths(
    svg_path: Path,
    epsilon: float = 2.0,
    num_samples: int = 50,
) -> Path:
    """Smooth all paths in an SVG file.

    Args:
        svg_path: Path to SVG file (modified in-place)
        epsilon: RDP simplification tolerance (higher = smoother, less detail)
        num_samples: Points to sample per path segment

    Returns:
        Same path (modified in-place)
    """
    content = svg_path.read_text(encoding="utf-8")

    def smooth_d(match):
        d_str = match.group(1)
        try:
            path = parse_path(d_str)
        except Exception:
            return f'd="{d_str}"'

        if len(path) < 2:
            return f'd="{d_str}"'

        # Sample points along the path
        points = []
        for seg in path:
            for t in np.linspace(0, 1, num_samples, endpoint=False):
                pt = seg.point(t)
                points.append((pt.real, pt.imag))
        # Add final point
        last_pt = path[-1].point(1.0)
        points.append((last_pt.real, last_pt.imag))

        # Simplify with RDP
        simplified = _rdp_simplify(points, epsilon)

        if len(simplified) < 2:
            return f'd="{d_str}"'

        # Refit as cubic Beziers
        beziers = _fit_cubic_beziers(simplified)

        if not beziers:
            return f'd="{d_str}"'

        # Build new path string
        new_d = f"M{beziers[0].start.real:.1f} {beziers[0].start.imag:.1f}"
        for b in beziers:
            new_d += f" C{b.control1.real:.1f} {b.control1.imag:.1f} {b.control2.real:.1f} {b.control2.imag:.1f} {b.end.real:.1f} {b.end.imag:.1f}"

        # Check if path was closed
        if d_str.rstrip().upper().endswith("Z"):
            new_d += " Z"

        return f'd="{new_d}"'

    # Replace all d="..." attributes
    smoothed = re.sub(r'd="([^"]+)"', smooth_d, content)

    svg_path.write_text(smoothed, encoding="utf-8")
    return svg_path
