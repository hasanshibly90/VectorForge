import { Link } from "react-router-dom";
import {
  ArrowRight, BookOpen, Code2, Download, FileCode, Layers, Play,
  Shield, Sparkles, Upload, Zap,
} from "lucide-react";

const FORMATS = [
  { name: "SVG", desc: "Illustrator, Inkscape" },
  { name: "PDF", desc: "Print shops" },
  { name: "EPS", desc: "CorelDRAW" },
  { name: "PNG", desc: "Transparent" },
  { name: "BMP", desc: "300 DPI print" },
  { name: "G-Code", desc: "CNC / Laser" },
];

const FEATURES = [
  { icon: Layers, title: "Color Layer Separation", desc: "Each color becomes its own SVG layer. Download individually or combined." },
  { icon: Zap, title: "CNC-Grade Potrace Engine", desc: "7-step pipeline: upscale, median filter, threshold, cleanup, Bezier tracing." },
  { icon: Download, title: "8 Export Formats", desc: "SVG, PDF, EPS, PNG, BMP, G-Code, JSON metadata, ZIP — one click." },
  { icon: Code2, title: "Developer API", desc: "REST API with JWT + API keys, batch upload, webhooks, usage stats." },
  { icon: BookOpen, title: "AI Prompt Gallery", desc: "12 curated prompts for ChatGPT, Gemini, Midjourney — copy and generate." },
  { icon: Shield, title: "Secure & Private", desc: "Your images are processed securely and never shared. Enterprise self-hosting available." },
];

const PRICING = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    desc: "Try it out",
    features: ["5 conversions/day", "All 8 formats", "Web upload only", "Community support"],
    cta: "Start Free",
    accent: false,
  },
  {
    name: "Pro",
    price: "$9",
    period: "/month",
    desc: "For professionals",
    features: ["Unlimited conversions", "All 8 formats", "Batch API", "API key access", "Priority support", "Webhook integration"],
    cta: "Get Pro",
    accent: true,
  },
  {
    name: "Enterprise",
    price: "$49",
    period: "/month",
    desc: "For teams & agencies",
    features: ["Everything in Pro", "Self-hosted option", "Custom color thresholds", "Dedicated support", "SLA guarantee", "White-label option"],
    cta: "Contact Us",
    accent: false,
  },
];

const STEPS = [
  { step: "1", title: "Upload", desc: "Drop any PNG, JPG, BMP, TIFF, or WEBP image", icon: Upload },
  { step: "2", title: "Convert", desc: "Our potrace engine traces optimal Bezier curves", icon: Play },
  { step: "3", title: "Download", desc: "Get SVG, PDF, EPS, PNG, BMP, G-Code — all in one ZIP", icon: Download },
];

export default function LandingPage() {
  return (
    <div className="overflow-hidden">
      {/* ── Hero ── */}
      <section className="relative max-w-5xl mx-auto px-4 pt-20 pb-24 text-center">
        <div className="absolute inset-0 bg-gradient-to-b from-accent-500/5 to-transparent rounded-3xl -z-10" />

        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-accent-500/10 text-accent-400 text-xs font-semibold mb-6 border border-accent-500/20">
          <Sparkles className="w-3.5 h-3.5" />
          CNC-Grade Vector Conversion
        </div>

        <h1 className="text-4xl sm:text-6xl font-extrabold text-white mb-6 tracking-tight leading-tight">
          Turn Any Image Into<br />
          <span className="text-accent-400">Production-Ready Vectors</span>
        </h1>

        <p className="text-lg sm:text-xl text-dark-300 max-w-2xl mx-auto mb-10 leading-relaxed">
          Upload a raster image. Get CNC-grade SVG with separated color layers,
          300 DPI BMP, transparent PNG, G-Code — all in one click.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link to="/convert" className="btn-primary !py-4 !px-8 !text-base flex items-center justify-center gap-2">
            <Zap className="w-5 h-5" /> Start Converting — Free
          </Link>
          <Link to="/prompts" className="btn-secondary !py-4 !px-8 !text-base flex items-center justify-center gap-2">
            <BookOpen className="w-5 h-5" /> Browse AI Prompts
          </Link>
        </div>

        {/* Format badges */}
        <div className="flex flex-wrap justify-center gap-2 mt-12">
          {FORMATS.map((f) => (
            <div key={f.name} className="px-3 py-1.5 rounded-lg bg-dark-800/60 border border-dark-700/50 text-xs">
              <span className="text-white font-semibold">{f.name}</span>
              <span className="text-dark-400 ml-1.5">{f.desc}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ── How It Works ── */}
      <section className="max-w-4xl mx-auto px-4 py-20">
        <h2 className="text-2xl sm:text-3xl font-extrabold text-white text-center mb-12">
          How It Works
        </h2>
        <div className="grid sm:grid-cols-3 gap-8">
          {STEPS.map((s) => (
            <div key={s.step} className="text-center">
              <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-accent-500/10 border border-accent-500/20 flex items-center justify-center">
                <s.icon className="w-6 h-6 text-accent-400" />
              </div>
              <div className="text-xs text-accent-400 font-bold mb-1">STEP {s.step}</div>
              <h3 className="text-lg font-bold text-white mb-2">{s.title}</h3>
              <p className="text-sm text-dark-400">{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Features ── */}
      <section className="max-w-5xl mx-auto px-4 py-20">
        <h2 className="text-2xl sm:text-3xl font-extrabold text-white text-center mb-4">
          Everything You Need
        </h2>
        <p className="text-dark-400 text-center mb-12 max-w-lg mx-auto">
          More than just a converter. A complete vector pipeline for designers, CNC operators, and developers.
        </p>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {FEATURES.map((f) => (
            <div key={f.title} className="card glass-hover">
              <f.icon className="w-8 h-8 text-accent-400 mb-3" />
              <h3 className="text-base font-bold text-white mb-1.5">{f.title}</h3>
              <p className="text-sm text-dark-400 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Pricing ── */}
      <section className="max-w-4xl mx-auto px-4 py-20">
        <h2 className="text-2xl sm:text-3xl font-extrabold text-white text-center mb-4">
          Simple Pricing
        </h2>
        <p className="text-dark-400 text-center mb-12">
          Start free. Upgrade when you need more.
        </p>
        <div className="grid sm:grid-cols-3 gap-5">
          {PRICING.map((p) => (
            <div
              key={p.name}
              className={`card flex flex-col ${
                p.accent ? "border-accent-500/40 shadow-glow-lg" : ""
              }`}
            >
              {p.accent && (
                <div className="text-[10px] font-bold text-accent-400 uppercase tracking-wider mb-2">Most Popular</div>
              )}
              <h3 className="text-lg font-bold text-white">{p.name}</h3>
              <div className="mt-2 mb-1">
                <span className="text-3xl font-extrabold text-white">{p.price}</span>
                <span className="text-dark-400 text-sm">{p.period}</span>
              </div>
              <p className="text-xs text-dark-400 mb-5">{p.desc}</p>
              <ul className="space-y-2.5 mb-6 flex-1">
                {p.features.map((feat) => (
                  <li key={feat} className="flex items-start gap-2 text-sm text-dark-300">
                    <ArrowRight className="w-3.5 h-3.5 text-accent-400 mt-0.5 flex-shrink-0" />
                    {feat}
                  </li>
                ))}
              </ul>
              <Link
                to={p.accent ? "/login" : "/"}
                className={p.accent ? "btn-primary text-center" : "btn-secondary text-center"}
              >
                {p.cta}
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="max-w-3xl mx-auto px-4 py-20 text-center">
        <div className="card !py-12 border-accent-500/20">
          <FileCode className="w-10 h-10 text-accent-400 mx-auto mb-4" />
          <h2 className="text-2xl font-extrabold text-white mb-3">
            Ready to vectorize?
          </h2>
          <p className="text-dark-400 mb-6">
            Upload your first image now. No account needed.
          </p>
          <Link to="/convert" className="btn-primary !py-3.5 !px-8 inline-flex items-center gap-2">
            <Zap className="w-5 h-5" /> Convert Now — Free
          </Link>
        </div>
      </section>
    </div>
  );
}
