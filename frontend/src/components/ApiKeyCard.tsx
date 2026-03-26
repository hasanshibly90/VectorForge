import { useState } from "react";
import { Copy, Eye, EyeOff, Key, Plus, Trash2 } from "lucide-react";
import { createApiKey, revokeApiKey } from "../api/client";
import type { ApiKey } from "../types";

interface ApiKeyCardProps {
  apiKeys: ApiKey[];
  onRefresh: () => void;
}

export default function ApiKeyCard({ apiKeys, onRefresh }: ApiKeyCardProps) {
  const [newKeyName, setNewKeyName] = useState("");
  const [newRawKey, setNewRawKey] = useState<string | null>(null);
  const [showKey, setShowKey] = useState(false);
  const [creating, setCreating] = useState(false);

  const handleCreate = async () => {
    setCreating(true);
    try {
      const res = await createApiKey(newKeyName || undefined);
      setNewRawKey(res.data.raw_key);
      setNewKeyName("");
      onRefresh();
    } finally {
      setCreating(false);
    }
  };

  const handleRevoke = async (id: string) => {
    await revokeApiKey(id);
    onRefresh();
  };

  const copyKey = (key: string) => navigator.clipboard.writeText(key);

  return (
    <div className="card">
      <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
        <Key className="w-4 h-4 text-accent-400" /> API Keys
      </h3>

      {newRawKey && (
        <div className="mb-4 p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl">
          <p className="text-xs text-emerald-400 font-semibold mb-2">
            Copy now -- won't be shown again
          </p>
          <div className="flex items-center gap-2">
            <code className="flex-1 text-xs bg-dark-900 px-3 py-2 rounded-lg font-mono text-emerald-300 break-all">
              {showKey ? newRawKey : "vf_live_" + "*".repeat(32)}
            </code>
            <button onClick={() => setShowKey(!showKey)} className="p-2 text-dark-400 hover:text-white">
              {showKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            </button>
            <button onClick={() => copyKey(newRawKey)} className="p-2 text-dark-400 hover:text-accent-400">
              <Copy className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      <div className="flex gap-2 mb-4">
        <input
          type="text"
          placeholder="Key name (optional)"
          value={newKeyName}
          onChange={(e) => setNewKeyName(e.target.value)}
          className="input-field"
        />
        <button onClick={handleCreate} disabled={creating} className="btn-primary whitespace-nowrap !px-4">
          <Plus className="w-4 h-4" />
        </button>
      </div>

      <div className="space-y-2">
        {apiKeys.filter((k) => k.is_active).map((key) => (
          <div key={key.id} className="flex items-center justify-between px-4 py-3 bg-dark-800 rounded-xl border border-dark-700/50">
            <div>
              <p className="text-sm font-medium text-gray-200">{key.name || "Unnamed"}</p>
              <p className="text-xs text-dark-400 font-mono">{key.key_prefix}...</p>
            </div>
            <button onClick={() => handleRevoke(key.id)} className="p-1.5 text-dark-500 hover:text-red-400 transition-colors">
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
        {apiKeys.filter((k) => k.is_active).length === 0 && (
          <p className="text-sm text-dark-500 text-center py-4">No API keys yet</p>
        )}
      </div>
    </div>
  );
}
