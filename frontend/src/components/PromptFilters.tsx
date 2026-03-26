import { Search } from "lucide-react";
import type { PromptCategory, AITool } from "../types";
import { CATEGORY_META, TOOL_META } from "../data/prompts";

interface PromptFiltersProps {
  search: string;
  onSearchChange: (v: string) => void;
  category: PromptCategory | null;
  onCategoryChange: (v: PromptCategory | null) => void;
  tool: AITool | null;
  onToolChange: (v: AITool | null) => void;
}

export default function PromptFilters({
  search, onSearchChange, category, onCategoryChange, tool, onToolChange,
}: PromptFiltersProps) {
  const categories = Object.entries(CATEGORY_META) as [PromptCategory, { label: string; color: string }][];
  const tools = Object.entries(TOOL_META) as [AITool, { label: string; color: string }][];

  return (
    <div className="space-y-4 mb-8">
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-dark-400" />
        <input
          type="text"
          placeholder="Search prompts..."
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          className="input-field !pl-11"
        />
      </div>

      {/* Category pills */}
      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-none">
        <button
          onClick={() => onCategoryChange(null)}
          className={`flex-shrink-0 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
            category === null
              ? "bg-accent-500 text-white shadow-glow"
              : "bg-dark-700 text-dark-300 border border-dark-600 hover:border-accent-500/30"
          }`}
        >
          All
        </button>
        {categories.map(([key, meta]) => (
          <button
            key={key}
            onClick={() => onCategoryChange(category === key ? null : key)}
            className={`flex-shrink-0 px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
              category === key
                ? "bg-accent-500 text-white shadow-glow"
                : "bg-dark-700 text-dark-300 border border-dark-600 hover:border-accent-500/30"
            }`}
          >
            {meta.label}
          </button>
        ))}
      </div>

      {/* AI tool filter */}
      <div className="flex gap-2">
        <button
          onClick={() => onToolChange(null)}
          className={`px-3 py-1 rounded-lg text-[11px] font-medium transition-all ${
            tool === null
              ? "bg-dark-600 text-white"
              : "text-dark-400 hover:text-dark-200"
          }`}
        >
          All Tools
        </button>
        {tools.map(([key, meta]) => (
          <button
            key={key}
            onClick={() => onToolChange(tool === key ? null : key)}
            className={`px-3 py-1 rounded-lg text-[11px] font-medium transition-all ${
              tool === key
                ? `${meta.color} border border-current/20`
                : "text-dark-400 hover:text-dark-200"
            }`}
          >
            {meta.label}
          </button>
        ))}
      </div>
    </div>
  );
}
