import { useCallback, useEffect, useRef, useState } from "react";
import { Archive, ChevronDown, Download, Eye, FileCode, Layers, Palette, Pipette, Play, Printer, RotateCcw, Share2, Sparkles, Upload, X } from "lucide-react";
import { useDropzone } from "react-dropzone";
import { useSearchParams } from "react-router-dom";
import { getConversion, uploadFile, downloadConversion, shareConversion } from "../api/client";
import type { Conversion } from "../types";
import SVGPreview from "../components/SVGPreview";
import CompareSlider from "../components/CompareSlider";
import ColorEditor, { type ColorEntry } from "../components/ColorEditor";
import DownloadButton from "../components/DownloadButton";

type Stage = "idle" | "selected" | "analyzing" | "editing" | "uploading" | "converting" | "done" | "error";

function _nameColor(rgb: number[]): string {
  const [r, g, b] = rgb;
  if (r > 200 && g > 200 && b > 200) return "white";
  if (r < 40 && g < 40 && b < 40) return "black";
  if (r > 150 && g < 80 && b < 80) return "red";
  if (g > 150 && r < 80 && b < 80) return "green";
  if (b > 150 && r < 80 && g < 80) return "blue";
  if (r > 180 && g > 150 && b < 80) return "yellow";
  if (r > 180 && g > 100 && b < 60) return "orange";
  if (r > 100 && g > 100 && b > 100 && r < 200) return "gray";
  return `color_${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
}

const ACCEPTED = {
  "image/png": [".png"],
  "image/jpeg": [".jpg", ".jpeg"],
  "image/bmp": [".bmp"],
  "image/tiff": [".tiff", ".tif"],
  "image/webp": [".webp"],
};

export default function UploadPage() {
  const [stage, setStage] = useState<Stage>("idle");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string>("");
  const [conversion, setConversion] = useState<Conversion | null>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [shareUrl, setShareUrl] = useState("");
  const [showSettings, setShowSettings] = useState(false);
  const [imageType, setImageType] = useState<"photo" | "artwork" | "logo">("artwork");
  const [detectedColors, setDetectedColors] = useState<ColorEntry[]>([]);
  const [showSegmented, setShowSegmented] = useState(false);
  const [segmentedUrl, setSegmentedUrl] = useState("");
  const [cropEnabled, setCropEnabled] = useState(false);
  const [eyedropperActive, setEyedropperActive] = useState(false);
  const [pickedColor, setPickedColor] = useState("");
  const imgRef = useRef<HTMLImageElement>(null);

  const handleImageClick = (e: React.MouseEvent<HTMLImageElement>) => {
    if (!eyedropperActive || !imgRef.current) return;
    const img = imgRef.current;
    const rect = img.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    // Draw to canvas to read pixel
    const canvas = document.createElement("canvas");
    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(img, 0, 0);
    const scaleX = img.naturalWidth / rect.width;
    const scaleY = img.naturalHeight / rect.height;
    const pixel = ctx.getImageData(Math.floor(x * scaleX), Math.floor(y * scaleY), 1, 1).data;
    const hex = `#${pixel[0].toString(16).padStart(2, "0")}${pixel[1].toString(16).padStart(2, "0")}${pixel[2].toString(16).padStart(2, "0")}`;
    setPickedColor(hex);
    // Add to colors if not already there
    const exists = detectedColors.some(c => {
      const dr = parseInt(c.hex.slice(1, 3), 16) - pixel[0];
      const dg = parseInt(c.hex.slice(3, 5), 16) - pixel[1];
      const db = parseInt(c.hex.slice(5, 7), 16) - pixel[2];
      return Math.sqrt(dr * dr + dg * dg + db * db) < 40;
    });
    if (!exists) {
      setDetectedColors(prev => [...prev, {
        hex, name: _nameColor([pixel[0], pixel[1], pixel[2]]),
        percentage: 0, isTransparent: false, enabled: true,
      }]);
    }
    setEyedropperActive(false);
  };
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Settings (can be pre-filled from URL params via /prompts "Try This" button)
  const [searchParams] = useSearchParams();
  const [colormode, setColormode] = useState<"color" | "binary">(
    (searchParams.get("colormode") as "color" | "binary") || "color"
  );
  const [detail, setDetail] = useState(Number(searchParams.get("detail")) || 5);
  const [smoothing, setSmoothing] = useState(Number(searchParams.get("smoothing")) || 5);

  const applyImageType = (type: "photo" | "artwork" | "logo") => {
    setImageType(type);
    switch (type) {
      case "photo":
        setColormode("color"); setDetail(4); setSmoothing(7);
        break;
      case "artwork":
        setColormode("color"); setDetail(6); setSmoothing(5);
        break;
      case "logo":
        setColormode("color"); setDetail(8); setSmoothing(3);
        break;
    }
  };

  const onDrop = useCallback((accepted: File[]) => {
    if (accepted.length === 0) return;
    const f = accepted[0];
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setConversion(null);
    setErrorMsg("");
    setShareUrl("");
    setDetectedColors([]);
    // Auto-analyze colors
    setStage("analyzing");
    const form = new FormData();
    form.append("file", f);
    import("../api/client").then(({ default: api }) => {
      api.post("/conversions/analyze-colors", form, { headers: { "Content-Type": "multipart/form-data" } })
        .then((res) => {
          const analyzed: ColorEntry[] = res.data.colors
            .filter((c: any) => c.percentage > 1)
            .slice(0, 8)
            .map((c: any, i: number) => ({
              hex: c.hex,
              name: _nameColor(c.rgb),
              percentage: c.percentage,
              isTransparent: i === 0, // largest = background
              enabled: true,
            }));
          setDetectedColors(analyzed);
          setStage("editing");
        })
        .catch(() => {
          // If analysis fails, skip to manual convert
          setStage("selected");
        });
    });
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED,
    multiple: false,
    maxSize: 50 * 1024 * 1024,
    disabled: stage === "uploading" || stage === "converting",
  });

  const stopPolling = () => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
  };

  const startPolling = (id: string) => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const res = await getConversion(id);
        setConversion(res.data);
        if (res.data.status === "completed") { stopPolling(); setStage("done"); }
        else if (res.data.status === "failed") { stopPolling(); setErrorMsg(res.data.error_message || "Conversion failed"); setStage("error"); }
      } catch { stopPolling(); }
    }, 1500);
  };

  const handleConvert = async () => {
    if (!file) return;
    setStage("uploading");
    setErrorMsg("");

    // Build custom colors JSON if user edited them
    const activeColors = detectedColors.filter(c => c.enabled && !c.isTransparent);
    const bgColor = detectedColors.find(c => c.isTransparent);
    const customColorsJson = activeColors.length > 0 ? JSON.stringify({
      colors: activeColors.map(c => ({ hex: c.hex, name: c.name })),
      transparent: bgColor ? bgColor.hex : null,
    }) : "";

    try {
      const settings: Record<string, string> = {
        colormode,
        detail_level: String(detail),
        smoothing: String(smoothing),
        output_formats: "svg",
      };
      if (customColorsJson) settings.custom_colors = customColorsJson;

      const res = await uploadFile(file, settings);
      setConversion(res.data);
      setStage("converting");
      startPolling(res.data.id);
    } catch (err: any) {
      if (err.code === "ERR_NETWORK" || !err.response) {
        setErrorMsg("Backend not running. Start the server on port 8000.");
      } else {
        setErrorMsg(err.response?.data?.detail || "Upload failed");
      }
      setStage("error");
    }
  };

  const handleReset = () => {
    stopPolling();
    if (preview) URL.revokeObjectURL(preview);
    setFile(null);
    setPreview("");
    setConversion(null);
    setErrorMsg("");
    setShareUrl("");
    setDetectedColors([]);
    setShowSegmented(false);
    if (segmentedUrl) URL.revokeObjectURL(segmentedUrl);
    setSegmentedUrl("");
    setStage("idle");
  };

  const fetchSegmentedPreview = async () => {
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    const activeColors = detectedColors.filter(c => c.enabled && !c.isTransparent);
    const bgColor = detectedColors.find(c => c.isTransparent);
    form.append("colors_json", JSON.stringify({
      colors: activeColors.map(c => ({ hex: c.hex, name: c.name })),
      transparent: bgColor?.hex || null,
    }));
    try {
      const { default: api } = await import("../api/client");
      const res = await api.post("/conversions/segmentation-preview", form, {
        responseType: "blob",
        headers: { "Content-Type": "multipart/form-data" },
      });
      if (segmentedUrl) URL.revokeObjectURL(segmentedUrl);
      setSegmentedUrl(URL.createObjectURL(res.data));
      setShowSegmented(true);
    } catch {}
  };

  const handleShare = async () => {
    if (!conversion) return;
    try { const r = await shareConversion(conversion.id); setShareUrl(r.data.share_url); } catch {}
  };

  const kb = (b: number) => b < 1048576 ? `${(b / 1024).toFixed(0)} KB` : `${(b / 1048576).toFixed(1)} MB`;

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 sm:py-14">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent-500/10 text-accent-400 text-xs font-semibold mb-3">
          <Sparkles className="w-3 h-3" /> CNC-Grade Potrace Engine
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-white mb-2 tracking-tight">
          Raster to <span className="text-accent-400">Vector</span>
        </h1>
        <p className="text-sm text-dark-400">
          Upload an image, adjust settings, hit convert. Get all files in one ZIP.
        </p>
      </div>

      {/* ── STAGE: idle ── */}
      {stage === "idle" && (
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-2xl p-10 sm:p-16 text-center cursor-pointer transition-all duration-300 ${
            isDragActive
              ? "border-accent-400 bg-accent-500/5 shadow-glow-lg"
              : "border-dark-600 hover:border-accent-500/40 hover:shadow-glow"
          }`}
        >
          <input {...getInputProps()} />
          <Upload className="w-12 h-12 mx-auto mb-4 text-dark-400" />
          <p className="text-white font-semibold mb-1">Drop an image here, or click to browse</p>
          <p className="text-xs text-dark-400">PNG, JPG, BMP, TIFF, WEBP (max 50 MB)</p>
        </div>
      )}

      {/* ── STAGE: analyzing ── */}
      {stage === "analyzing" && (
        <div className="card text-center py-10">
          <div className="w-10 h-10 border-2 border-accent-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-white font-semibold">Analyzing colors...</p>
          <p className="text-xs text-dark-400 mt-1">Detecting dominant colors in your image</p>
        </div>
      )}

      {/* ── STAGE: selected (fallback if analysis failed) ── */}
      {stage === "selected" && file && (
        <div className="card text-center py-8">
          <p className="text-dark-400 mb-3">Color analysis unavailable</p>
          <button onClick={handleConvert} className="btn-primary">Convert Anyway</button>
        </div>
      )}

      {/* ── STAGE: editing (color picker + settings + convert) ── */}
      {stage === "editing" && file && (
        <div className="space-y-4">
          {/* Image Type Selector */}
          <div className="card">
            <p className="text-xs font-medium text-dark-300 uppercase tracking-wider mb-3">Image Type</p>
            <div className="grid grid-cols-3 gap-2">
              {([
                { type: "photo" as const, icon: "camera", label: "Photo", desc: "Camera shot, many colors" },
                { type: "artwork" as const, icon: "brush", label: "Artwork", desc: "Illustration, blended edges" },
                { type: "logo" as const, icon: "shapes", label: "Logo / Icon", desc: "Flat colors, sharp edges" },
              ]).map((t) => (
                <button key={t.type} onClick={() => applyImageType(t.type)}
                  className={`py-3 px-2 rounded-xl text-center transition-all ${
                    imageType === t.type ? "bg-accent-500 text-white shadow-glow" : "bg-dark-700 text-dark-300 border border-dark-600 hover:border-accent-500/30"
                  }`}>
                  <span className="text-sm font-semibold block">{t.label}</span>
                  <span className={`text-[9px] block mt-0.5 ${imageType === t.type ? "text-white/70" : "text-dark-500"}`}>{t.desc}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Image preview with segmentation toggle + eyedropper */}
          <div className="card !p-3">
            <div className="flex items-center justify-between mb-3 px-2">
              <div className="flex items-center gap-2">
                <Eye className="w-3.5 h-3.5 text-accent-400" />
                <span className="text-xs font-medium text-dark-400">
                  {showSegmented ? "Segmentation Preview" : "Original Image"}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => { if (segmentedUrl) setShowSegmented(false); }}
                  className={`px-2.5 py-1 rounded-lg text-[10px] font-semibold transition-all ${
                    !showSegmented ? "bg-accent-500/20 text-accent-400" : "text-dark-500 hover:text-dark-300"
                  }`}
                >
                  Original
                </button>
                <button
                  onClick={() => { if (segmentedUrl) setShowSegmented(true); else fetchSegmentedPreview(); }}
                  className={`px-2.5 py-1 rounded-lg text-[10px] font-semibold transition-all ${
                    showSegmented ? "bg-accent-500/20 text-accent-400" : "text-dark-500 hover:text-dark-300"
                  }`}
                >
                  Segmented
                </button>
                <div className="w-px h-4 bg-dark-700 mx-1" />
                <button
                  onClick={() => setEyedropperActive(!eyedropperActive)}
                  className={`px-2.5 py-1 rounded-lg text-[10px] font-semibold transition-all flex items-center gap-1 ${
                    eyedropperActive ? "bg-emerald-500/20 text-emerald-400" : "text-dark-500 hover:text-dark-300"
                  }`}
                >
                  <Pipette className="w-3 h-3" />
                  Pick
                </button>
              </div>
            </div>
            {eyedropperActive && (
              <div className="px-2 py-1.5 bg-emerald-500/10 rounded-lg text-[10px] text-emerald-400 text-center font-medium">
                Click on the image to pick a color
              </div>
            )}
            <div
              className={`rounded-xl overflow-hidden max-h-[50vh] ${eyedropperActive ? "cursor-crosshair" : ""}`}
              style={{ backgroundImage: "repeating-conic-gradient(#151520 0% 25%, #1a1a28 0% 50%)", backgroundSize: "16px 16px" }}
            >
              <img
                ref={imgRef}
                src={showSegmented && segmentedUrl ? segmentedUrl : preview}
                alt={showSegmented ? "Segmented" : "Original"}
                className="w-full object-contain max-h-[50vh]"
                crossOrigin="anonymous"
                onClick={handleImageClick}
              />
            </div>
            {/* File info bar */}
            <div className="flex items-center justify-between mt-2 px-2">
              <p className="text-xs text-dark-400 truncate">{file.name} &middot; {kb(file.size)}</p>
              <button onClick={handleReset} className="text-xs text-dark-500 hover:text-red-400">
                Remove
              </button>
            </div>
          </div>

          {/* Color Editor */}
          <ColorEditor colors={detectedColors} onChange={(c) => { setDetectedColors(c); setShowSegmented(false); setSegmentedUrl(""); }} previewUrl={preview} />

          {/* Quality Presets + Settings */}
          <div className="card space-y-4">
            <p className="text-xs font-medium text-dark-300 uppercase tracking-wider">Quality Preset</p>
            <div className="grid grid-cols-4 gap-2">
              {([
                { label: "Low", desc: "Fast, simple shapes", d: 3, s: 7 },
                { label: "Medium", desc: "Balanced quality", d: 5, s: 5 },
                { label: "High", desc: "Detailed output", d: 7, s: 4 },
                { label: "Ultra", desc: "Max detail, sharp", d: 9, s: 2 },
              ] as const).map((preset) => {
                const active = detail === preset.d && smoothing === preset.s;
                return (
                  <button key={preset.label}
                    onClick={() => { setDetail(preset.d); setSmoothing(preset.s); }}
                    className={`py-2.5 px-2 rounded-xl text-center transition-all ${
                      active ? "bg-accent-500 text-white shadow-glow" : "bg-dark-700 text-dark-300 border border-dark-600 hover:border-accent-500/30"
                    }`}>
                    <span className="text-xs font-semibold block">{preset.label}</span>
                    <span className={`text-[9px] block mt-0.5 ${active ? "text-white/70" : "text-dark-500"}`}>{preset.desc}</span>
                  </button>
                );
              })}
            </div>

            {/* Color mode */}
            <div>
              <p className="text-xs font-medium text-dark-300 uppercase tracking-wider mb-2">Color Mode</p>
              <div className="flex gap-2">
                {(["color", "binary"] as const).map((m) => (
                  <button key={m} onClick={() => setColormode(m)}
                    className={`flex-1 py-2 rounded-xl text-sm font-medium transition-all ${
                      colormode === m ? "bg-accent-500 text-white shadow-glow" : "bg-dark-700 text-dark-300 border border-dark-600"
                    }`}>{m === "color" ? "Full Color" : "Monochrome"}</button>
                ))}
              </div>
            </div>

            {/* Advanced sliders (collapsible) */}
            <button onClick={() => setShowSettings(!showSettings)}
              className="flex items-center gap-1 text-[10px] text-dark-500 hover:text-dark-300 transition-colors">
              <ChevronDown className={`w-3 h-3 transition-transform ${showSettings ? "rotate-180" : ""}`} />
              Advanced settings
            </button>
            {showSettings && (
              <div className="grid grid-cols-2 gap-4 pt-1">
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-dark-300">Detail</span>
                    <span className="text-accent-400 font-mono">{detail}</span>
                  </div>
                  <input type="range" min="1" max="10" value={detail} onChange={(e) => setDetail(+e.target.value)}
                    className="w-full accent-accent-500 h-1.5 bg-dark-700 rounded-full appearance-none" />
                </div>
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-dark-300">Smooth</span>
                    <span className="text-accent-400 font-mono">{smoothing}</span>
                  </div>
                  <input type="range" min="1" max="10" value={smoothing} onChange={(e) => setSmoothing(+e.target.value)}
                    className="w-full accent-accent-500 h-1.5 bg-dark-700 rounded-full appearance-none" />
                </div>
              </div>
            )}
          </div>

          {/* CONVERT BUTTON */}
          <button onClick={handleConvert} className="btn-primary w-full !py-4 !text-base flex items-center justify-center gap-3">
            <Play className="w-5 h-5 fill-current" />
            Convert to Vector
          </button>
        </div>
      )}

      {/* ── STAGE: uploading / converting ── */}
      {(stage === "uploading" || stage === "converting") && (
        <ConvertingProgress stage={stage} conversionId={conversion?.id} />
      )}

      {/* ── STAGE: done ── */}
      {stage === "done" && conversion && (
        <div className="space-y-5">
          {/* Summary */}
          <div className="card flex items-center justify-between">
            <div className="min-w-0">
              <p className="font-semibold text-white truncate">{conversion.original_filename}</p>
              <p className="text-sm text-dark-400">
                {(conversion.processing_time_ms! / 1000).toFixed(1)}s &middot; {conversion.engine_used} &middot; {conversion.layers?.length || 0} layers
              </p>
            </div>
            <button onClick={handleReset} className="btn-secondary !py-2 !px-3 ml-3 flex-shrink-0">
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>

          {/* Preview with Original/Vector toggle */}
          <ResultPreview
            originalUrl={preview || downloadConversion(conversion.id, "original")}
            vectorUrl={downloadConversion(conversion.id, "svg")}
          />

          {/* Layers */}
          {conversion.layers && conversion.layers.length > 0 && (
            <div className="card">
              <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <Layers className="w-4 h-4 text-accent-400" /> {conversion.layers.length} Color Layers
              </h3>
              <div className="space-y-2">
                {conversion.layers.map((l) => (
                  <div key={l.name} className="flex items-center gap-3 px-3 py-2 bg-dark-800/50 rounded-xl">
                    <div className="w-5 h-5 rounded-lg border border-dark-600 flex-shrink-0" style={{ backgroundColor: l.color_hex }} />
                    <span className="text-sm text-gray-200 flex-1 truncate">{l.name}</span>
                    <span className="text-xs font-mono text-dark-400 hidden sm:inline">{l.color_hex}</span>
                    <span className="text-xs text-dark-500">{l.area_pct}%</span>
                    <a href={`/api/conversions/${conversion.id}/download?format=layer&layer=${l.name}`}
                      download className="text-xs text-accent-400 font-semibold">SVG</a>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Downloads — all formats */}
          <div className="card space-y-4">
            <a href={`/api/conversions/${conversion.id}/download-all`} download
              className="btn-primary w-full !py-3.5 flex items-center justify-center gap-2">
              <Archive className="w-5 h-5" />
              Download All Files (ZIP)
            </a>

            {/* Vector formats */}
            <div>
              <p className="text-[10px] text-dark-500 uppercase tracking-wider font-semibold mb-2">Vector Formats</p>
              <div className="grid grid-cols-3 gap-2">
                <DownloadButton href={downloadConversion(conversion.id, "svg")} label="SVG" variant="secondary" size="sm" />
                <DownloadButton href={downloadConversion(conversion.id, "pdf")} label="PDF" variant="secondary" size="sm" />
                <DownloadButton href={downloadConversion(conversion.id, "eps")} label="EPS" variant="secondary" size="sm" />
              </div>
            </div>

            {/* Raster formats */}
            <div>
              <p className="text-[10px] text-dark-500 uppercase tracking-wider font-semibold mb-2">Raster Formats</p>
              <div className="grid grid-cols-2 gap-2">
                <DownloadButton href={downloadConversion(conversion.id, "png")} label="PNG (Alpha)" variant="secondary" size="sm" />
                <DownloadButton href={downloadConversion(conversion.id, "bmp")} label="BMP 300dpi" variant="secondary" size="sm" />
              </div>
            </div>

            {/* CNC / Machine */}
            <div>
              <p className="text-[10px] text-dark-500 uppercase tracking-wider font-semibold mb-2">CNC / Machine</p>
              <div className="grid grid-cols-2 gap-2">
                <DownloadButton href={downloadConversion(conversion.id, "gcode")} label="G-Code" variant="secondary" size="sm" />
                <DownloadButton href={downloadConversion(conversion.id, "json")} label="Metadata" variant="secondary" size="sm" />
              </div>
            </div>
          </div>

          {/* Share */}
          <div className="flex gap-3">
            <button onClick={handleShare} className="btn-secondary flex items-center gap-2">
              <Share2 className="w-4 h-4" /> Share
            </button>
            {conversion.outputs?.viewer && (
              <a href={`/api/conversions/${conversion.id}/viewer`} target="_blank" rel="noopener noreferrer"
                className="btn-secondary flex items-center gap-2">
                <Layers className="w-4 h-4" /> Viewer
              </a>
            )}
          </div>

          {shareUrl && (
            <div className="p-3 bg-accent-500/10 border border-accent-500/20 rounded-xl">
              <code className="text-sm text-accent-300 font-mono break-all">{shareUrl}</code>
            </div>
          )}
        </div>
      )}

      {/* ── STAGE: error ── */}
      {stage === "error" && (
        <div className="space-y-4">
          <div className="p-5 bg-red-500/10 border border-red-500/20 rounded-2xl text-center">
            <p className="text-red-400 font-semibold mb-1">Conversion Failed</p>
            <p className="text-sm text-red-400/70">{errorMsg}</p>
          </div>
          <button onClick={handleReset} className="btn-secondary w-full flex items-center justify-center gap-2">
            <RotateCcw className="w-4 h-4" /> Try Again
          </button>
        </div>
      )}
    </div>
  );
}


/* ── Result Preview with Original/Vector toggle ── */

function ResultPreview({ originalUrl, vectorUrl }: { originalUrl: string; vectorUrl: string }) {
  const [view, setView] = useState<"vector" | "original">("vector");

  return (
    <div className="card !p-3">
      <div className="flex items-center justify-between mb-3 px-2">
        <div className="flex items-center gap-2">
          <Eye className="w-3.5 h-3.5 text-accent-400" />
          <span className="text-xs font-medium text-dark-400">
            {view === "vector" ? "Vector Output" : "Original Image"}
          </span>
        </div>
        <div className="flex items-center gap-1 bg-dark-800 rounded-lg p-0.5">
          <button
            onClick={() => setView("vector")}
            className={`px-3 py-1 rounded-md text-[10px] font-semibold transition-all ${
              view === "vector" ? "bg-accent-500 text-white shadow-glow" : "text-dark-400 hover:text-dark-200"
            }`}
          >
            Vector
          </button>
          <button
            onClick={() => setView("original")}
            className={`px-3 py-1 rounded-md text-[10px] font-semibold transition-all ${
              view === "original" ? "bg-accent-500 text-white shadow-glow" : "text-dark-400 hover:text-dark-200"
            }`}
          >
            Original
          </button>
        </div>
      </div>
      <div
        className="rounded-xl overflow-auto max-h-[60vh]"
        style={{ backgroundImage: "repeating-conic-gradient(#151520 0% 25%, #1a1a28 0% 50%)", backgroundSize: "16px 16px" }}
      >
        <img
          src={view === "vector" ? vectorUrl : originalUrl}
          alt={view === "vector" ? "Vector" : "Original"}
          className="w-full object-contain"
        />
      </div>
    </div>
  );
}


/* ── Animated Progress Component ── */

const PIPELINE_STEPS = [
  { label: "Uploading image", duration: 2000 },
  { label: "Upscaling to 4K", duration: 3000 },
  { label: "Median filter (anti-alias removal)", duration: 3000 },
  { label: "Color thresholding", duration: 2000 },
  { label: "Morphological cleanup", duration: 3000 },
  { label: "Resolving overlaps & gaps", duration: 2000 },
  { label: "Potrace Bezier tracing", duration: 8000 },
  { label: "Exporting SVG + BMP + PNG", duration: 5000 },
];

function ConvertingProgress({ stage, conversionId }: { stage: string; conversionId?: string }) {
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef(Date.now());

  useEffect(() => {
    startRef.current = Date.now();
    const timer = setInterval(() => setElapsed(Date.now() - startRef.current), 200);
    return () => clearInterval(timer);
  }, []);

  // Calculate which step we're on based on elapsed time
  let cumulative = 0;
  let currentStep = 0;
  for (let i = 0; i < PIPELINE_STEPS.length; i++) {
    cumulative += PIPELINE_STEPS[i].duration;
    if (elapsed < cumulative) { currentStep = i; break; }
    if (i === PIPELINE_STEPS.length - 1) currentStep = i;
  }

  const totalDuration = PIPELINE_STEPS.reduce((s, p) => s + p.duration, 0);
  const pct = Math.min(95, (elapsed / totalDuration) * 100);
  const secs = (elapsed / 1000).toFixed(1);

  return (
    <div className="card py-8 px-6">
      {/* Timer */}
      <div className="text-center mb-6">
        <div className="inline-flex items-center gap-3 mb-2">
          <div className="w-8 h-8 border-[3px] border-accent-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-2xl font-bold text-white font-mono">{secs}s</span>
        </div>
        <p className="text-sm text-dark-400">
          {stage === "uploading" ? "Uploading..." : "Processing with Potrace pipeline"}
        </p>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-dark-800 rounded-full h-2 mb-6 overflow-hidden">
        <div
          className="bg-gradient-to-r from-accent-600 to-accent-400 h-full rounded-full transition-all duration-500 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Steps */}
      <div className="space-y-2">
        {PIPELINE_STEPS.map((step, i) => {
          const isDone = i < currentStep;
          const isCurrent = i === currentStep;
          return (
            <div key={i} className={`flex items-center gap-3 px-3 py-1.5 rounded-lg transition-all duration-300 ${
              isCurrent ? "bg-accent-500/10" : ""
            }`}>
              <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 text-[10px] font-bold transition-all duration-300 ${
                isDone ? "bg-emerald-500 text-white" :
                isCurrent ? "bg-accent-500 text-white animate-pulse" :
                "bg-dark-700 text-dark-500"
              }`}>
                {isDone ? "\u2713" : i + 1}
              </div>
              <span className={`text-sm transition-all duration-300 ${
                isDone ? "text-dark-400 line-through" :
                isCurrent ? "text-white font-medium" :
                "text-dark-500"
              }`}>
                {step.label}
              </span>
              {isCurrent && (
                <div className="ml-auto flex gap-0.5">
                  <div className="w-1.5 h-1.5 bg-accent-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                  <div className="w-1.5 h-1.5 bg-accent-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                  <div className="w-1.5 h-1.5 bg-accent-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {conversionId && (
        <p className="text-[10px] text-dark-600 font-mono text-center mt-4">{conversionId.slice(0, 8)}</p>
      )}
    </div>
  );
}
