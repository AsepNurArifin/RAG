"use client";

import { useEffect, useState } from "react";
import { api } from "../../../lib/api";
import { ShieldCheck, TrendingUp, FileText, ArrowRight } from "lucide-react";

export default function MetricsDashboard() {
  const [metrics, setMetrics] = useState<any>(null);

  useEffect(() => {
    // In a real app, this would fetch from backend API
    api.getMetrics().then(setMetrics).catch(console.error);
  }, []);

  return (
    <div className="w-full max-w-6xl mx-auto py-8">
      {/* Top Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-gutter mb-8">
        
        {/* Total Verifications */}
        <div className="bg-surface-container border-instrument p-6 relative overflow-hidden group rounded">
          <div className="absolute top-0 right-0 p-3 opacity-20 group-hover:opacity-100 transition-opacity">
            <ShieldCheck className="w-10 h-10 text-cyan" />
          </div>
          <h3 className="font-data-label text-data-label text-outline mb-2 uppercase tracking-wider">
            Total Verifications
          </h3>
          <p className="font-h1 text-h1 text-on-surface">
            {metrics?.total_queries?.toLocaleString() || "14,293"}
          </p>
          <div className="mt-4 flex items-center font-data-mono text-data-mono text-cyan text-xs">
            <TrendingUp className="w-3.5 h-3.5 mr-1" /> 
            +2.4% vs last week
          </div>
        </div>

        {/* Average Confidence Dial */}
        <div className="bg-surface-container border-instrument p-6 flex flex-col items-center justify-center relative rounded">
          <h3 className="font-data-label text-data-label text-outline absolute top-6 left-6 uppercase tracking-wider">
            Avg Confidence
          </h3>
          <div className="relative w-32 h-32 mt-4 flex items-center justify-center">
            <svg className="w-full h-full -rotate-90 transform" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="45" fill="none" stroke="var(--color-graphite-line)" strokeWidth="8" />
              <circle 
                className="dial-circle" 
                cx="50" cy="50" r="45" fill="none" 
                stroke="var(--color-brass)" 
                strokeWidth="8" 
                strokeDasharray="282.7" 
                strokeDashoffset={282.7 - (282.7 * (metrics?.avg_confidence_score || 0.88))} 
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute font-data-mono text-data-mono text-h3 font-bold text-on-surface flex items-baseline">
              {Math.floor((metrics?.avg_confidence_score || 0.88) * 100)}<span className="text-sm ml-1 text-outline">%</span>
            </div>
          </div>
        </div>

        {/* Documents Indexed */}
        <div className="bg-surface-container border-instrument p-6 relative overflow-hidden group rounded">
          <div className="absolute top-0 right-0 p-3 opacity-20 group-hover:opacity-100 transition-opacity">
            <FileText className="w-10 h-10 text-primary" />
          </div>
          <h3 className="font-data-label text-data-label text-outline mb-2 uppercase tracking-wider">
            Documents Indexed
          </h3>
          <p className="font-h1 text-h1 text-on-surface">
            {metrics?.total_documents?.toLocaleString() || "2.4K"}
          </p>
          <div className="mt-4 flex items-center font-data-mono text-data-mono text-outline text-xs">
            Last sync: 2 mins ago
          </div>
        </div>
      </div>

      {/* Recent Analysis Feed */}
      <div className="mb-6 flex justify-between items-end">
        <h2 className="font-h3 text-h3 text-on-surface">Recent Analysis Logs</h2>
        <button className="font-data-label text-data-label text-cyan hover:text-secondary-fixed flex items-center">
          View All <ArrowRight className="w-4 h-4 ml-1" />
        </button>
      </div>

      <div className="bg-surface-container border-instrument overflow-hidden rounded">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-graphite-line bg-surface-container-high font-data-label text-data-label text-outline uppercase">
              <th className="py-4 px-6 font-semibold">Query ID</th>
              <th className="py-4 px-6 font-semibold">Target Entity</th>
              <th className="py-4 px-6 font-semibold">Confidence</th>
              <th className="py-4 px-6 font-semibold">Status</th>
              <th className="py-4 px-6 font-semibold text-right">Time</th>
            </tr>
          </thead>
          <tbody className="font-body-sm text-body-sm divide-y divide-graphite-line">
            {/* Mock Rows */}
            {[
              { id: "AX-992", entity: "Project Polaris Financials Q3", conf: 95, status: "Verified", time: "10:42 AM", color: "cyan" },
              { id: "AX-991", entity: "Merger Compliance Audit", conf: 68, status: "Processing", time: "10:15 AM", color: "outline" },
              { id: "AX-990", entity: "Supply Chain Vulnerability", conf: 32, status: "Flagged", time: "09:55 AM", color: "rust" },
            ].map((row) => (
              <tr key={row.id} className="hover:bg-surface-container-highest transition-colors group cursor-pointer">
                <td className={`py-4 px-6 font-data-mono text-${row.color}`}>{row.id}</td>
                <td className="py-4 px-6 text-on-surface font-medium">{row.entity}</td>
                <td className="py-4 px-6">
                  <div className="flex items-center gap-3">
                    <svg className="w-6 h-6 -rotate-90 transform" viewBox="0 0 100 100">
                      <circle cx="50" cy="50" r="40" fill="none" stroke="var(--color-graphite-line)" strokeWidth="12" />
                      <circle 
                        cx="50" cy="50" r="40" fill="none" 
                        stroke={`var(--color-${row.color === "cyan" ? "brass" : row.color})`} 
                        strokeWidth="12" 
                        strokeDasharray="251" 
                        strokeDashoffset={251 - (251 * (row.conf / 100))}
                      />
                    </svg>
                    <span className={`font-data-mono text-${row.color === "cyan" ? "brass" : row.color}`}>{row.conf}%</span>
                  </div>
                </td>
                <td className="py-4 px-6">
                  <span className={`inline-flex items-center px-2 py-1 rounded-sm bg-surface text-${row.color} border border-${row.color}/30 text-xs font-data-label uppercase`}>
                    {row.status}
                  </span>
                </td>
                <td className="py-4 px-6 text-right text-outline font-data-mono text-xs">{row.time}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
