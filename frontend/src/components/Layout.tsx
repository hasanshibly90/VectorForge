import { useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { Menu, X, Zap } from "lucide-react";
import { useAuth } from "../hooks/useAuth";

const navLinks = [
  { to: "/", label: "Convert" },
  { to: "/prompts", label: "Prompts" },
  { to: "/batch", label: "Batch" },
  { to: "/dashboard", label: "Dashboard" },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-50 glass border-b border-dark-700/50">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 group">
            <div className="w-7 h-7 sm:w-8 sm:h-8 bg-accent-500 rounded-lg flex items-center justify-center shadow-glow group-hover:shadow-glow-lg transition-shadow">
              <Zap className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-white" />
            </div>
            <span className="font-bold text-base sm:text-lg text-white">
              Vector<span className="text-accent-400">Forge</span>
            </span>
          </Link>

          {/* Desktop nav */}
          <nav className="hidden sm:flex items-center gap-1">
            {navLinks.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                className={`px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                  location.pathname === link.to
                    ? "bg-accent-500/15 text-accent-400"
                    : "text-dark-300 hover:text-white hover:bg-dark-700/50"
                }`}
              >
                {link.label}
              </Link>
            ))}
            <div className="w-px h-5 bg-dark-700 mx-2" />
            {user ? (
              <div className="flex items-center gap-3">
                <span className="text-xs text-dark-400 font-mono truncate max-w-[120px]">{user.email}</span>
                <button onClick={logout} className="text-xs text-dark-400 hover:text-accent-400 transition-colors">
                  Logout
                </button>
              </div>
            ) : (
              <Link to="/login" className="btn-secondary !py-1.5 !px-3.5 !text-xs">Sign In</Link>
            )}
          </nav>

          {/* Mobile hamburger */}
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="sm:hidden p-2 text-dark-300 hover:text-white"
          >
            {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>

        {/* Mobile menu */}
        {mobileOpen && (
          <div className="sm:hidden border-t border-dark-700/50 bg-dark-900/95 backdrop-blur-xl">
            <div className="px-4 py-3 space-y-1">
              {navLinks.map((link) => (
                <Link
                  key={link.to}
                  to={link.to}
                  onClick={() => setMobileOpen(false)}
                  className={`block px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                    location.pathname === link.to
                      ? "bg-accent-500/15 text-accent-400"
                      : "text-dark-300 hover:text-white hover:bg-dark-800"
                  }`}
                >
                  {link.label}
                </Link>
              ))}
              <div className="border-t border-dark-700/50 pt-2 mt-2">
                {user ? (
                  <button
                    onClick={() => { logout(); setMobileOpen(false); }}
                    className="block w-full text-left px-3 py-2.5 text-sm text-dark-400 hover:text-accent-400"
                  >
                    Logout ({user.email})
                  </button>
                ) : (
                  <Link
                    to="/login"
                    onClick={() => setMobileOpen(false)}
                    className="block px-3 py-2.5 text-sm font-medium text-accent-400"
                  >
                    Sign In
                  </Link>
                )}
              </div>
            </div>
          </div>
        )}
      </header>

      <main className="flex-1 overflow-x-hidden">
        <Outlet />
      </main>

      <footer className="border-t border-dark-800 py-4 sm:py-6">
        <div className="max-w-6xl mx-auto px-4 flex items-center justify-between text-xs text-dark-500">
          <span>VectorForge</span>
          <span className="font-mono">v0.1.0</span>
        </div>
      </footer>
    </div>
  );
}
