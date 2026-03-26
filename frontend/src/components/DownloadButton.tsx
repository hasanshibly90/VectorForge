import { Download } from "lucide-react";

interface DownloadButtonProps {
  href: string;
  label?: string;
  variant?: "primary" | "secondary";
  size?: "sm" | "md";
}

export default function DownloadButton({
  href,
  label = "Download SVG",
  variant = "primary",
  size = "md",
}: DownloadButtonProps) {
  return (
    <a
      href={href}
      download
      className={`inline-flex items-center justify-center gap-2 rounded-xl font-medium transition-all duration-200 ${
        size === "sm" ? "px-3 py-1.5 text-xs" : "px-4 py-2.5 text-sm"
      } ${
        variant === "primary"
          ? "btn-primary"
          : "btn-secondary"
      }`}
    >
      <Download className={size === "sm" ? "w-3 h-3" : "w-4 h-4"} />
      {label}
    </a>
  );
}
