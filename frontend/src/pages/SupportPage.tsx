import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ChevronDown, FileQuestion, HelpCircle, Layers, MessageSquare, Monitor,
  Settings, Upload, Zap,
} from "lucide-react";

interface FAQItem {
  q: string;
  a: string;
}

interface FAQSection {
  title: string;
  icon: typeof HelpCircle;
  items: FAQItem[];
}

const FAQ_DATA: FAQSection[] = [
  {
    title: "Getting Started",
    icon: Upload,
    items: [
      {
        q: "What image formats can I upload?",
        a: "PNG, JPG, BMP, TIFF, and WEBP. For best results, use PNG with flat colors and no gradients. Maximum file size is 50MB.",
      },
      {
        q: "Do I need an account to convert images?",
        a: "No! Anonymous conversions work on the Convert page. Create an account to access batch uploads, API keys, conversion history, and webhook integration.",
      },
      {
        q: "What output formats are available?",
        a: "8 formats: SVG (combined layers), PDF, EPS, PNG (transparent), BMP (300 DPI), G-Code (for CNC/laser), JSON metadata, and ZIP (all files). Download individually or as a single ZIP.",
      },
      {
        q: "How long does conversion take?",
        a: "Typically 10-30 seconds depending on image complexity. The 7-step potrace pipeline upscales to 4K, applies median filtering, color separation, morphological cleanup, Bezier tracing, and multi-format export.",
      },
    ],
  },
  {
    title: "Image Quality",
    icon: Layers,
    items: [
      {
        q: "What makes a good source image for vectorization?",
        a: "Flat solid colors, no gradients, no shadows, no textures, high contrast. 2-4 colors work best. Check our Prompts page for AI prompts that generate ideal images.",
      },
      {
        q: "Why are there stray shapes in my SVG output?",
        a: "These are usually anti-alias edge artifacts from the source image. Try increasing the Detail slider (which increases the minimum component size filter). Our pipeline automatically removes disconnected fragments smaller than 1% of the main design.",
      },
      {
        q: "How do I get separate color layers?",
        a: "VectorForge automatically detects and separates colors using KMeans clustering. Each color becomes its own SVG layer. You can download individual layer SVGs from the results page.",
      },
      {
        q: "My SVG has too many colors / unwanted layers",
        a: "The auto-detection merges similar colors within 120 RGB distance and drops clusters under 5% of total pixels. For images with many similar colors, try using Monochrome mode (binary) for a clean 2-color output.",
      },
      {
        q: "The SVG doesn't open in Adobe Illustrator",
        a: "Make sure you're downloading the latest conversion (not a cached old file). Our SVGs are valid XML with flat coordinates, no transforms, and Illustrator-compatible attributes. If issues persist, contact support.",
      },
    ],
  },
  {
    title: "CNC & Machine Cutting",
    icon: Settings,
    items: [
      {
        q: "Can I use the output for laser cutting/engraving?",
        a: "Yes! Download the SVG for path-based cutting or the G-Code for direct machine control. The G-Code is GRBL-compatible and works with most CNC routers, laser engravers, and vinyl cutters.",
      },
      {
        q: "How do I adjust G-Code settings (feed rate, Z depth)?",
        a: "Currently G-Code uses default settings: 1000 mm/min feed, 3000 mm/min travel, 0.1 scale factor. Custom G-Code parameters are coming in a future update. For now, you can edit the G-Code file directly or re-generate via the API.",
      },
      {
        q: "What CNC machines are compatible?",
        a: "Any GRBL-based machine: CNC routers (Shapeoko, X-Carve, OpenBuilds), laser engravers (Ortur, Sculpfun, xTool), vinyl cutters, and pen plotters. The G-Code uses standard G0/G1/M3/M5 commands.",
      },
    ],
  },
  {
    title: "API & Integration",
    icon: Zap,
    items: [
      {
        q: "How do I get an API key?",
        a: "Create an account, go to Dashboard, and click 'Create' under API Keys. You'll get a key starting with 'vf_live_' — save it immediately as it's only shown once. Use it via the X-API-Key header.",
      },
      {
        q: "What's the API rate limit?",
        a: "Free tier: 5 conversions/day. Pro: unlimited. Rate limiting is per-API-key. See the API docs at /docs for full endpoint documentation.",
      },
      {
        q: "How do webhooks work?",
        a: "Register a webhook URL in Dashboard. VectorForge sends POST requests with HMAC-SHA256 signed payloads on conversion.completed and conversion.failed events. Verify the X-Webhook-Signature header.",
      },
      {
        q: "Can I self-host VectorForge?",
        a: "Yes! Clone from GitHub, install potrace, run with Docker Compose or directly with uvicorn + npm. See the README for setup instructions. Enterprise plan includes dedicated self-hosting support.",
      },
    ],
  },
  {
    title: "Billing & Account",
    icon: Monitor,
    items: [
      {
        q: "Is VectorForge free?",
        a: "Yes! The free tier includes 5 conversions/day with all 8 output formats. No credit card required. Upgrade to Pro for unlimited conversions and batch API access.",
      },
      {
        q: "How do I upgrade to Pro?",
        a: "Stripe billing integration is coming soon. Currently all features are available during our beta period. Sign up to be notified when paid plans launch.",
      },
      {
        q: "Can I delete my account and data?",
        a: "Contact us at supportibe@gmail.com and we'll delete your account and all associated conversion data within 24 hours.",
      },
    ],
  },
];

function FAQAccordion({ section }: { section: FAQSection }) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  const Icon = section.icon;

  return (
    <div className="card">
      <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
        <Icon className="w-4 h-4 text-accent-400" /> {section.title}
      </h2>
      <div className="space-y-1">
        {section.items.map((item, i) => (
          <div key={i} className="rounded-xl overflow-hidden">
            <button
              onClick={() => setOpenIndex(openIndex === i ? null : i)}
              className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-dark-800/50 rounded-xl transition-colors"
            >
              <span className="text-sm font-medium text-gray-200 pr-4">{item.q}</span>
              <ChevronDown className={`w-4 h-4 text-dark-400 flex-shrink-0 transition-transform duration-200 ${
                openIndex === i ? "rotate-180" : ""
              }`} />
            </button>
            {openIndex === i && (
              <div className="px-4 pb-4">
                <p className="text-sm text-dark-400 leading-relaxed">{item.a}</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function SupportPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-8 sm:py-14">
      <div className="text-center mb-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent-500/10 text-accent-400 text-xs font-semibold mb-3">
          <FileQuestion className="w-3 h-3" /> Help Center
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-white mb-2 tracking-tight">
          FAQ & <span className="text-accent-400">Support</span>
        </h1>
        <p className="text-sm text-dark-400">
          Find answers to common questions or reach out for help.
        </p>
      </div>

      {/* FAQ sections */}
      <div className="space-y-6">
        {FAQ_DATA.map((section) => (
          <FAQAccordion key={section.title} section={section} />
        ))}
      </div>

      {/* Still need help */}
      <div className="card !bg-accent-500/5 border-accent-500/20 mt-10 text-center">
        <HelpCircle className="w-8 h-8 text-accent-400 mx-auto mb-3" />
        <h2 className="text-lg font-bold text-white mb-2">Still Need Help?</h2>
        <p className="text-sm text-dark-400 mb-5">
          Can't find what you're looking for? Our team is here to help.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link to="/contact" className="btn-primary flex items-center justify-center gap-2">
            <MessageSquare className="w-4 h-4" /> Contact Us
          </Link>
          <a href="https://github.com/hasanshibly90/VectorForge/issues" target="_blank" rel="noopener noreferrer"
            className="btn-secondary flex items-center justify-center gap-2">
            Report an Issue
          </a>
        </div>
      </div>
    </div>
  );
}
