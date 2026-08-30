"use client";

import { useState } from "react";
import { useActiveAgent } from "../../context/ActiveAgentContext";
import { GitBranch, Search, ShieldCheck, FileText, PlayCircle, ChevronRight, ChevronLeft, Bot } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export function ProcessRail() {
  const { activeAgent } = useActiveAgent();
  const [isOpen, setIsOpen] = useState(false);

  const agents = [
    { id: "orchestrator", label: "Orchestrator", icon: GitBranch },
    { id: "researcher", label: "Researcher", icon: Search },
    { id: "verifier", label: "Verifier", icon: ShieldCheck },
    { id: "summarizer", label: "Summarizer", icon: FileText },
    { id: "executor", label: "Executor", icon: PlayCircle },
  ];

  const activeIndex = agents.findIndex((a) => a.id === activeAgent);

  return (
    <div className="hidden md:block absolute top-4 right-4 z-20">
      {/* Toggle Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="absolute -left-12 top-2 w-9 h-9 rounded-full bg-[#004790] text-white shadow-lg flex items-center justify-center hover:bg-[#0077ff] transition-colors"
        title="Toggle Agent Pipeline"
      >
        <Bot className="w-4 h-4" />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, x: 20, scale: 0.95 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 20, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="w-56 bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 bg-[#004790] text-white">
              <span className="text-xs font-semibold tracking-wide">AGENT PIPELINE</span>
              <button onClick={() => setIsOpen(false)} className="text-white/70 hover:text-white">
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>

            {/* Agents */}
            <div className="p-3 flex flex-col gap-1">
              {agents.map((agent, idx) => {
                const Icon = agent.icon;
                const isActive = activeAgent === agent.id;
                const isPast = activeIndex > -1 && idx < activeIndex;

                return (
                  <div key={agent.id} className="relative">
                    {/* Highlight berpindah antar-agent via shared layoutId */}
                    {isActive && (
                      <motion.div
                        layoutId="active-agent-highlight"
                        transition={{ type: "spring", stiffness: 500, damping: 35 }}
                        className="absolute inset-0 rounded-xl bg-[#F2C300] shadow-sm"
                      />
                    )}
                    {isPast && <div className="absolute inset-0 rounded-xl bg-[#e6f0fa]" />}
                    <div
                      className={`relative z-10 flex items-center gap-3 px-3 py-2 rounded-xl transition-colors ${
                        isActive
                          ? "text-slate-900 font-semibold"
                          : isPast
                          ? "text-[#0077ff]"
                          : "text-slate-400"
                      }`}
                    >
                      <div
                        className={`flex items-center justify-center w-8 h-8 rounded-lg ${
                          isActive ? "bg-white/30" : "bg-slate-100"
                        }`}
                      >
                        <Icon className="w-4 h-4" />
                      </div>
                      <span className="text-sm">{agent.label}</span>
                      {isActive && (
                        <motion.div
                          animate={{ scale: [1, 1.2, 1] }}
                          transition={{ repeat: Infinity, duration: 1.5 }}
                          className="ml-auto w-2 h-2 rounded-full bg-[#004790]"
                        />
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Footer */}
            <div className="px-4 py-2 bg-slate-50 border-t border-slate-100">
              <p className="text-[10px] text-slate-400 text-center">
                {activeAgent === "idle"
                  ? "Multi-agent RAG system"
                  : `Menjalankan: ${agents.find((a) => a.id === activeAgent)?.label ?? "..."}`}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
