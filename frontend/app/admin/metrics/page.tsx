"use client";

import { useEffect, useState } from "react";
import { api } from "../../../lib/api";
import { ShieldCheck, TrendingUp, FileText, ArrowRight, Activity, Percent } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";

export default function MetricsDashboard() {
  const [metrics, setMetrics] = useState<any>(null);

  useEffect(() => {
    api.getMetrics().then(setMetrics).catch(console.error);
  }, []);

  return (
    <div className="w-full max-w-5xl mx-auto px-4 sm:px-6 md:px-8">
      <motion.div 
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6 sm:mb-8"
      >
        <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">Audit Settings & Metrics</h2>
        <p className="text-slate-500 mt-2 text-xs sm:text-sm">
          Pantau performa model, total pencarian, tingkat akurasi verifikasi, dan status indeks sistem.
        </p>
      </motion.div>

      {/* Top Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6 mb-6 sm:mb-8">
        
        {/* Total Verifications */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
          <Card className="shadow-sm border-slate-200 overflow-hidden bg-[#e6f0fa] relative group">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 bg-transparent">
              <CardTitle className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Total Verifications
              </CardTitle>
              <ShieldCheck className="h-5 w-5 text-[#0077ff]" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-slate-900">
                {metrics?.total_queries?.toLocaleString() || "0"}
              </div>
              <p className="text-xs text-emerald-600 flex items-center mt-2 font-medium">
                <TrendingUp className="w-3.5 h-3.5 mr-1" /> 
                +2.4% vs minggu lalu
              </p>
            </CardContent>
          </Card>
        </motion.div>

        {/* Average Confidence Dial */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <Card className="shadow-sm border-slate-200 overflow-hidden bg-[#e6f0fa] relative">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 bg-transparent">
              <CardTitle className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Avg Confidence
              </CardTitle>
              <Percent className="h-5 w-5 text-[#0077ff]" />
            </CardHeader>
            <CardContent className="flex items-center justify-between py-2">
              <div className="text-3xl font-bold text-slate-900">
                {Math.floor((metrics?.avg_confidence_score || 0) * 100)}%
              </div>
              <div className="relative w-14 h-14 flex items-center justify-center shrink-0">
                <svg className="w-full h-full -rotate-90 transform" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="40" fill="none" stroke="#e2e8f0" strokeWidth="10" />
                  <circle 
                    cx="50" cy="50" r="40" fill="none" 
                    stroke="#0077ff" 
                    strokeWidth="10" 
                    strokeDasharray="251.2" 
                    strokeDashoffset={251.2 - (251.2 * (metrics?.avg_confidence_score || 0))} 
                    strokeLinecap="round"
                  />
                </svg>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Documents Indexed */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
          <Card className="shadow-sm border-slate-200 overflow-hidden bg-[#e6f0fa] relative group">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 bg-transparent">
              <CardTitle className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Documents Indexed
              </CardTitle>
              <FileText className="h-5 w-5 text-[#ffcc00]" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-slate-900">
                {metrics?.total_documents?.toLocaleString() || "0"}
              </div>
              <p className="text-xs text-slate-500 mt-2 font-medium">
                Live Database Sync
              </p>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Recent Analysis Feed */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }} 
        animate={{ opacity: 1, y: 0 }} 
        transition={{ delay: 0.2 }}
        className="space-y-4"
      >
        <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2 sm:gap-4">
          <h2 className="text-lg sm:text-xl font-bold text-slate-800 flex items-center gap-2">
            <Activity className="w-5 h-5 text-[#0077ff]" />
            Recent Analysis Logs
          </h2>
          <Button variant="ghost" size="sm" className="text-[#0077ff] hover:text-[#0047b3] hover:bg-[#0077ff]/5 gap-1 self-start sm:self-auto">
            Lihat Semua <ArrowRight className="w-4 h-4" />
          </Button>
        </div>

        {/* Mobile Cards */}
        <Card className="shadow-sm border-slate-200 overflow-hidden bg-[#e6f0fa] md:hidden">
          <CardContent className="p-0">
            {metrics?.recent_logs?.length > 0 ? (
              <div className="divide-y divide-slate-200/60">
                {metrics.recent_logs.map((log: any) => {
                  const conf = log.confidence_score ? Math.floor(log.confidence_score * 100) : 0;
                  let status = "Processing";
                  let statusColor = "bg-amber-100 text-amber-800 border-amber-200";
                  let progressColor = "#f59e0b";
                  
                  if (conf >= 80) { 
                    status = "Verified"; 
                    statusColor = "bg-emerald-100 text-emerald-800 border-emerald-200";
                    progressColor = "#0077ff";
                  } else if (conf >= 50) { 
                    status = "Review"; 
                    statusColor = "bg-blue-100 text-blue-800 border-blue-200";
                    progressColor = "#3b82f6";
                  } else if (conf > 0) { 
                    status = "Flagged"; 
                    statusColor = "bg-rose-100 text-rose-800 border-rose-200";
                    progressColor = "#f43f5e";
                  }

                  const entity = log.query.length > 60 ? log.query.substring(0, 60) + "..." : log.query;

                  return (
                    <div key={log.id} className="px-4 py-3 bg-transparent">
                      <div className="flex items-start justify-between gap-3">
                        <p className="text-sm text-slate-900 font-medium leading-snug">{entity}</p>
                        <div className="flex items-center gap-2 shrink-0">
                          <div className="relative w-6 h-6 flex items-center justify-center shrink-0">
                            <svg className="w-full h-full -rotate-90 transform" viewBox="0 0 100 100">
                              <circle cx="50" cy="50" r="40" fill="none" stroke="#f1f5f9" strokeWidth="12" />
                              <circle 
                                cx="50" cy="50" r="40" fill="none" 
                                stroke={progressColor} 
                                strokeWidth="12" 
                                strokeDasharray="251.2" 
                                strokeDashoffset={251.2 - (251.2 * (conf / 100))}
                              />
                            </svg>
                          </div>
                          <span className="font-mono text-sm font-semibold" style={{ color: progressColor }}>{conf}%</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 mt-2">
                        <Badge className={`${statusColor} hover:${statusColor} border shadow-none font-medium capitalize text-xs`}>
                          {status}
                        </Badge>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="py-8 text-center text-slate-400">
                Belum ada data log analisis.
              </div>
            )}
          </CardContent>
        </Card>

        {/* Desktop Table */}
        <Card className="shadow-sm border-slate-200 overflow-hidden bg-[#e6f0fa] hidden md:block">
          <div className="overflow-x-auto bg-[#e6f0fa]">
            <Table className="bg-[#e6f0fa]">
              <TableHeader className="bg-[#0077ff]/5">
                <TableRow className="bg-transparent hover:bg-transparent border-b border-slate-200">
                  <TableHead className="font-semibold text-slate-700 px-4">Query ID</TableHead>
                  <TableHead className="font-semibold text-slate-700 px-4">Target Entity</TableHead>
                  <TableHead className="font-semibold text-slate-700 px-4">Confidence</TableHead>
                  <TableHead className="font-semibold text-slate-700 px-4">Status</TableHead>
                  <TableHead className="font-semibold text-slate-700 text-right px-4">Waktu</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody className="bg-[#e6f0fa]">
                {metrics?.recent_logs?.length > 0 ? (
                  metrics.recent_logs.map((log: any) => {
                    const conf = log.confidence_score ? Math.floor(log.confidence_score * 100) : 0;
                    let status = "Processing";
                    let statusColor = "bg-amber-100 text-amber-800 border-amber-200";
                    let progressColor = "#f59e0b";
                    
                    if (conf >= 80) { 
                      status = "Verified"; 
                      statusColor = "bg-emerald-100 text-emerald-800 border-emerald-200";
                      progressColor = "#0077ff";
                    } else if (conf >= 50) { 
                      status = "Review"; 
                      statusColor = "bg-blue-100 text-blue-800 border-blue-200";
                      progressColor = "#3b82f6";
                    } else if (conf > 0) { 
                      status = "Flagged"; 
                      statusColor = "bg-rose-100 text-rose-800 border-rose-200";
                      progressColor = "#f43f5e";
                    }

                    const time = new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }).replace('.', ':');
                    const id = log.id.split('-')[0].toUpperCase();
                    const entity = log.query.length > 50 ? log.query.substring(0, 50) + "..." : log.query;

                    return (
                      <TableRow key={log.id} className="bg-transparent hover:bg-[#0077ff]/5 border-b border-slate-200/60 transition-colors cursor-pointer">
                        <TableCell className="font-mono text-sm text-slate-500 font-semibold px-4 py-3 bg-transparent">{id}</TableCell>
                        <TableCell className="text-slate-900 font-medium px-4 py-3 bg-transparent">{entity}</TableCell>
                        <TableCell className="px-4 py-3 bg-transparent">
                          <div className="flex items-center gap-3">
                            <div className="relative w-6 h-6 flex items-center justify-center shrink-0">
                              <svg className="w-full h-full -rotate-90 transform" viewBox="0 0 100 100">
                                <circle cx="50" cy="50" r="40" fill="none" stroke="#f1f5f9" strokeWidth="12" />
                                <circle 
                                  cx="50" cy="50" r="40" fill="none" 
                                  stroke={progressColor} 
                                  strokeWidth="12" 
                                  strokeDasharray="251.2" 
                                  strokeDashoffset={251.2 - (251.2 * (conf / 100))}
                                />
                              </svg>
                            </div>
                            <span className="font-mono text-sm font-semibold" style={{ color: progressColor }}>{conf}%</span>
                          </div>
                        </TableCell>
                        <TableCell className="px-4 py-3 bg-transparent">
                          <Badge className={`${statusColor} hover:${statusColor} border shadow-none font-medium capitalize text-xs`}>
                            {status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right text-slate-500 font-mono text-xs px-4 py-3 bg-transparent">{time}</TableCell>
                      </TableRow>
                    );
                  })
                ) : (
                  <TableRow className="bg-transparent hover:bg-transparent">
                    <TableCell colSpan={5} className="py-8 text-center text-slate-400 bg-transparent">
                      Belum ada data log analisis.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </Card>
      </motion.div>
    </div>
  );
}
