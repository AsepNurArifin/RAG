"use client";

import { Citation } from "../types";
import { FileText } from "lucide-react";

interface CitationCardProps {
  citation: Citation;
  index: number;
}

export function CitationCard({ citation, index }: CitationCardProps) {
  const source = citation.source || `REF-${index}`;
  const excerpt = citation.excerpt || "No excerpt available.";
  const relevance = citation.relevance_score ?? 0;

  return (
    <div className="paper-card p-6 relative rounded-sm shadow-sm flex flex-col justify-between h-48 hover:-translate-y-1 transition-transform cursor-pointer">
      {/* Top right tag */}
      <div className="absolute top-0 right-0 bg-graphite-line text-paper-cream px-2 py-1 font-data-mono text-[10px] rounded-bl-sm uppercase">
        DOC-{source.substring(0, 8)}
      </div>
      
      <div>
        <div className="flex items-center gap-2 mb-3 text-rust">
          <FileText className="w-4 h-4 text-rust" />
          <span className="font-data-label text-data-label uppercase">
            {source}
          </span>
        </div>
        <p className="font-body-sm text-body-sm opacity-90 line-clamp-3">
          &quot;{excerpt}&quot;
        </p>
      </div>
      
      <div className="mt-4 text-xs font-data-mono opacity-60 flex items-center justify-between">
        <span>MATCH: {Math.floor(relevance * 100)}%</span>
        <span className="uppercase">{relevance > 0.8 ? "VERIFIED" : "PENDING_REVIEW"}</span>
      </div>
    </div>
  );
}
