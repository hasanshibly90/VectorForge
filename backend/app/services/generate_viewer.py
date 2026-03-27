#!/usr/bin/env python3
"""
Layer Viewer Generator
======================
Reads pipeline output directory and generates a self-contained HTML viewer
with embedded layer previews, toggle controls, and opacity sliders.

Usage:
    python generate_viewer.py <output_dir> [--max-preview-px 400]
"""

import argparse
import base64
import io
import json
import sys
from pathlib import Path
from PIL import Image


def generate_viewer(output_dir: str, max_preview_px: int = 400) -> Path:
    output_dir = Path(output_dir)

    json_files = list(output_dir.glob("*_layers.json"))
    if not json_files:
        print(f"WARNING: No *_layers.json in {output_dir}", file=sys.stderr)
        return output_dir / "layer_viewer.html"  # return path even if not created

    meta = json.loads(json_files[0].read_text())
    dims = meta.get("dimensions", {})
    w, h = dims.get("width", 800), dims.get("height", 800)

    # Generate preview PNGs from layer SVGs (rasterize mask regions)
    # Since we may not have preview PNGs, generate from the transparent PNG
    png_files = list(output_dir.glob("*_transparent.png"))
    if png_files:
        full_img = Image.open(png_files[0]).convert("RGBA")
    else:
        full_img = None

    for layer in meta.get("layers", []):
        layer_svg_path = output_dir / layer.get("svg_file", "")

        # Try to make a preview from the full transparent PNG
        if full_img:
            arr = __import__("numpy").array(full_img)
            hex_c = layer["color"]
            r_t = int(hex_c[1:3], 16)
            g_t = int(hex_c[3:5], 16)
            b_t = int(hex_c[5:7], 16)

            # Create mask of pixels matching this layer's color (±30 tolerance)
            r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
            a = arr[:, :, 3]
            match = (
                (abs(r.astype(int) - r_t) < 30) &
                (abs(g.astype(int) - g_t) < 30) &
                (abs(b.astype(int) - b_t) < 30) &
                (a > 128)
            )
            preview = __import__("numpy").zeros_like(arr)
            preview[match] = arr[match]

            preview_img = Image.fromarray(preview, "RGBA")
            scale = min(1.0, max_preview_px / max(preview_img.size))
            if scale < 1.0:
                preview_img = preview_img.resize(
                    (int(preview_img.size[0] * scale), int(preview_img.size[1] * scale)),
                    Image.LANCZOS,
                )
            buf = io.BytesIO()
            preview_img.save(buf, format="PNG", optimize=True)
            layer["preview_b64"] = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
        else:
            layer["preview_b64"] = ""

        if "display_name" not in layer:
            layer["display_name"] = layer.get("name", layer.get("id", ""))

        layer.pop("svg_file", None)
        layer.pop("preview_file", None)

    data_json = json.dumps(meta)

    html = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Layer Viewer</title><style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#0d0d12;--sf:#16161e;--sf2:#1e1e2a;--bd:#2a2a3a;--tx:#e4e4ef;--dim:#7a7a8e;--ac:#7c6af6;--glow:rgba(124,106,246,.15)}
body{background:var(--bg);color:var(--tx);font-family:system-ui,sans-serif;min-height:100vh}
.app{display:grid;grid-template-columns:310px 1fr;grid-template-rows:56px 1fr;min-height:100vh}
header{grid-column:1/-1;background:var(--sf);border-bottom:1px solid var(--bd);display:flex;align-items:center;justify-content:space-between;padding:0 20px}
header h1{font-size:14px;font-weight:600}
.back-btn{display:inline-flex;align-items:center;gap:6px;padding:5px 12px;border-radius:8px;border:1px solid var(--bd);background:var(--sf2);color:var(--tx);font-size:11px;font-weight:600;cursor:pointer;text-decoration:none;transition:.15s}
.back-btn:hover{background:var(--bd);color:#fff}
.mb{display:flex;gap:14px;font-size:11px;font-family:monospace;color:var(--dim)}
.sb{background:var(--sf);border-right:1px solid var(--bd);overflow-y:auto;padding:14px}
.sb h2{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--dim);margin-bottom:10px}
.lc{background:var(--sf2);border:1px solid var(--bd);border-radius:8px;margin-bottom:6px;overflow:hidden;cursor:pointer;transition:.2s}
.lc:hover{border-color:var(--ac);box-shadow:0 0 0 1px var(--ac),0 4px 12px var(--glow)}
.lc.active{border-color:var(--ac);box-shadow:0 0 0 2px var(--ac)}
.lc.hidden .lp{opacity:.2;filter:grayscale(.8)}
.lh{display:flex;align-items:center;gap:8px;padding:8px 10px}
.lt{width:16px;height:16px;border-radius:3px;border:2px solid var(--bd);display:flex;align-items:center;justify-content:center;flex-shrink:0;cursor:pointer;transition:.15s}
.lt.on{background:var(--ac);border-color:var(--ac)}
.lt.on::after{content:'\\2713';color:#fff;font-size:10px;font-weight:700}
.ls{width:14px;height:14px;border-radius:3px;border:1px solid rgba(255,255,255,.12);flex-shrink:0}
.li{flex:1;min-width:0}.ln{font-size:11px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.lm{font-size:9px;font-family:monospace;color:var(--dim);margin-top:1px}
.lp{height:50px;background:repeating-conic-gradient(#1a1a2a 0% 25%,#222235 0% 50%) 50%/10px 10px;display:flex;align-items:center;justify-content:center;transition:.3s}
.lp img{height:50px;width:100%;object-fit:contain}
.or{padding:5px 10px 8px;display:flex;align-items:center;gap:6px}
.or label{font-size:9px;color:var(--dim);font-family:monospace;width:44px}
.or input[type=range]{flex:1;accent-color:var(--ac);height:3px}
.ov{font-size:9px;font-family:monospace;color:var(--dim);width:28px;text-align:right}
.acts{margin-top:14px;display:flex;flex-direction:column;gap:5px}
.btn{padding:7px 12px;border-radius:5px;border:1px solid var(--bd);background:var(--sf2);color:var(--tx);font-size:11px;font-weight:600;cursor:pointer;text-align:center;transition:.15s}
.btn:hover{background:var(--bd)}
.ba{background:var(--ac);border-color:var(--ac);color:#fff}
.ca{background:var(--bg);display:flex;align-items:center;justify-content:center;position:relative;overflow:hidden}
.cw{position:relative;background:repeating-conic-gradient(#141420 0% 25%,#1a1a2a 0% 50%) 50%/18px 18px;border-radius:10px;overflow:hidden;box-shadow:0 8px 36px rgba(0,0,0,.5);max-width:90%;max-height:85vh}
.cw img{display:block;position:absolute;top:0;left:0;width:100%;height:100%;object-fit:contain;transition:opacity .3s}
.cw .sz{position:relative;visibility:hidden;max-width:100%;max-height:85vh}
.vl{position:absolute;bottom:14px;right:14px;background:rgba(0,0,0,.7);backdrop-filter:blur(8px);padding:5px 10px;border-radius:5px;font-size:10px;font-family:monospace;color:var(--dim)}
@media(max-width:768px){.app{grid-template-columns:1fr;grid-template-rows:52px auto 1fr}.sb{max-height:40vh;border-right:none;border-bottom:1px solid var(--bd)}}
</style></head><body><div class="app">
<header><div style="display:flex;align-items:center;gap:12px"><a href="/convert" class="back-btn">&larr; Back</a><h1>Layer Viewer</h1></div><div class="mb" id="mb"></div></header>
<div class="sb" id="sb"></div>
<div class="ca"><div class="cw" id="cw"></div><div class="vl" id="vl"></div></div>
</div><script>
const D=""" + data_json + """;
const S={layers:D.layers.map((l,i)=>({...l,visible:true,opacity:1,order:i})),focus:null};
function rM(){document.getElementById('mb').innerHTML=`<span>${D.dimensions.width}x${D.dimensions.height}</span><span>${D.dpi} DPI</span><span>${S.layers.length} layers</span>`}
function rS(){const s=document.getElementById('sb');
s.innerHTML='<h2>Layers ('+S.layers.length+')</h2>'+S.layers.map((l,i)=>'<div class="lc '+(l.visible?'':'hidden ')+(S.focus===i?'active ':'')+'" data-i="'+i+'"><div class="lh"><div class="lt '+(l.visible?'on':'')+'" data-t="'+i+'"></div><div class="ls" style="background:'+l.color+'"></div><div class="li"><div class="ln">'+(l.display_name||l.name)+'</div><div class="lm">'+l.color+' - '+l.area_pct+'%</div></div></div><div class="lp"><img src="'+(l.preview_b64||'')+'" /></div><div class="or"><label>Opacity</label><input type="range" min="0" max="100" value="'+Math.round(l.opacity*100)+'" data-o="'+i+'" /><span class="ov">'+Math.round(l.opacity*100)+'%</span></div></div>').join('')+'<div class="acts"><button class="btn ba" id="sa">Show All</button><button class="btn" id="ha">Hide All</button><button class="btn" id="so">Solo Focused</button></div>';
s.querySelectorAll('.lt').forEach(e=>{e.addEventListener('click',ev=>{ev.stopPropagation();S.layers[+e.dataset.t].visible=!S.layers[+e.dataset.t].visible;R()})});
s.querySelectorAll('.lc').forEach(e=>{e.addEventListener('click',()=>{const i=+e.dataset.i;S.focus=S.focus===i?null:i;R()})});
s.querySelectorAll('input[data-o]').forEach(e=>{e.addEventListener('input',ev=>{ev.stopPropagation();S.layers[+e.dataset.o].opacity=+e.value/100;rC()});e.addEventListener('click',ev=>ev.stopPropagation())});
document.getElementById('sa').onclick=()=>{S.layers.forEach(l=>l.visible=true);R()};
document.getElementById('ha').onclick=()=>{S.layers.forEach(l=>l.visible=false);R()};
document.getElementById('so').onclick=()=>{if(S.focus!==null){S.layers.forEach((l,i)=>l.visible=i===S.focus);R()}}}
function rC(){const w=document.getElementById('cw'),lbl=document.getElementById('vl'),v=S.layers.filter(l=>l.visible);
if(!v.length){w.innerHTML='<div style="padding:40px;color:var(--dim);font-size:13px;text-align:center">No layers visible</div>';lbl.textContent='';return}
let h='<img class="sz" src="'+v[0].preview_b64+'" />';
S.layers.forEach(l=>{if(l.visible)h+='<img src="'+l.preview_b64+'" style="opacity:'+l.opacity+'" />'});
w.innerHTML=h;
const n=v.length;
lbl.textContent=S.focus!==null&&S.layers[S.focus].visible?(S.layers[S.focus].display_name||S.layers[S.focus].name)+' - '+n+' visible':n===S.layers.length?'Composite - All layers':'Composite - '+n+'/'+S.layers.length+' layers'}
function R(){rM();rS();rC()}R();
</script></body></html>"""

    viewer_path = output_dir / "layer_viewer.html"
    viewer_path.write_text(html, encoding="utf-8")
    print(f"Viewer: {viewer_path} ({viewer_path.stat().st_size // 1024} KB)")
    return viewer_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir")
    parser.add_argument("--max-preview-px", type=int, default=400)
    args = parser.parse_args()
    generate_viewer(args.output_dir, args.max_preview_px)
