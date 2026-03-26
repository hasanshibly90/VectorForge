import { CheckCircle, Clock, Loader2, XCircle } from "lucide-react";
import type { Conversion } from "../types";

interface FileListProps {
  conversions: Conversion[];
  onDownload?: (id: string) => void;
}

const statusConfig = {
  pending: { icon: Clock, color: "text-dark-400", bg: "bg-dark-700 text-dark-300", label: "Queued" },
  processing: { icon: Loader2, color: "text-accent-400 animate-spin", bg: "bg-accent-500/10 text-accent-400", label: "Converting" },
  completed: { icon: CheckCircle, color: "text-emerald-400", bg: "bg-emerald-500/10 text-emerald-400", label: "Done" },
  failed: { icon: XCircle, color: "text-red-400", bg: "bg-red-500/10 text-red-400", label: "Failed" },
};

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function FileList({ conversions, onDownload }: FileListProps) {
  if (conversions.length === 0) return null;

  return (
    <div className="card !p-0 divide-y divide-dark-700/50">
      {conversions.map((conv) => {
        const cfg = statusConfig[conv.status];
        const Icon = cfg.icon;
        return (
          <div key={conv.id} className="flex items-center gap-4 px-5 py-3.5 glass-hover">
            <Icon className={`w-4 h-4 flex-shrink-0 ${cfg.color}`} />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-200 truncate">
                {conv.original_filename}
              </p>
              <p className="text-xs text-dark-400 font-mono">
                {formatBytes(conv.original_size_bytes)}
                {conv.processing_time_ms && ` / ${conv.processing_time_ms}ms`}
                {conv.engine_used && ` / ${conv.engine_used}`}
              </p>
            </div>
            <span className={`text-[10px] font-semibold px-2.5 py-1 rounded-full uppercase tracking-wider ${cfg.bg}`}>
              {cfg.label}
            </span>
            {conv.status === "completed" && onDownload && (
              <button
                onClick={() => onDownload(conv.id)}
                className="text-xs text-accent-400 hover:text-accent-300 font-semibold"
              >
                Download
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}
