import { useCallback, useEffect, useRef, useState } from "react";
import { Archive, ChevronDown, Download, Eye, FileCode, Layers, Play, Printer, RotateCcw, Share2, Sparkles, Upload, X } from "lucide-react";
import { useDropzone } from "react-dropzone";
import { getConversion, uploadFile, downloadConversion, shareConversion } from "../api/client";
import type { Conversion } from "../types";
import SVGPreview from "../components/SVGPreview";
import CompareSlider from "../components/CompareSlider";
import DownloadButton from "../components/DownloadButton";

type Stage = "idle" | "selected" | "uploading" | "converting" | "done" | "error";

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
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Settings
  const [colormode, setColormode] = useState<"color" | "binary">("color");
  const [detail, setDetail] = useState(5);
  const [smoothing, setSmoothing] = useState(5);

  const onDrop = useCallback((accepted: File[]) => {
    if (accepted.length === 0) return;
    const f = accepted[0];
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setConversion(null);
    setErrorMsg("");
    setShareUrl("");
    setStage("selected");
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
    try {
      const res = await uploadFile(file, {
        colormode,
        detail_level: String(detail),
        smoothing: String(smoothing),
        output_formats: "svg",
      });
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
    setStage("idle");
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

      {/* ── STAGE: selected ── */}
      {stage === "selected" && file && (
        <div className="space-y-4">
          {/* File preview card */}
          <div className="card flex items-center gap-4">
            {preview && (
              <img src={preview} alt="" className="w-16 h-16 sm:w-20 sm:h-20 rounded-xl object-cover bg-dark-900 border border-dark-700 flex-shrink-0" />
            )}
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-white truncate text-sm sm:text-base">{file.name}</p>
              <p className="text-xs text-dark-400 mt-0.5">{kb(file.size)} &middot; {file.type.split("/")[1]?.toUpperCase()}</p>
            </div>
            <button onClick={handleReset} className="p-2 text-dark-400 hover:text-red-400 flex-shrink-0">
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Settings (collapsible on mobile) */}
          <div className="card !p-0 overflow-hidden">
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="w-full flex items-center justify-between px-5 py-3 sm:hidden"
            >
              <span className="text-sm font-semibold text-white">Settings</span>
              <ChevronDown className={`w-4 h-4 text-dark-400 transition-transform ${showSettings ? "rotate-180" : ""}`} />
            </button>
            <div className={`px-5 pb-5 pt-2 space-y-4 ${showSettings ? "block" : "hidden sm:block"}`}>
              <p className="text-sm font-semibold text-white hidden sm:block">Settings</p>

              {/* Color mode */}
              <div className="flex gap-2">
                {(["color", "binary"] as const).map((m) => (
                  <button key={m} onClick={() => setColormode(m)}
                    className={`flex-1 py-2 rounded-xl text-sm font-medium transition-all ${
                      colormode === m ? "bg-accent-500 text-white shadow-glow" : "bg-dark-700 text-dark-300 border border-dark-600"
                    }`}>{m === "color" ? "Full Color" : "Monochrome"}</button>
                ))}
              </div>

              {/* Detail + Smoothing */}
              <div className="grid grid-cols-2 gap-4">
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
            </div>
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

          {/* Vector Preview */}
          <SVGPreview url={downloadConversion(conversion.id, "svg")} />

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
