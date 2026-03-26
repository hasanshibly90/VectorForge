import type { PromptCategory, AITool, PromptEntry } from "../types";

export const CATEGORY_META: Record<PromptCategory, { label: string; color: string }> = {
  logos:          { label: "Logos",         color: "bg-blue-500/10 text-blue-400" },
  illustrations:  { label: "Illustrations", color: "bg-emerald-500/10 text-emerald-400" },
  "cnc-laser":   { label: "CNC / Laser",  color: "bg-orange-500/10 text-orange-400" },
  icons:         { label: "Icons",         color: "bg-pink-500/10 text-pink-400" },
  patterns:      { label: "Patterns",      color: "bg-cyan-500/10 text-cyan-400" },
  typography:    { label: "Typography",    color: "bg-amber-500/10 text-amber-400" },
};

export const TOOL_META: Record<AITool, { label: string; color: string }> = {
  chatgpt:    { label: "ChatGPT",    color: "bg-emerald-500/10 text-emerald-400" },
  gemini:     { label: "Gemini",     color: "bg-blue-500/10 text-blue-400" },
  midjourney: { label: "Midjourney", color: "bg-purple-500/10 text-purple-400" },
};

export const VECTORIZATION_TIPS = [
  { title: "Always specify \"no gradients\"", desc: "Gradients create thousands of color regions that produce messy vectors. Say it explicitly in every prompt." },
  { title: "Limit colors explicitly", desc: "Say \"use only 3 solid flat colors\" to get clean separable layers. Fewer colors = cleaner SVG." },
  { title: "Request \"flat design\" or \"vector art style\"", desc: "These keywords tell AI models to avoid photorealism and produce clean vector-like output." },
  { title: "Specify \"pure white background\"", desc: "Avoids subtle gray backgrounds that create unwanted layers in the conversion." },
  { title: "Add \"no shadows, no textures\"", desc: "Shadows create gradient-like regions; textures create noise that potrace can't clean up." },
  { title: "For CNC/laser: \"uniform line thickness\"", desc: "Ensures paths are cuttable at scale. Thin lines may not survive morphological cleanup." },
  { title: "Use negative prompts in Midjourney", desc: "--no gradient --no shadow --no texture is highly effective for flat output." },
  { title: "Request high contrast", desc: "Black on white or bold color separations trace the cleanest. Low contrast = noisy boundaries." },
];

export const prompts: PromptEntry[] = [
  // ── Logos ──────────────────────────────────────
  {
    id: "logo-wolf",
    title: "Minimalist Wolf Logo",
    category: "logos",
    aiTool: "chatgpt",
    prompt: "Create a minimalist wolf head logo in flat design style. Use only 2 colors: solid black on a pure white background. No gradients, no shadows, no textures. Sharp clean edges, geometric shapes. The wolf should face left in profile view. Output as a square image with large margins.",
    expectedResult: "A clean geometric wolf silhouette, perfect for vinyl cutting or logo use. 2 colors only.",
    settings: { colormode: "binary", detail_level: 7, smoothing: 6 },
    tags: ["flat", "minimalist", "2-color", "geometric"],
    difficulty: "beginner",
  },
  {
    id: "logo-monogram",
    title: "Abstract Geometric Monogram",
    category: "logos",
    aiTool: "gemini",
    prompt: "Design a monogram logo using the letters 'VF' in a bold geometric style. Use exactly 3 flat solid colors: deep purple, white, and black. No gradients, no shadows, no 3D effects. Clean vector-like appearance with sharp edges. Square format, centered, minimal background.",
    expectedResult: "Bold interlocking V and F letters in geometric style. 3 clean color layers.",
    settings: { colormode: "color", detail_level: 6, smoothing: 5 },
    tags: ["flat", "geometric", "3-color", "monogram"],
    difficulty: "intermediate",
  },

  // ── Illustrations ──────────────────────────────
  {
    id: "illust-owl",
    title: "Flat Animal Sticker - Owl",
    category: "illustrations",
    aiTool: "chatgpt",
    prompt: "Create a cute owl illustration in flat design sticker style. Use only solid red and white colors on a black background. Absolutely no gradients, no shadows, no textures. Clean outlines, simple shapes. Cartoon style like a vinyl sticker. Square image.",
    expectedResult: "A cute cartoon owl with clean red and white areas on black. Perfect for sticker cutting.",
    settings: { colormode: "color", detail_level: 5, smoothing: 5 },
    tags: ["flat", "sticker", "cartoon", "3-color"],
    difficulty: "beginner",
  },
  {
    id: "illust-space",
    title: "Retro Space Poster",
    category: "illustrations",
    aiTool: "midjourney",
    prompt: "A retro space travel poster in flat illustration style, a rocket launching from a planet, maximum 4 solid flat colors, no gradients, no photorealism, screen print aesthetic, bold shapes, clean edges, vector art style --no gradient --no shadow --no texture --no photorealistic --stylize 250",
    expectedResult: "Bold retro poster with 3-4 solid color blocks. Screen-print quality with clean layer separation.",
    settings: { colormode: "color", detail_level: 8, smoothing: 4 },
    tags: ["flat", "retro", "poster", "4-color"],
    difficulty: "advanced",
  },

  // ── CNC / Laser ────────────────────────────────
  {
    id: "cnc-celtic",
    title: "Celtic Knot Panel",
    category: "cnc-laser",
    aiTool: "chatgpt",
    prompt: "Create a Celtic knot pattern suitable for CNC router cutting. Pure black lines on pure white background. Continuous interlocking knot design in a square panel. All lines should be uniform thickness. No fills, no gradients, no shading. High contrast line art only.",
    expectedResult: "Intricate interlocking knot pattern with uniform line weight. Ready for CNC routing or laser engraving.",
    settings: { colormode: "binary", detail_level: 9, smoothing: 3 },
    tags: ["line-art", "cnc", "2-color", "pattern"],
    difficulty: "intermediate",
  },
  {
    id: "cnc-number",
    title: "Decorative House Number Sign",
    category: "cnc-laser",
    aiTool: "gemini",
    prompt: "Design a decorative house number sign showing the number '42' for CNC plasma cutting. Bold silhouette style, pure black on white. Include a simple decorative border frame with corner ornaments. No thin lines, all elements must be thick and bold. No gradients, no gray tones, solid black only.",
    expectedResult: "Bold number '42' with ornamental border. All elements thick enough for plasma/laser cutting.",
    settings: { colormode: "binary", detail_level: 7, smoothing: 5 },
    tags: ["silhouette", "cnc", "plasma", "2-color"],
    difficulty: "beginner",
  },

  // ── Icons ──────────────────────────────────────
  {
    id: "icon-weather",
    title: "Weather App Icon - Sun & Cloud",
    category: "icons",
    aiTool: "chatgpt",
    prompt: "Create a single weather icon showing a sun partially behind a cloud. Flat design, no gradients, no shadows. Use only 3 solid colors: bright yellow for sun, white for cloud, light blue circle background. Clean geometric shapes, thick outlines. App icon style, perfectly centered in a square.",
    expectedResult: "Clean flat weather icon with 3 distinct color regions. Perfect for app UI or web use.",
    settings: { colormode: "color", detail_level: 5, smoothing: 7 },
    tags: ["flat", "icon", "3-color", "geometric"],
    difficulty: "beginner",
  },
  {
    id: "icon-runner",
    title: "Pictogram - Running Person",
    category: "icons",
    aiTool: "gemini",
    prompt: "Create an Olympic-style pictogram of a person running. Pure black silhouette on pure white background. Minimalist stick-figure style like international signage icons. No details, no face features, just the essential body pose. High contrast, clean edges, large size.",
    expectedResult: "Clean black silhouette pictogram. Single path, ideal for signage or wayfinding systems.",
    settings: { colormode: "binary", detail_level: 6, smoothing: 6 },
    tags: ["silhouette", "pictogram", "2-color", "minimalist"],
    difficulty: "beginner",
  },

  // ── Patterns ───────────────────────────────────
  {
    id: "pattern-tessellation",
    title: "Geometric Tessellation",
    category: "patterns",
    aiTool: "chatgpt",
    prompt: "Create a seamless geometric tessellation pattern. Use only 3 flat solid colors: navy blue, coral red, and white. Hexagonal tiling with triangular subdivisions. No gradients, no shadows, perfectly flat. Each color region has sharp clean edges. Square tile format suitable for repeating.",
    expectedResult: "Repeatable tile with 3 clean color layers. Each color separates into its own vector layer.",
    settings: { colormode: "color", detail_level: 8, smoothing: 4 },
    tags: ["seamless", "geometric", "3-color", "tile"],
    difficulty: "intermediate",
  },
  {
    id: "pattern-artdeco",
    title: "Art Deco Border Pattern",
    category: "patterns",
    aiTool: "midjourney",
    prompt: "An art deco border pattern, horizontal strip, repeating fan and line motifs, pure black on white background, no gradients, clean geometric shapes, vector art appearance, high contrast --no gradient --no texture --no shading --ar 4:1 --stylize 100",
    expectedResult: "Elegant repeating art deco motifs in pure black and white. Clean for laser etching or print borders.",
    settings: { colormode: "binary", detail_level: 8, smoothing: 3 },
    tags: ["art-deco", "border", "2-color", "repeating"],
    difficulty: "advanced",
  },

  // ── Typography ─────────────────────────────────
  {
    id: "typo-forge",
    title: "Bold Display Word - FORGE",
    category: "typography",
    aiTool: "chatgpt",
    prompt: "Create the word 'FORGE' in a bold industrial display typeface. Pure black letters on pure white background. Block letters with sharp edges, no serifs, no outlines, no shadows, no 3D effects. Ultra bold weight, tightly kerned. Centered in a wide rectangle.",
    expectedResult: "Clean bold black text on white. Single layer, sharp edges, perfect for signage or branding.",
    settings: { colormode: "binary", detail_level: 7, smoothing: 5 },
    tags: ["typography", "bold", "2-color", "industrial"],
    difficulty: "beginner",
  },
  {
    id: "typo-script",
    title: "Decorative Script Initial",
    category: "typography",
    aiTool: "gemini",
    prompt: "Design a large decorative script letter 'A' in calligraphic style. Pure black ink on pure white background. Elegant flowing curves with varying stroke thickness. No gray tones, no gradients, no background decoration. Just the single letter, centered, filling the frame.",
    expectedResult: "Elegant calligraphic letter with smooth Bezier curves. Ideal for monogramming or engraving.",
    settings: { colormode: "binary", detail_level: 9, smoothing: 4 },
    tags: ["calligraphy", "script", "2-color", "decorative"],
    difficulty: "intermediate",
  },
];
