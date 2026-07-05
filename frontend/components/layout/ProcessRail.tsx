"use client";

import { useActiveAgent } from "../../context/ActiveAgentContext";
import { GitBranch, Search, ShieldCheck, FileText, PlayCircle } from "lucide-react";

export function ProcessRail() {
  const { activeAgent } = useActiveAgent();
  
  return (
    <aside className="bg-surface-container dark:bg-surface-container fixed right-0 top-0 w-[64px] h-screen border-l border-outline-variant bg-surface-container-high flex flex-col items-center py-8 space-y-8 z-10">
      
      <div className="relative w-full flex flex-col items-center gap-8 before:content-[''] before:absolute before:top-4 before:bottom-4 before:w-[1px] before:bg-outline-variant before:-z-10">
        
        {/* Orchestrator */}
        <div 
          className={`group relative flex items-center justify-center w-10 h-10 transition-all cursor-pointer rounded-full 
            ${activeAgent === "orchestrator" 
              ? "text-secondary ring-2 ring-secondary bg-surface-container glow-on-active shadow-[0_0_12px_rgba(79,168,184,0.4)]" 
              : "text-primary-container bg-surface-container hover:bg-surface-container-highest"
            }`}
          title="Orchestrator"
        >
          <GitBranch className="w-5 h-5" />
        </div>

        {/* Researcher */}
        <div 
          className={`group relative flex items-center justify-center w-10 h-10 transition-all cursor-pointer rounded-full 
            ${activeAgent === "researcher" 
              ? "text-secondary ring-2 ring-secondary bg-surface-container glow-on-active shadow-[0_0_12px_rgba(79,168,184,0.4)]" 
              : "text-primary-container bg-surface-container hover:bg-surface-container-highest"
            }`}
          title="Researcher"
        >
          <Search className="w-5 h-5" />
        </div>

        {/* Verifier */}
        <div 
          className={`group relative flex items-center justify-center w-10 h-10 transition-all cursor-pointer rounded-full 
            ${activeAgent === "verifier" 
              ? "text-secondary ring-2 ring-secondary bg-surface-container glow-on-active shadow-[0_0_12px_rgba(79,168,184,0.4)]" 
              : "text-primary-container bg-surface-container hover:bg-surface-container-highest"
            }`}
          title="Verifier"
        >
          <ShieldCheck className="w-5 h-5" />
        </div>

        {/* Summarizer */}
        <div 
          className={`group relative flex items-center justify-center w-10 h-10 transition-all cursor-pointer rounded-full 
            ${activeAgent === "summarizer" 
              ? "text-secondary ring-2 ring-secondary bg-surface-container glow-on-active shadow-[0_0_12px_rgba(79,168,184,0.4)]" 
              : "text-outline bg-surface-container hover:bg-surface-container-highest"
            }`}
          title="Summarizer"
        >
          <FileText className="w-5 h-5" />
        </div>

        {/* Executor */}
        <div 
          className={`group relative flex items-center justify-center w-10 h-10 transition-all cursor-pointer rounded-full 
            ${activeAgent === "executor" 
              ? "text-secondary ring-2 ring-secondary bg-surface-container glow-on-active shadow-[0_0_12px_rgba(79,168,184,0.4)]" 
              : "text-outline bg-surface-container hover:bg-surface-container-highest"
            }`}
          title="Executor"
        >
          <PlayCircle className="w-5 h-5" />
        </div>
      </div>
      
    </aside>
  );
}
