import { useState } from "react";
import { Link } from "react-router-dom";
import { Check, Copy, Sparkles } from "lucide-react";
import type { PromptEntry } from "../types";
import { CATEGORY_META, TOOL_META } from "../data/prompts";

interface PromptCardProps {
  prompt: PromptEntry;
}

export default function PromptCard({ prompt }: PromptCardProps) {
  const [copied, setCopied] = useState(false);
  const cat = CATEGORY_META[prompt.category];
  const tool = TOOL_META[prompt.aiTool];

  const handleCopy = () => {
    navigator.clipboard.writeText(prompt.prompt);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="card flex flex-col gap-3 hover:border-accent-500/30 hover:shadow-glow transition-all duration-200">
      {/* Badges */}
      <div className="flex items-center justify-between">
        <span className={`text-[10px] font-semibold px-2.5 py-1 rounded-full uppercase tracking-wider ${cat.color}`}>
          {cat.label}
        </span>
        <span className={`text-[10px] font-semibold px-2.5 py-1 rounded-full ${tool.color}`}>
          {tool.label}
        </span>
      </div>

      {/* Title */}
      <h3 className="font-semibold text-white text-sm">{prompt.title}</h3>

      {/* Prompt text */}
      <div className="relative bg-dark-900/60 rounded-xl p-3">
        <p className="text-[11px] text-dark-300 font-mono leading-relaxed pr-8 line-clamp-4">
          {prompt.prompt}
        </p>
        <button
          onClick={handleCopy}
          className={`absolute top-2 right-2 p-1.5 rounded-lg transition-all ${
            copied ? "bg-emerald-500/20 text-emerald-400" : "bg-dark-700 text-dark-400 hover:text-white"
          }`}
        >
          {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* Expected result */}
      <p className="text-xs text-dark-400 leading-relaxed">{prompt.expectedResult}</p>

      {/* Settings pills */}
      <div className="flex gap-1.5 flex-wrap">
        <span className="text-[10px] px-2 py-0.5 rounded-md bg-dark-800 text-dark-300 border border-dark-700">
          {prompt.settings.colormode === "color" ? "Color" : "Mono"}
        </span>
        <span className="text-[10px] px-2 py-0.5 rounded-md bg-dark-800 text-dark-300 border border-dark-700">
          Detail: {prompt.settings.detail_level}
        </span>
        <span className="text-[10px] px-2 py-0.5 rounded-md bg-dark-800 text-dark-300 border border-dark-700">
          Smooth: {prompt.settings.smoothing}
        </span>
        <span className={`text-[10px] px-2 py-0.5 rounded-md border ${
          prompt.difficulty === "beginner" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
          prompt.difficulty === "intermediate" ? "bg-amber-500/10 text-amber-400 border-amber-500/20" :
          "bg-red-500/10 text-red-400 border-red-500/20"
        }`}>
          {prompt.difficulty}
        </span>
      </div>

      {/* Try This button */}
      <Link
        to={`/convert?colormode=${prompt.settings.colormode}&detail=${prompt.settings.detail_level}&smoothing=${prompt.settings.smoothing}`}
        className="btn-primary text-center mt-auto !py-2.5 flex items-center justify-center gap-2"
      >
        <Sparkles className="w-3.5 h-3.5" />
        Try This
      </Link>
    </div>
  );
}
