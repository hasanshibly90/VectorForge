import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Zap } from "lucide-react";
import { getShared, downloadShared } from "../api/client";
import SVGPreview from "../components/SVGPreview";
import DownloadButton from "../components/DownloadButton";
import type { Conversion } from "../types";

export default function SharedViewPage() {
  const { token } = useParams<{ token: string }>();
  const [conversion, setConversion] = useState<Conversion | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    getShared(token)
      .then((res) => setConversion(res.data))
      .catch(() => setError("Shared link not found or expired"))
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return (
      <div className="min-h-screen bg-dark-950 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-accent-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !conversion || !token) {
    return (
      <div className="min-h-screen bg-dark-950 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-white mb-2">Not Found</h1>
          <p className="text-dark-400">{error || "Invalid link."}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-dark-950">
      <div className="max-w-3xl mx-auto px-4 py-12">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-white mb-2">{conversion.original_filename}</h1>
          <p className="text-dark-400 text-sm">
            {conversion.original_format.toUpperCase()} to SVG
            {conversion.processing_time_ms && ` in ${(conversion.processing_time_ms / 1000).toFixed(1)}s`}
          </p>
        </div>

        {conversion.status === "completed" && (
          <div className="space-y-6">
            <SVGPreview url={downloadShared(token, "svg")} />
            <div className="flex justify-center gap-3">
              <DownloadButton href={downloadShared(token, "svg")} label="Download SVG" />
            </div>
          </div>
        )}

        <div className="mt-12 text-center">
          <div className="inline-flex items-center gap-2 text-dark-500 text-xs">
            <Zap className="w-3 h-3" />
            Powered by <span className="font-semibold text-dark-400">VectorForge</span>
          </div>
        </div>
      </div>
    </div>
  );
}
