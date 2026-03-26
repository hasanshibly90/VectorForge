import { useCallback, useRef, useState } from "react";
import { ArrowLeftRight } from "lucide-react";

interface CompareSliderProps {
  originalUrl: string;
  vectorUrl: string;
}

export default function CompareSlider({ originalUrl, vectorUrl }: CompareSliderProps) {
  const [position, setPosition] = useState(50);
  const [dragging, setDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const updatePosition = useCallback((clientX: number) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = Math.max(0, Math.min(clientX - rect.left, rect.width));
    setPosition((x / rect.width) * 100);
  }, []);

  const handleMouseDown = () => setDragging(true);
  const handleMouseUp = () => setDragging(false);
  const handleMouseMove = (e: React.MouseEvent) => { if (dragging) updatePosition(e.clientX); };
  const handleTouchMove = (e: React.TouchEvent) => { updatePosition(e.touches[0].clientX); };
  const handleClick = (e: React.MouseEvent) => updatePosition(e.clientX);

  return (
    <div className="card !p-3">
      <div className="flex items-center gap-2 mb-3 px-2">
        <ArrowLeftRight className="w-3.5 h-3.5 text-accent-400" />
        <span className="text-xs font-medium text-dark-400">Before / After</span>
        <span className="text-[10px] text-dark-500 ml-auto">Drag slider to compare</span>
      </div>
      <div
        ref={containerRef}
        className="relative w-full aspect-square rounded-xl overflow-hidden cursor-col-resize select-none"
        style={{ backgroundImage: "repeating-conic-gradient(#151520 0% 25%, #1a1a28 0% 50%)", backgroundSize: "16px 16px" }}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onClick={handleClick}
        onTouchMove={handleTouchMove}
      >
        {/* Original (full width, behind) */}
        <img
          src={originalUrl}
          alt="Original"
          className="absolute inset-0 w-full h-full object-contain"
          draggable={false}
        />

        {/* Vector (clipped to slider position) */}
        <div
          className="absolute inset-0 overflow-hidden"
          style={{ width: `${position}%` }}
        >
          <img
            src={vectorUrl}
            alt="Vector"
            className="absolute inset-0 w-full h-full object-contain"
            style={{ width: containerRef.current ? `${containerRef.current.offsetWidth}px` : "100%" }}
            draggable={false}
          />
        </div>

        {/* Slider line */}
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-accent-400 shadow-glow z-10"
          style={{ left: `${position}%` }}
          onMouseDown={handleMouseDown}
          onTouchStart={() => setDragging(true)}
        >
          {/* Handle */}
          <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-8 h-8 bg-accent-500 rounded-full flex items-center justify-center shadow-glow-lg cursor-grab active:cursor-grabbing">
            <ArrowLeftRight className="w-4 h-4 text-white" />
          </div>
        </div>

        {/* Labels */}
        <div className="absolute top-3 left-3 px-2 py-1 bg-dark-900/80 rounded-md text-[10px] font-semibold text-accent-400 backdrop-blur-sm z-10">
          VECTOR
        </div>
        <div className="absolute top-3 right-3 px-2 py-1 bg-dark-900/80 rounded-md text-[10px] font-semibold text-dark-400 backdrop-blur-sm z-10">
          ORIGINAL
        </div>
      </div>
    </div>
  );
}
