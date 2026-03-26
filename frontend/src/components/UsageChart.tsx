import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { BarChart3 } from "lucide-react";
import type { UsageData } from "../types";

interface UsageChartProps {
  data: UsageData[];
}

export default function UsageChart({ data }: UsageChartProps) {
  const chartData = data.map((d) => ({
    period: new Date(d.period_start).toLocaleDateString("en-US", { month: "short" }),
    successful: d.successful_conversions,
    failed: d.failed_conversions,
  })).reverse();

  return (
    <div className="card">
      <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
        <BarChart3 className="w-4 h-4 text-accent-400" /> Usage
      </h3>
      {chartData.length === 0 ? (
        <p className="text-sm text-dark-500 text-center py-8">No data yet</p>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={chartData}>
            <XAxis dataKey="period" tick={{ fontSize: 11, fill: "#7a7a8e" }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: "#7a7a8e" }} axisLine={false} tickLine={false} allowDecimals={false} />
            <Tooltip
              contentStyle={{ background: "#1e1e2a", border: "1px solid #2e2e3e", borderRadius: 12, fontSize: 12 }}
              labelStyle={{ color: "#a3a3b3" }}
            />
            <Bar dataKey="successful" fill="#22c55e" name="OK" radius={[6, 6, 0, 0]} />
            <Bar dataKey="failed" fill="#ef4444" name="Failed" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
