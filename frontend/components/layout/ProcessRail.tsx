"use client";

import { useActiveAgent } from "../../context/ActiveAgentContext";
import { GitBranch, Search, ShieldCheck, FileText, PlayCircle } from "lucide-react";
import { motion } from "framer-motion";

export function ProcessRail() {
  const { activeAgent } = useActiveAgent();
  
  const agents = [
    { id: "orchestrator", label: "Orchestrator", icon: GitBranch },
    { id: "researcher", label: "Researcher", icon: Search },
    { id: "verifier", label: "Verifier", icon: ShieldCheck },
    { id: "summarizer", label: "Summarizer", icon: FileText },
    { id: "executor", label: "Executor", icon: PlayCircle },
  ];

  return (
    <aside className="hidden md:flex w-[64px] h-screen fixed right-0 top-0 border-l border-slate-200 bg-[#e6f0fa] flex-col items-center py-8 z-10 shadow-sm">
      <div className="relative w-full flex flex-col items-center gap-6 before:content-[''] before:absolute before:top-4 before:bottom-4 before:w-[1px] before:bg-slate-100 before:-z-10">
        {agents.map((agent) => {
          const Icon = agent.icon;
          const isActive = activeAgent === agent.id;
          
          return (
            <div key={agent.id} className="relative group flex flex-col items-center">
              <motion.div 
                animate={isActive ? { scale: 1.1 } : { scale: 1 }}
                className={`flex items-center justify-center w-10 h-10 transition-all cursor-pointer rounded-xl border
                  ${isActive 
                    ? "text-slate-900 bg-[#F2C300] border-yellow-500 ring-2 ring-offset-2 ring-[#F2C300]/50 shadow-[0_0_12px_rgba(242,195,0,0.4)] font-bold" 
                    : "text-slate-400 bg-[#e6f0fa] hover:bg-[#F2C300]/30 border-slate-200 hover:text-slate-700"
                  }`}
                title={agent.label}
              >
                <Icon className="w-5 h-5" />
              </motion.div>
              
              {/* Tooltip */}
              <div className="absolute right-12 top-1/2 -translate-y-1/2 bg-slate-900 text-white text-[10px] font-medium px-2 py-1 rounded opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity duration-200 whitespace-nowrap shadow-sm">
                {agent.label}
              </div>
            </div>
          );
        })}
      </div>
    </aside>
  );
}
