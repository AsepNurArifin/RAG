"use client";

import { Message } from "../types";
import { CitationCard } from "./CitationCard";
import { User, ShieldCheck, Zap, RefreshCw } from "lucide-react";

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="w-full flex justify-end">
        <div className="bg-surface-container-highest border border-outline-variant rounded p-6 max-w-[80%] relative before:content-[''] before:absolute before:right-[-8px] before:top-6 before:w-0 before:h-0 before:border-y-8 before:border-y-transparent before:border-l-8 before:border-l-outline-variant">
          <div className="flex items-center gap-2 mb-2">
            <User className="w-4 h-4 text-primary" />
            <span className="font-data-label text-data-label text-primary uppercase tracking-widest">Operator Input</span>
          </div>
          <p className="font-data-mono text-data-mono text-on-surface">
            {message.content}
          </p>
        </div>
      </div>
    );
  }

  // AI Response
  const confidenceScore = message.confidenceScore !== undefined ? Math.round(message.confidenceScore * 100) : 98;
  const radius = 20;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (confidenceScore / 100) * circumference;

  return (
    <div className="w-full space-y-4">
      {/* AI Answer Area */}
      <section className="bg-surface-container border border-outline-variant rounded p-8 relative">
        <div className="flex justify-between items-start mb-6">
          <div>
            <h2 className="font-h3 text-h3 text-on-surface mb-1">Synthesized Findings</h2>
            <p className="font-data-label text-data-label text-secondary uppercase tracking-widest flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-secondary animate-pulse" /> 
              STATUS: VERIFICATION COMPLETE
            </p>
          </div>
          
          {/* Confidence Dial */}
          <div className="flex flex-col items-center">
            <div className="relative w-12 h-12">
              <svg className="w-full h-full transform -rotate-90" viewBox="0 0 48 48">
                {/* Background Circle */}
                <circle 
                  className="text-surface-container-highest" 
                  cx="24" cy="24" r={radius} 
                  fill="none" stroke="currentColor" strokeWidth="4" 
                />
                {/* Progress Circle */}
                <circle 
                  className="text-primary-container dial-circle" 
                  cx="24" cy="24" r={radius} 
                  fill="none" stroke="currentColor" strokeWidth="4"
                  strokeLinecap="round"
                  strokeDasharray={circumference}
                  strokeDashoffset={strokeDashoffset}
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center font-data-mono text-data-label text-on-surface">
                {confidenceScore}%
              </div>
            </div>
            <span className="font-data-label text-[10px] text-outline-variant mt-1 uppercase">Confidence Level</span>
          </div>
        </div>

        <div className="font-body-md text-body-md text-on-surface-variant leading-relaxed space-y-4">
          {message.content.split("\n\n").map((para, i) => (
            <p key={i}>{para}</p>
          ))}
          
          {/* Action Items Box (if any action items exist) */}
          {message.actionItems && message.actionItems.length > 0 && (
            <div className="mt-4 p-4 bg-surface-container-lowest border-l-2 border-secondary font-data-mono text-data-mono text-sm">
              <span className="text-secondary flex items-center gap-1.5"><Zap className="w-4 h-4" /> INFERENCE_ENGINE: </span> Recommended Action.<br/>
              {message.actionItems.map((item: any, i: number) => (
                <div key={i}>&gt; RECOMMENDATION: {item.draft_content || item.action_type}</div>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Citations Section */}
      {message.citations && message.citations.length > 0 && (
        <section className="space-y-4 mt-8">
          <h3 className="font-data-label text-data-label text-on-surface-variant uppercase tracking-widest border-b border-outline-variant pb-2">
            Audit Citations & Source Data
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-gutter">
            {message.citations.map((citation, index) => (
              <CitationCard key={index} citation={citation} index={index} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
