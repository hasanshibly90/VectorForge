import { useState } from "react";
import { Link } from "react-router-dom";
import { Check, Globe, Mail, MessageSquare, Send } from "lucide-react";

const SUBJECTS = [
  { value: "general", label: "General Inquiry" },
  { value: "bug", label: "Bug Report" },
  { value: "feature", label: "Feature Request" },
  { value: "enterprise", label: "Enterprise / Pricing" },
  { value: "api", label: "API Integration Help" },
  { value: "cnc", label: "CNC / Machine Setup" },
];

export default function ContactPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [subject, setSubject] = useState("general");
  const [message, setMessage] = useState("");
  const [sent, setSent] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const subjectLabel = SUBJECTS.find((s) => s.value === subject)?.label || subject;
    const body = `Name: ${name}\nEmail: ${email}\nSubject: ${subjectLabel}\n\n${message}`;
    window.location.href = `mailto:supportibe@gmail.com?subject=[VectorForge] ${subjectLabel}&body=${encodeURIComponent(body)}`;
    setSent(true);
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 sm:py-14">
      <div className="text-center mb-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent-500/10 text-accent-400 text-xs font-semibold mb-3">
          <MessageSquare className="w-3 h-3" /> Get in Touch
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-white mb-2 tracking-tight">
          Contact <span className="text-accent-400">Us</span>
        </h1>
        <p className="text-sm text-dark-400">
          Questions, feedback, or enterprise inquiries — we'd love to hear from you.
        </p>
      </div>

      <div className="grid gap-8 lg:grid-cols-[1fr,320px]">
        {/* Form */}
        <div className="card">
          {sent ? (
            <div className="text-center py-12">
              <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-emerald-500/10 flex items-center justify-center">
                <Check className="w-7 h-7 text-emerald-400" />
              </div>
              <h2 className="text-lg font-bold text-white mb-2">Message Ready</h2>
              <p className="text-sm text-dark-400 mb-4">
                Your email client should have opened with the message pre-filled. Just hit send!
              </p>
              <button onClick={() => setSent(false)} className="btn-secondary">
                Send Another
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-dark-300 mb-1.5 uppercase tracking-wider">Name</label>
                  <input
                    type="text" required value={name} onChange={(e) => setName(e.target.value)}
                    placeholder="Your name"
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-dark-300 mb-1.5 uppercase tracking-wider">Email</label>
                  <input
                    type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    className="input-field"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-dark-300 mb-1.5 uppercase tracking-wider">Subject</label>
                <select
                  value={subject} onChange={(e) => setSubject(e.target.value)}
                  className="input-field appearance-none"
                >
                  {SUBJECTS.map((s) => (
                    <option key={s.value} value={s.value}>{s.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-dark-300 mb-1.5 uppercase tracking-wider">Message</label>
                <textarea
                  required value={message} onChange={(e) => setMessage(e.target.value)}
                  placeholder="Tell us how we can help..."
                  rows={5}
                  className="input-field resize-none"
                />
              </div>

              <button type="submit" className="btn-primary w-full !py-3 flex items-center justify-center gap-2">
                <Send className="w-4 h-4" /> Send Message
              </button>
            </form>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-5">
          <div className="card">
            <h3 className="font-semibold text-white mb-4">Quick Links</h3>
            <div className="space-y-3">
              <a href="mailto:supportibe@gmail.com" className="flex items-center gap-3 text-sm text-dark-300 hover:text-accent-400 transition-colors">
                <Mail className="w-4 h-4 flex-shrink-0" /> supportibe@gmail.com
              </a>
              <a href="https://aiosolibe.cloud" target="_blank" rel="noopener noreferrer"
                className="flex items-center gap-3 text-sm text-dark-300 hover:text-accent-400 transition-colors">
                <Globe className="w-4 h-4 flex-shrink-0" /> aiosolibe.cloud
              </a>
            </div>
          </div>

          <div className="card">
            <h3 className="font-semibold text-white mb-3">Response Time</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-dark-400">General</span>
                <span className="text-dark-300">24-48 hours</span>
              </div>
              <div className="flex justify-between">
                <span className="text-dark-400">Bug Reports</span>
                <span className="text-dark-300">12-24 hours</span>
              </div>
              <div className="flex justify-between">
                <span className="text-dark-400">Enterprise</span>
                <span className="text-emerald-400 font-medium">Same day</span>
              </div>
            </div>
          </div>

          <div className="card !bg-accent-500/5 border-accent-500/20">
            <h3 className="font-semibold text-white mb-2">Need Help?</h3>
            <p className="text-xs text-dark-400 mb-3">
              Check our FAQ for common questions and quick answers.
            </p>
            <Link to="/support"
              className="btn-secondary !py-2 !text-xs w-full text-center block">
              Browse FAQ
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
