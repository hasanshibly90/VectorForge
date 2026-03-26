import { useMemo, useState } from "react";
import { BookOpen, Lightbulb } from "lucide-react";
import type { PromptCategory, AITool } from "../types";
import { prompts, VECTORIZATION_TIPS } from "../data/prompts";
import PromptCard from "../components/PromptCard";
import PromptFilters from "../components/PromptFilters";

export default function PromptsPage() {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<PromptCategory | null>(null);
  const [tool, setTool] = useState<AITool | null>(null);

  const filtered = useMemo(() => {
    return prompts.filter((p) => {
      if (category && p.category !== category) return false;
      if (tool && p.aiTool !== tool) return false;
      if (search) {
        const q = search.toLowerCase();
        return (
          p.title.toLowerCase().includes(q) ||
          p.prompt.toLowerCase().includes(q) ||
          p.tags.some((t) => t.includes(q)) ||
          p.expectedResult.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [search, category, tool]);

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 sm:py-14">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent-500/10 text-accent-400 text-xs font-semibold mb-3">
          <BookOpen className="w-3 h-3" /> Prompt Library
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-white mb-2 tracking-tight">
          AI Prompt <span className="text-accent-400">Gallery</span>
        </h1>
        <p className="text-sm text-dark-400 max-w-lg mx-auto">
          Prompts that generate images perfect for vectorization. Copy a prompt, generate in your AI tool, upload here.
        </p>
      </div>

      {/* Filters */}
      <PromptFilters
        search={search}
        onSearchChange={setSearch}
        category={category}
        onCategoryChange={setCategory}
        tool={tool}
        onToolChange={setTool}
      />

      {/* Results count */}
      <p className="text-xs text-dark-500 mb-4">
        {filtered.length} prompt{filtered.length !== 1 ? "s" : ""}
        {category || tool || search ? " matching filters" : " available"}
      </p>

      {/* Grid */}
      {filtered.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((p) => (
            <PromptCard key={p.id} prompt={p} />
          ))}
        </div>
      ) : (
        <div className="card text-center py-16">
          <p className="text-dark-400 font-medium mb-2">No prompts match your filters</p>
          <button
            onClick={() => { setSearch(""); setCategory(null); setTool(null); }}
            className="text-accent-400 text-sm font-semibold hover:text-accent-300"
          >
            Clear all filters
          </button>
        </div>
      )}

      {/* Tips Section */}
      <div className="card mt-12">
        <h2 className="font-semibold text-white mb-5 flex items-center gap-2">
          <Lightbulb className="w-4 h-4 text-amber-400" />
          Tips for Writing Vectorization Prompts
        </h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {VECTORIZATION_TIPS.map((tip, i) => (
            <div key={i} className="flex gap-3">
              <span className="text-accent-400 font-bold text-sm mt-0.5 flex-shrink-0">{i + 1}.</span>
              <div>
                <p className="text-sm font-medium text-gray-200">{tip.title}</p>
                <p className="text-xs text-dark-400 mt-0.5 leading-relaxed">{tip.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
