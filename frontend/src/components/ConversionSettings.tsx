import { Settings2 } from "lucide-react";

interface SettingsProps {
  colormode: "color" | "binary";
  detailLevel: number;
  smoothing: number;
  outputFormats: string;
  onChange: (key: string, value: string | number) => void;
}

export default function ConversionSettings({
  colormode,
  detailLevel,
  smoothing,
  outputFormats,
  onChange,
}: SettingsProps) {
  return (
    <div className="card space-y-6">
      <h3 className="font-semibold text-white flex items-center gap-2">
        <Settings2 className="w-4 h-4 text-accent-400" />
        Settings
      </h3>

      {/* Color Mode */}
      <div>
        <label className="block text-xs font-medium text-dark-300 mb-2 uppercase tracking-wider">Color Mode</label>
        <div className="flex gap-2">
          {(["color", "binary"] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => onChange("colormode", mode)}
              className={`flex-1 px-3 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${
                colormode === mode
                  ? "bg-accent-500 text-white shadow-glow"
                  : "bg-dark-700 text-dark-300 border border-dark-600 hover:border-accent-500/30"
              }`}
            >
              {mode === "color" ? "Full Color" : "Mono"}
            </button>
          ))}
        </div>
      </div>

      {/* Detail Level */}
      <div>
        <div className="flex justify-between mb-2">
          <label className="text-xs font-medium text-dark-300 uppercase tracking-wider">Detail</label>
          <span className="text-xs font-mono text-accent-400">{detailLevel}</span>
        </div>
        <input
          type="range"
          min="1"
          max="10"
          value={detailLevel}
          onChange={(e) => onChange("detail_level", Number(e.target.value))}
          className="w-full accent-accent-500 h-1.5 bg-dark-700 rounded-full appearance-none cursor-pointer"
        />
        <div className="flex justify-between text-[10px] text-dark-500 mt-1">
          <span>Simple</span>
          <span>Detailed</span>
        </div>
      </div>

      {/* Smoothing */}
      <div>
        <div className="flex justify-between mb-2">
          <label className="text-xs font-medium text-dark-300 uppercase tracking-wider">Smoothing</label>
          <span className="text-xs font-mono text-accent-400">{smoothing}</span>
        </div>
        <input
          type="range"
          min="1"
          max="10"
          value={smoothing}
          onChange={(e) => onChange("smoothing", Number(e.target.value))}
          className="w-full accent-accent-500 h-1.5 bg-dark-700 rounded-full appearance-none cursor-pointer"
        />
        <div className="flex justify-between text-[10px] text-dark-500 mt-1">
          <span>Sharp</span>
          <span>Smooth</span>
        </div>
      </div>

      {/* Output Format */}
      <div>
        <label className="block text-xs font-medium text-dark-300 mb-2 uppercase tracking-wider">Output</label>
        <div className="flex gap-2">
          {[
            { value: "svg", label: "SVG" },
            { value: "svg,dxf", label: "SVG + DXF" },
          ].map((opt) => (
            <button
              key={opt.value}
              onClick={() => onChange("output_formats", opt.value)}
              className={`flex-1 px-3 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${
                outputFormats === opt.value
                  ? "bg-accent-500 text-white shadow-glow"
                  : "bg-dark-700 text-dark-300 border border-dark-600 hover:border-accent-500/30"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
