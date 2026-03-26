import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Activity, TrendingUp, XOctagon } from "lucide-react";
import { listApiKeys, listConversions, getUsage, getUsageHistory } from "../api/client";
import { useAuth } from "../hooks/useAuth";
import ApiKeyCard from "../components/ApiKeyCard";
import UsageChart from "../components/UsageChart";
import FileList from "../components/FileList";
import type { ApiKey, Conversion, UsageData } from "../types";

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [conversions, setConversions] = useState<Conversion[]>([]);
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [usageHistory, setUsageHistory] = useState<UsageData[]>([]);

  useEffect(() => { if (!loading && !user) navigate("/login"); }, [user, loading, navigate]);

  const loadData = async () => {
    try {
      const [k, c, u, h] = await Promise.all([listApiKeys(), listConversions(1, 10), getUsage(), getUsageHistory()]);
      setApiKeys(k.data);
      setConversions(c.data.conversions);
      setUsage(u.data);
      setUsageHistory(h.data.history);
    } catch {}
  };

  useEffect(() => { if (user) loadData(); }, [user]);
  if (loading || !user) return null;

  return (
    <div className="max-w-5xl mx-auto px-4 py-16">
      <h1 className="text-3xl font-extrabold text-white mb-8 tracking-tight">Dashboard</h1>

      {usage && (
        <div className="grid grid-cols-3 gap-4 mb-8">
          {[
            { label: "Total", value: usage.total_conversions, icon: Activity, color: "text-accent-400" },
            { label: "Successful", value: usage.successful_conversions, icon: TrendingUp, color: "text-emerald-400" },
            { label: "Failed", value: usage.failed_conversions, icon: XOctagon, color: "text-red-400" },
          ].map((s) => (
            <div key={s.label} className="card">
              <div className="flex items-center gap-2 mb-2">
                <s.icon className={`w-4 h-4 ${s.color}`} />
                <span className="text-xs text-dark-400 uppercase tracking-wider font-medium">{s.label}</span>
              </div>
              <p className={`text-3xl font-bold ${s.color}`}>{s.value}</p>
            </div>
          ))}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2 mb-8">
        <UsageChart data={usageHistory} />
        <ApiKeyCard apiKeys={apiKeys} onRefresh={loadData} />
      </div>

      <div>
        <h2 className="font-semibold text-white mb-4">Recent Conversions</h2>
        <FileList conversions={conversions} />
        {conversions.length === 0 && (
          <div className="card text-center py-12">
            <p className="text-dark-500">No conversions yet</p>
          </div>
        )}
      </div>
    </div>
  );
}
