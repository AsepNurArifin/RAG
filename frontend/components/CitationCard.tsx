"use client";

import { Citation } from "../types";
import { FileText, CheckCircle2, Clock } from "lucide-react";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { motion } from "framer-motion";

interface CitationCardProps {
  citation: Citation;
  index: number;
}

export function CitationCard({ citation, index }: CitationCardProps) {
  const source = citation.source || `REF-${index}`;
  const excerpt = citation.excerpt || "No excerpt available.";
  const relevance = citation.relevance_score ?? 0;
  const date = citation.date || "";
  
  const handleClick = () => {
    if (citation.source) {
      const el = document.getElementById(`citation-${index}`);
      el?.scrollIntoView({ behavior: "smooth" });
    }
  };

  const isVerified = relevance > 0.8;

  return (
    <motion.div
      whileHover={{ y: -4 }}
      transition={{ type: "spring", stiffness: 300 }}
    >
      <Card 
        className="h-full flex flex-col justify-between cursor-pointer hover:shadow-md transition-shadow border-slate-200 overflow-hidden bg-[#e6f0fa]"
        onClick={handleClick}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') handleClick(); }}
      >
        <CardHeader className="p-4 pb-2 relative">
          <div className="absolute top-0 right-0 bg-[#0077ff]/10 text-[#0077ff] px-3 py-1 text-[10px] font-mono font-medium rounded-bl-lg border-b border-l border-[#0077ff]/20">
            DOC-{source.substring(0, 8)}
          </div>
          <div className="flex items-center gap-2 text-[#0077ff] mt-2">
            <FileText className="w-4 h-4" />
            <span className="font-semibold text-sm uppercase line-clamp-1 break-all" title={source}>
              {source}
            </span>
          </div>
        </CardHeader>
        
        <CardContent className="p-4 pt-0 flex-grow">
          <p className="text-sm text-slate-600 italic line-clamp-3">
            &quot;{excerpt}&quot;
          </p>
        </CardContent>
        
        <CardFooter className="p-4 pt-0 border-t border-slate-100 mt-auto flex items-center justify-between text-xs text-slate-500">
          <div className="flex items-center gap-2">
            {date && <span className="font-medium">{date}</span>}
            <Badge variant="secondary" className="font-mono text-[10px]">
              MATCH {Math.floor(relevance * 100)}%
            </Badge>
          </div>
          <div className="flex items-center gap-1">
            {isVerified ? (
              <Badge variant="outline" className="text-emerald-600 border-emerald-200 bg-emerald-50 gap-1 rounded-sm px-1.5 py-0.5">
                <CheckCircle2 className="w-3 h-3" /> VERIFIED
              </Badge>
            ) : (
              <Badge variant="outline" className="text-amber-600 border-amber-200 bg-amber-50 gap-1 rounded-sm px-1.5 py-0.5">
                <Clock className="w-3 h-3" /> PENDING
              </Badge>
            )}
          </div>
        </CardFooter>
      </Card>
    </motion.div>
  );
}
