import { useEffect, useState } from "react";
import { Eye } from "lucide-react";

interface SVGPreviewProps {
  url: string;
}

export default function SVGPreview({ url }: SVGPreviewProps) {
  const [svgContent, setSvgContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const token = localStorage.getItem("vf_token");
    fetch(url, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((res) => res.text())
      .then((text) => {
        setSvgContent(text);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [url]);

  if (loading) {
    return (
      <div className="card flex items-center justify-center min-h-[300px]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-accent-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm text-dark-400">Loading preview...</span>
        </div>
      </div>
    );
  }

  if (!svgContent) {
    return (
      <div className="card flex items-center justify-center min-h-[300px]">
        <span className="text-dark-500">Preview unavailable</span>
      </div>
    );
  }

  return (
    <div className="card !p-3 overflow-hidden">
      <div className="flex items-center gap-2 mb-3 px-2">
        <Eye className="w-3.5 h-3.5 text-accent-400" />
        <span className="text-xs font-medium text-dark-400">Preview</span>
      </div>
      <div
        className="max-h-[500px] overflow-auto flex items-center justify-center rounded-xl bg-dark-900/50 p-4"
        style={{ backgroundImage: "repeating-conic-gradient(#151520 0% 25%, #1a1a28 0% 50%)", backgroundSize: "16px 16px" }}
        dangerouslySetInnerHTML={{ __html: svgContent }}
      />
    </div>
  );
}
