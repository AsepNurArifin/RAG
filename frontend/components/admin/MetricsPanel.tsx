"use client";

import { useState, useEffect } from "react";
import { api } from "../../lib/api";
import { Activity, Zap, ShieldAlert, Coins } from "lucide-react";

export function MetricsPanel() {
  const [metrics, setMetrics] = useState<any>(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const data = await api.getMetrics();
        setMetrics(data);
      } catch (e) {
        console.error(e);
      }
    };
    fetchMetrics();
    // Auto refresh every 30s
    const interval = setInterval(fetchMetrics, 30000);
    return () => clearInterval(interval);
  }, []);

  if (!metrics) {
    return <div className="h-24 bg-white/5 animate-pulse rounded-2xl border border-white/10"></div>;
  }

  const stats = [
    {
      name: "Total Queries",
      value: metrics.total_queries,
      icon: <Activity className="w-5 h-5 text-blue-400" />,
    },
    {
      name: "Avg Latency",
      value: `${(metrics.avg_latency_ms / 1000).toFixed(1)}s`,
      icon: <Zap className="w-5 h-5 text-amber-400" />,
    },
    {
      name: "Confidence Avg",
      value: `${(metrics.avg_confidence_score * 100).toFixed(0)}%`,
      icon: <ShieldAlert className="w-5 h-5 text-emerald-400" />,
    },
    {
      name: "Est. Cost (USD)",
      value: `$${metrics.total_estimated_cost_usd.toFixed(4)}`,
      icon: <Coins className="w-5 h-5 text-purple-400" />,
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
      {stats.map((stat, i) => (
        <div key={i} className="p-4 bg-white/5 border border-white/10 rounded-2xl flex items-center space-x-4">
          <div className="p-3 bg-black/40 rounded-xl">
            {stat.icon}
          </div>
          <div>
            <p className="text-xs text-white/50">{stat.name}</p>
            <p className="text-lg font-bold text-white/90">{stat.value}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
