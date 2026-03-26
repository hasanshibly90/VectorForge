import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Zap } from "lucide-react";
import { useAuth } from "../hooks/useAuth";

export default function LoginPage() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (isRegister) await register(email, password);
      else await login(email, password);
      navigate("/dashboard");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Authentication failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-sm mx-auto px-4 py-24">
      <div className="card">
        <div className="flex justify-center mb-6">
          <div className="w-12 h-12 bg-accent-500 rounded-2xl flex items-center justify-center shadow-glow-lg">
            <Zap className="w-6 h-6 text-white" />
          </div>
        </div>
        <h1 className="text-xl font-bold text-white mb-6 text-center">
          {isRegister ? "Create Account" : "Welcome Back"}
        </h1>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-dark-300 mb-1.5 uppercase tracking-wider">Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required className="input-field" />
          </div>
          <div>
            <label className="block text-xs font-medium text-dark-300 mb-1.5 uppercase tracking-wider">Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={6} className="input-field" />
          </div>
          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl">
              <p className="text-xs text-red-400">{error}</p>
            </div>
          )}
          <button type="submit" disabled={submitting} className="btn-primary w-full disabled:opacity-50">
            {submitting ? "..." : isRegister ? "Create Account" : "Sign In"}
          </button>
        </form>

        <p className="text-center text-sm text-dark-400 mt-5">
          {isRegister ? "Have an account?" : "Need an account?"}{" "}
          <button onClick={() => setIsRegister(!isRegister)} className="text-accent-400 hover:text-accent-300 font-semibold">
            {isRegister ? "Sign in" : "Register"}
          </button>
        </p>
      </div>
    </div>
  );
}
