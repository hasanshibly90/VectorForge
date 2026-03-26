import { useCallback, useRef, useState } from "react";
import { FolderUp } from "lucide-react";
import DropZone from "../components/DropZone";
import ConversionSettings from "../components/ConversionSettings";
import FileList from "../components/FileList";
import { downloadConversion, getConversion, uploadBatch } from "../api/client";
import type { Conversion } from "../types";

export default function BatchPage() {
  const [settings, setSettings] = useState({
    colormode: "color" as "color" | "binary",
    detail_level: 5,
    smoothing: 5,
    output_formats: "svg",
  });
  const [conversions, setConversions] = useState<Conversion[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollInterval = useRef<ReturnType<typeof setInterval> | null>(null);

  const pollAll = useCallback((convs: Conversion[]) => {
    if (pollInterval.current) clearInterval(pollInterval.current);
    pollInterval.current = setInterval(async () => {
      const updated = await Promise.all(
        convs.map(async (c) => {
          if (c.status === "completed" || c.status === "failed") return c;
          try { return (await getConversion(c.id)).data; } catch { return c; }
        })
      );
      setConversions(updated);
      if (updated.every((c) => c.status === "completed" || c.status === "failed")) {
        clearInterval(pollInterval.current!);
        pollInterval.current = null;
      }
    }, 2000);
  }, []);

  const handleFiles = async (files: File[]) => {
    setUploading(true);
    setError(null);
    try {
      const res = await uploadBatch(files, {
        colormode: settings.colormode,
        detail_level: String(settings.detail_level),
        smoothing: String(settings.smoothing),
        output_formats: settings.output_formats,
      });
      setConversions(res.data.conversions);
      pollAll(res.data.conversions);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Batch upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleDownload = (id: string) => window.open(downloadConversion(id, "svg"), "_blank");

  return (
    <div className="max-w-5xl mx-auto px-4 py-16">
      <div className="text-center mb-12">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent-500/10 text-accent-400 text-xs font-semibold mb-4">
          <FolderUp className="w-3 h-3" /> Batch Processing
        </div>
        <h1 className="text-4xl font-extrabold text-white mb-3 tracking-tight">Batch Conversion</h1>
        <p className="text-dark-400">Upload multiple images and convert them all at once.</p>
      </div>

      <div className="grid gap-8 lg:grid-cols-[1fr,300px]">
        <div className="space-y-6">
          <DropZone onFiles={handleFiles} multiple disabled={uploading} />
          {uploading && (
            <div className="text-center py-6">
              <div className="w-8 h-8 border-2 border-accent-500 border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="text-sm text-dark-400 mt-3">Processing batch...</p>
            </div>
          )}
          {error && (
            <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}
          <FileList conversions={conversions} onDownload={handleDownload} />
        </div>
        <div className="lg:sticky lg:top-20 lg:self-start">
          <ConversionSettings
            colormode={settings.colormode}
            detailLevel={settings.detail_level}
            smoothing={settings.smoothing}
            outputFormats={settings.output_formats}
            onChange={(k, v) => setSettings((p) => ({ ...p, [k]: v }))}
          />
        </div>
      </div>
    </div>
  );
}
