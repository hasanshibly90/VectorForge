import { useState } from "react";
import { Eye, ZoomIn, ZoomOut } from "lucide-react";

interface SVGPreviewProps {
  url: string;
}

export default function SVGPreview({ url }: SVGPreviewProps) {
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);
  const [zoom, setZoom] = useState(100);

  if (error) {
    return (
      <div className="card flex items-center justify-center min-h-[200px]">
        <span className="text-dark-500">Preview unavailable</span>
      </div>
    );
  }

  return (
    <div className="card !p-3 overflow-hidden">
      <div className="flex items-center gap-2 mb-3 px-2">
        <Eye className="w-3.5 h-3.5 text-accent-400" />
        <span className="text-xs font-medium text-dark-400">Preview</span>
        <div className="ml-auto flex items-center gap-1">
          <button
            onClick={() => setZoom((z) => Math.max(25, z - 25))}
            className="p-1 text-dark-400 hover:text-white rounded transition-colors"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <span className="text-[10px] font-mono text-dark-500 w-8 text-center">{zoom}%</span>
          <button
            onClick={() => setZoom((z) => Math.min(200, z + 25))}
            className="p-1 text-dark-400 hover:text-white rounded transition-colors"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
      <div
        className="overflow-auto rounded-xl"
        style={{
          backgroundImage: "repeating-conic-gradient(#151520 0% 25%, #1a1a28 0% 50%)",
          backgroundSize: "16px 16px",
          maxHeight: "60vh",
        }}
      >
        {!loaded && (
          <div className="flex items-center justify-center h-[200px]">
            <div className="w-6 h-6 border-2 border-accent-500 border-t-transparent rounded-full animate-spin" />
          </div>
        )}
        <img
          src={url}
          alt="Vector preview"
          className="mx-auto block transition-transform duration-200"
          style={{
            width: `${zoom}%`,
            maxWidth: `${zoom}%`,
            display: loaded ? "block" : "none",
          }}
          onLoad={() => setLoaded(true)}
          onError={() => setError(true)}
        />
      </div>
    </div>
  );
}
