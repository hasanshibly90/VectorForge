import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, ImagePlus } from "lucide-react";

interface DropZoneProps {
  onFiles: (files: File[]) => void;
  multiple?: boolean;
  disabled?: boolean;
}

const ACCEPTED = {
  "image/png": [".png"],
  "image/jpeg": [".jpg", ".jpeg"],
  "image/bmp": [".bmp"],
  "image/tiff": [".tiff", ".tif"],
  "image/webp": [".webp"],
};

export default function DropZone({ onFiles, multiple = false, disabled = false }: DropZoneProps) {
  const onDrop = useCallback(
    (accepted: File[]) => {
      if (accepted.length > 0) onFiles(accepted);
    },
    [onFiles]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED,
    multiple,
    disabled,
    maxSize: 50 * 1024 * 1024,
  });

  return (
    <div
      {...getRootProps()}
      className={`relative border-2 border-dashed rounded-2xl p-8 sm:p-16 text-center cursor-pointer transition-all duration-300 ${
        disabled
          ? "opacity-40 cursor-not-allowed bg-dark-900"
          : isDragActive
          ? "border-accent-400 bg-accent-500/5 shadow-glow-lg"
          : "border-dark-600 hover:border-accent-500/40 hover:bg-dark-800/40 hover:shadow-glow"
      }`}
    >
      <input {...getInputProps()} />
      <div className={`mx-auto mb-5 w-16 h-16 rounded-2xl flex items-center justify-center transition-all duration-300 ${
        isDragActive ? "bg-accent-500/20 scale-110" : "bg-dark-800"
      }`}>
        {isDragActive ? (
          <ImagePlus className="w-7 h-7 text-accent-400" />
        ) : (
          <Upload className="w-7 h-7 text-dark-400" />
        )}
      </div>
      {isDragActive ? (
        <p className="text-accent-400 font-semibold text-lg">Drop {multiple ? "images" : "image"} here</p>
      ) : (
        <>
          <p className="text-gray-200 font-semibold text-lg mb-2">
            Drop {multiple ? "images" : "an image"} here, or click to browse
          </p>
          <p className="text-sm text-dark-400">PNG, JPG, BMP, TIFF, WEBP (max 50MB)</p>
        </>
      )}
    </div>
  );
}
