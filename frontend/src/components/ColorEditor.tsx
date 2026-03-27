import { useState } from "react";
import { Eye, EyeOff, Palette, Plus, Trash2, X } from "lucide-react";

export interface ColorEntry {
  hex: string;
  name: string;
  percentage: number;
  isTransparent: boolean;
  enabled: boolean;
}

interface ColorEditorProps {
  colors: ColorEntry[];
  onChange: (colors: ColorEntry[]) => void;
  previewUrl: string;
}

export default function ColorEditor({ colors, onChange, previewUrl }: ColorEditorProps) {
  const [addingColor, setAddingColor] = useState(false);
  const [newHex, setNewHex] = useState("#000000");
  const [newName, setNewName] = useState("");

  const updateColor = (index: number, updates: Partial<ColorEntry>) => {
    const next = colors.map((c, i) => i === index ? { ...c, ...updates } : c);
    // If marking as transparent, unmark others
    if (updates.isTransparent) {
      next.forEach((c, i) => { if (i !== index) c.isTransparent = false; });
    }
    onChange(next);
  };

  const removeColor = (index: number) => {
    onChange(colors.filter((_, i) => i !== index));
  };

  const addColor = () => {
    if (!newHex) return;
    onChange([...colors, {
      hex: newHex,
      name: newName || `custom_${colors.length}`,
      percentage: 0,
      isTransparent: false,
      enabled: true,
    }]);
    setNewHex("#000000");
    setNewName("");
    setAddingColor(false);
  };

  const transparentColor = colors.find(c => c.isTransparent);

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <Palette className="w-4 h-4 text-accent-400" />
          Color Layers ({colors.filter(c => c.enabled && !c.isTransparent).length})
        </h3>
        <button
          onClick={() => setAddingColor(!addingColor)}
          className="p-1.5 rounded-lg text-dark-400 hover:text-accent-400 hover:bg-dark-700 transition-all"
        >
          {addingColor ? <X className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
        </button>
      </div>

      {/* Background indicator / toggle */}
      {transparentColor ? (
        <div className="mb-3 px-3 py-2 rounded-xl bg-dark-900/60 text-xs text-dark-400 flex items-center gap-2">
          <div className="w-4 h-4 rounded border border-dark-600" style={{
            backgroundImage: "repeating-conic-gradient(#333 0% 25%, #555 0% 50%)",
            backgroundSize: "6px 6px"
          }} />
          Background: <span className="text-dark-300 font-medium">{transparentColor.name}</span>
          <button onClick={() => updateColor(colors.indexOf(transparentColor), { isTransparent: false })}
            className="ml-auto text-[10px] text-dark-500 hover:text-accent-400">Keep background</button>
        </div>
      ) : (
        <div className="mb-3 px-3 py-2 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-400 flex items-center justify-between">
          <span>No background set. Click the eye icon on a color to mark it as background.</span>
        </div>
      )}

      {/* Color list */}
      <div className="space-y-2">
        {colors.map((color, i) => (
          <div
            key={i}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all ${
              !color.enabled ? "opacity-40" :
              color.isTransparent ? "bg-dark-900/40 border border-dark-700/50" :
              "bg-dark-800/50"
            }`}
          >
            {/* Color swatch + picker */}
            <label className="relative flex-shrink-0 cursor-pointer">
              <div
                className="w-8 h-8 rounded-lg border-2 border-dark-600 hover:border-accent-500/50 transition-colors"
                style={{ backgroundColor: color.hex }}
              />
              <input
                type="color"
                value={color.hex}
                onChange={(e) => updateColor(i, { hex: e.target.value })}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />
            </label>

            {/* Name + hex */}
            <div className="flex-1 min-w-0">
              <input
                type="text"
                value={color.name}
                onChange={(e) => updateColor(i, { name: e.target.value })}
                className="text-sm font-medium text-gray-200 bg-transparent border-none outline-none w-full"
              />
              <p className="text-[10px] font-mono text-dark-400">
                {color.hex} {color.percentage > 0 && `- ${color.percentage}%`}
              </p>
            </div>

            {/* Transparent toggle */}
            <button
              onClick={() => updateColor(i, { isTransparent: !color.isTransparent })}
              title={color.isTransparent ? "Remove as background" : "Set as background (transparent)"}
              className={`p-1.5 rounded-lg transition-all ${
                color.isTransparent
                  ? "bg-accent-500/20 text-accent-400"
                  : "text-dark-500 hover:text-dark-300 hover:bg-dark-700"
              }`}
            >
              {color.isTransparent ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            </button>

            {/* Enable/disable */}
            <button
              onClick={() => updateColor(i, { enabled: !color.enabled })}
              className={`w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all flex-shrink-0 ${
                color.enabled
                  ? "bg-accent-500 border-accent-500 text-white"
                  : "border-dark-600 text-transparent"
              }`}
            >
              {color.enabled && <span className="text-[10px] font-bold">&#10003;</span>}
            </button>

            {/* Remove */}
            <button
              onClick={() => removeColor(i)}
              className="p-1 text-dark-600 hover:text-red-400 transition-colors flex-shrink-0"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>

      {/* Add color form */}
      {addingColor && (
        <div className="mt-3 p-3 rounded-xl bg-dark-900/60 space-y-2">
          <div className="flex gap-2">
            <label className="relative flex-shrink-0">
              <div className="w-10 h-10 rounded-lg border-2 border-dark-600" style={{ backgroundColor: newHex }} />
              <input type="color" value={newHex} onChange={(e) => setNewHex(e.target.value)}
                className="absolute inset-0 opacity-0 cursor-pointer" />
            </label>
            <div className="flex-1 space-y-1">
              <input type="text" value={newName} onChange={(e) => setNewName(e.target.value)}
                placeholder="Color name" className="input-field !py-1.5 !text-xs" />
              <input type="text" value={newHex} onChange={(e) => setNewHex(e.target.value)}
                placeholder="#000000" className="input-field !py-1.5 !text-xs font-mono" />
            </div>
          </div>
          <button onClick={addColor} className="btn-primary w-full !py-2 !text-xs">Add Color</button>
        </div>
      )}

      {/* Eyedropper hint */}
      <p className="text-[10px] text-dark-500 mt-3 text-center">
        Click color swatches to pick new colors. Toggle eye icon to set background.
      </p>
    </div>
  );
}
