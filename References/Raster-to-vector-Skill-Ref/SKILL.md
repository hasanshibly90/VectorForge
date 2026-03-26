---
name: raster-to-vector
description: >
  Production CNC-grade raster image → layered vector pipeline using potrace. Converts any image
  (PNG, JPG, WEBP, TIFF, BMP) into mathematically optimal Bézier SVGs with zero zigzag, zero noise,
  and zero anti-alias artifacts. Outputs separated color layers as individual SVGs, transparent PNGs,
  300 DPI BMPs, and an interactive HTML layer viewer. Use this skill whenever the user uploads an image
  and mentions "vectorize", "convert to SVG", "trace", "vector", "separate layers", "print-ready",
  "300 DPI", "CNC", "laser cut", "vinyl cut", "screen print", "die cut", "plotter", "Illustrator",
  "image to SVG", "raster to vector", "clean paths", "smooth curves", or wants to turn any raster
  image into scalable vector graphics. Also trigger when the user uploads a logo, illustration, or
  design and says "go", "process this", "make this CNC ready", or just wants clean separated vector
  layers from a raster source — even without explicitly asking for vectorization.
---

# Raster → CNC-Grade Layered Vector Pipeline

## Overview

This skill converts raster images into production-grade, CNC-ready layered vector SVGs using
**potrace** (mathematically optimal Bézier curve fitting). The pipeline was battle-tested through
7 iterations to eliminate every source of noise, zigzag, and anti-alias artifacts.

### Why Potrace Over vtracer

| Feature | vtracer | **potrace** (this skill) |
|---------|---------|--------------------------|
| Algorithm | Pixel grid tracing | Optimal Bézier fitting |
| Edge quality | Micro-zigzag on curves | Mathematically smooth |
| Path count | Hundreds of paths | 1-2 paths per layer |
| File size | 200-400 KB/layer | 25-40 KB/layer |
| CNC suitability | Needs workarounds | Native CNC-grade |

## Pipeline Steps

```
[INPUT]  Any raster image (PNG/JPG/WEBP/TIFF/BMP)
   │
   ├─ [1] Load & Upscale ──────── Lanczos to 4K/8K (preserves aspect ratio)
   ├─ [2] Median Filter ────────── MedianFilter(7) dissolves AA pixels at source
   ├─ [3] Hard Threshold ───────── Snap every pixel to nearest pure color
   ├─ [4] Morphological Clean ──── Remove specks <2000px, close gaps, smooth edges
   ├─ [5] Resolve & Fill ───────── No overlaps, no gaps between layers
   ├─ [6] Potrace Vectorize ────── σ=2.5 smooth → optimal Bézier → flat pixel coords
   └─ [7] Export All Formats
        ├─ SVG: potrace paths (σ=2.5, sharp detail)
        ├─ BMP: stronger smooth (σ=3.5) + 2nd speck cleanup + border verify
        └─ PNG: same as BMP, with alpha transparency
```

## Quick Start

### 1. Install dependencies (first run only)

```bash
apt-get install -y potrace 2>/dev/null
pip install Pillow scikit-learn numpy scipy --break-system-packages
```

### 2. Analyze the image first

Before running the pipeline, ALWAYS analyze the uploaded image to determine its color palette.
This is critical — the pipeline needs to know what colors to separate into layers.

```python
import numpy as np
from PIL import Image
from collections import Counter

img = Image.open('/mnt/user-data/uploads/<filename>').convert('RGB')
pixels = np.array(img).reshape(-1, 3)
quantized = (pixels // 32) * 32
counts = Counter(map(tuple, quantized))
for color, count in counts.most_common(10):
    pct = count / len(pixels) * 100
    print(f"  RGB({color[0]:3d},{color[1]:3d},{color[2]:3d}) → {pct:.1f}%")
```

From this analysis, define the color layers. Common patterns:
- **Logo on solid background**: 2-3 colors (background + 1-2 design colors)
- **Illustration**: 3-6 colors
- **Complex artwork**: 6-12 colors

### 3. Run the pipeline

```python
import sys
sys.path.insert(0, '<SKILL_DIR>/scripts')
from vectorize_cnc import run_cnc_pipeline

results = run_cnc_pipeline(
    input_path='/mnt/user-data/uploads/<filename>',
    output_dir='/home/claude/vector_output',
    colors={
        'red':   {'threshold': lambda r,g,b: (r > 120) & (g < 80) & (b < 80), 'hex': '#c80f12'},
        'white': {'threshold': lambda r,g,b: (r > 200) & (g > 200) & (b > 200), 'hex': '#ffffff'},
    },
    transparent_color='black',  # which color becomes transparent (usually background)
    target_resolution='4K',     # '4K' or '8K'
)
```

Replace `<SKILL_DIR>` with the actual path to this skill's directory.

**The `colors` dict** is the KEY parameter. Each entry defines:
- `threshold`: A lambda that takes (r, g, b) numpy arrays and returns a boolean mask
- `hex`: The clean hex color to use in the SVG output

**The `transparent_color`** specifies which color region becomes transparent (no SVG layer).
Usually this is the background color. Set to `None` to keep all colors as layers.

### 4. Generate the interactive viewer (optional)

```bash
python3 <SKILL_DIR>/scripts/generate_viewer.py /home/claude/vector_output
```

### 5. Copy outputs and present to user

```bash
# Copy all outputs
cp /home/claude/vector_output/*.svg /mnt/user-data/outputs/
cp /home/claude/vector_output/*.bmp /mnt/user-data/outputs/
cp /home/claude/vector_output/*.png /mnt/user-data/outputs/
mkdir -p /mnt/user-data/outputs/layers
cp /home/claude/vector_output/layers/*.svg /mnt/user-data/outputs/layers/
```

Then use `present_files` to share the combined SVG, individual layer SVGs, PNG, and BMP.

## Defining Color Thresholds

This is the most important step. Analyze the image colors first (Step 2), then write thresholds.

### Common threshold patterns

**Black background**: `lambda r,g,b: (r < 40) & (g < 40) & (b < 40)`
**White elements**: `lambda r,g,b: (r > 200) & (g > 200) & (b > 200)`
**Red fill**: `lambda r,g,b: (r > 120) & (g < 80) & (b < 80)`
**Blue accent**: `lambda r,g,b: (b > 150) & (r < 80) & (g < 80)`
**Green**: `lambda r,g,b: (g > 120) & (r < 80) & (b < 80)`
**Yellow/Gold**: `lambda r,g,b: (r > 180) & (g > 150) & (b < 80)`
**Grey**: `lambda r,g,b: (r > 80) & (r < 180) & (np.abs(r.astype(int) - g.astype(int)) < 20) & (np.abs(r.astype(int) - b.astype(int)) < 20)`

### "Everything else" pattern

If the image has a known background + known accent colors, define those explicitly and let
the remaining pixels be assigned to the nearest defined color automatically. The pipeline
handles this via Euclidean RGB distance — no leftover pixels are ever lost.

### Tight vs. loose thresholds

- **Tight** (e.g., `r > 200`): Captures only the purest pixels. Anti-alias boundaries fall
  through to the "snap to nearest" logic. Best for CNC/cutting workflows.
- **Loose** (e.g., `r > 120`): Captures more boundary pixels directly. Fewer pixels need
  snapping. Best when you want generous coverage of a color region.

For CNC work, always use TIGHT thresholds. Let the pipeline's nearest-color snapping handle
the transition pixels — this produces the cleanest boundaries.

## Pipeline Configuration

### Target Resolution

| Value | Max dimension | Best for |
|-------|--------------|----------|
| `4K`  | 3840px       | Logos, web, standard print, CNC cutting |
| `8K`  | 7680px       | Large-format print, billboards, fine detail |

### Potrace Parameters (tuned in the script, rarely need changing)

| Parameter | Value | Effect |
|-----------|-------|--------|
| `-a 1.334` | alphamax | Maximum curve smoothness |
| `-O 2.0` | optimize | Aggressive curve simplification |
| `-t 200` | turdsize | Remove blobs < 200 pixels (aggressive) |
| `--flat` | flat | No nested groups, flat path structure |

### Morphological Cleanup

| Parameter | Default | Effect |
|-----------|---------|--------|
| `min_component_px` | 2000 | Remove connected components smaller than this — high threshold kills all stray dots |
| `closing_iterations` | 3 | Fill gaps in boundaries |
| `opening_iterations` | 2 | Smooth jagged edges |

### Gaussian Smoothing

The pipeline uses TWO separate sigma values:

| Parameter | Default | Used for | Effect |
|-----------|---------|----------|--------|
| `gaussian_sigma` | 2.5 | SVG paths (potrace input) | Moderate smoothing — preserves sharp details |
| `gaussian_sigma_bmp` | 3.5 | BMP/PNG raster output | Stronger smoothing — eliminates all pixel staircase |

The BMP/PNG also gets a **second speck cleanup pass** after smoothing, which catches any tiny
blobs that survived the first morphological cleanup but became disconnected after Gaussian blur.
A border verification check confirms zero stray pixels in the outer 50px margin.

Higher sigma = smoother curves but slightly rounded corners. For CNC, 2.5 is the sweet spot
for SVG. For BMP reference images, 3.5 gives print-quality edges.

## Output Structure

```
vector_output/
├── {name}_combined.svg            # All layers in one SVG with <g> groups
├── {name}_300dpi.bmp              # White-background bitmap (print-ready)
├── {name}_transparent.png         # RGBA with true alpha transparency
├── {name}_layers.json             # Layer metadata
├── layer_viewer.html              # Interactive HTML viewer (if generated)
└── layers/
    ├── {name}_{color1}.svg        # Individual layer: flat pixel coords, no transforms
    ├── {name}_{color2}.svg
    └── ...
```

### SVG Properties (Illustrator-compatible)

- Coordinates: **absolute pixel values** (0 to width/height)
- No `<g transform>` tags anywhere — all transforms baked into path data
- Each path has explicit `fill="..."` and `stroke="none"` attributes
- `viewBox` matches pixel dimensions exactly
- Compatible with: Adobe Illustrator, Inkscape, CorelDRAW, CNC controllers

## How to Present Results to the User

After running the pipeline:

1. **List each layer** with color swatch, hex code, and what it represents
2. **Explain transparent regions** — what was the background becomes transparent
3. **Give CNC-specific advice**:
   - For vinyl/laser cutting → each layer is a separate cut path
   - For screen printing → each layer is a separate screen
   - For CNC routing → each layer is a separate toolpath
4. **Present the SVG files first** (combined + individual layers)
5. **Then present BMP and PNG** for reference/print

## Troubleshooting

**Potrace not installed**: `apt-get install -y potrace`

**White layer invisible in Illustrator**: White paths on white artboard are invisible.
Add a dark rectangle behind, or open the individual layer SVG and change artboard color.

**Output dir read-only**: Always use `/home/claude/` as working directory. Copy final
outputs to `/mnt/user-data/outputs/`.

**Too many/few layers**: Adjust the `colors` dict. More entries = more layers. Check the
color analysis output (Step 2) to see what's actually in the image.

**Edge not smooth enough**: Increase Gaussian sigma to 3.0-4.0 in the script call.
Trade-off: smoother edges but slightly rounded sharp corners.

**Tiny blobs surviving**: Increase `min_component_px` from 2000 to 5000, or increase
potrace's turdsize parameter via `potrace_turdsize=500`.

**Stray pixels in BMP outside the design**: The BMP gets a separate second speck cleanup
pass, but if dots still appear, increase `gaussian_sigma_bmp` to 4.0-5.0 and/or increase
`min_component_px` to 5000. The pipeline verifies the border is clean and reports any
stray pixels.

**BMP edges rougher than SVG**: This is expected since BMP is raster and SVG uses Bézier
curves. The `gaussian_sigma_bmp=3.5` default smooths BMP edges significantly. Increase to
4.0-5.0 for even smoother BMP edges (trade-off: slightly rounded sharp corners).

**Single-color design fills entire canvas**: When only 1 color layer is defined (e.g., red
on white background), the gap-fill step is automatically SKIPPED. Background pixels stay as
background/transparent. This is handled automatically — no parameter changes needed.

**JPEG input has artifacts**: JPEG compression creates intermediate color pixels at edges.
The pipeline handles this via MedianFilter(7) + nearest-color snapping. For heavily
compressed JPEGs, increase `median_kernel` to 9 or 11. PNG inputs are always preferred over
JPEG for cleanest results — advise clients to export/save as PNG when possible.
