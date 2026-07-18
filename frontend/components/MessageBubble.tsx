"use client";

import { Message } from "../types";
import { CitationCard } from "./CitationCard";
import { User, ShieldCheck, Zap, Bot } from "lucide-react";
import ReactMarkdown from 'react-markdown';
import rehypeSanitize from 'rehype-sanitize';
import { Card, CardContent } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { motion } from "framer-motion";
import { useState, useEffect } from "react";

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (isUser) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.3 }}
        className="w-full flex justify-end mb-6"
      >
        <div className="flex gap-4 max-w-[80%] items-start flex-row-reverse">
          <Avatar className="w-10 h-10 border border-slate-200 shadow-sm mt-1">
            <AvatarFallback className="bg-[#0077ff] text-white">
              <User className="w-5 h-5" />
            </AvatarFallback>
          </Avatar>
          <div className="bg-[#004790] text-white rounded-2xl rounded-tr-sm p-4 px-5 shadow-sm">
            <p className="text-sm font-medium leading-relaxed">
              {message.content}
            </p>
          </div>
        </div>
      </motion.div>
    );
  }

  // AI Response
  const confidenceScore = message.confidenceScore !== undefined ? Math.round(message.confidenceScore * 100) : 98;
  const radius = 20;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = mounted ? circumference - (confidenceScore / 100) * circumference : circumference;

  const confColor = confidenceScore >= 70 ? "#10b981" : confidenceScore >= 40 ? "#f59e0b" : "#dc2626";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="w-full mb-8"
    >
      <div className="flex gap-4 max-w-[90%] items-start">
        <Avatar className="w-10 h-10 border border-[#0077ff]/20 shadow-sm mt-1">
          <AvatarFallback className="bg-[#0077ff] text-white">
            <Bot className="w-5 h-5" />
          </AvatarFallback>
        </Avatar>

        <div className="flex-1 space-y-4">
          {/* AI Answer Area */}
          <Card className="border-slate-200 shadow-sm overflow-hidden bg-white">
            <div className="bg-[#f8fafc] border-b border-slate-100 px-6 py-3 flex justify-between items-center">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                <span className="text-xs font-semibold text-slate-600 uppercase tracking-wider">
                  Verified Response
                </span>
              </div>

              {/* Confidence Dial */}
              <div className="flex items-center gap-2" title="Confidence Score">
                <div className="relative w-6 h-6">
                  <svg className="w-full h-full transform -rotate-90" viewBox="0 0 48 48">
                    <circle
                      className="text-slate-200"
                      cx="24" cy="24" r={radius}
                      fill="none" stroke="currentColor" strokeWidth="6"
                    />
                    <circle
                      className="transition-all duration-1000 ease-out"
                      cx="24" cy="24" r={radius}
                      fill="none" stroke={confColor} strokeWidth="6"
                      strokeLinecap="round"
                      strokeDasharray={circumference}
                      strokeDashoffset={strokeDashoffset}
                      style={{ color: confColor }}
                    />
                  </svg>
                </div>
                <span className="text-xs font-bold text-slate-700">{confidenceScore}%</span>
              </div>
            </div>

            <CardContent className="p-4 sm:p-6">
              <div className="text-slate-800 text-sm leading-relaxed space-y-4 prose prose-slate max-w-none prose-p:leading-relaxed prose-pre:bg-slate-50 prose-pre:border prose-pre:border-slate-200 prose-a:text-[#0077ff] hover:prose-a:text-[#0077ff]/80">
                <ReactMarkdown
                  rehypePlugins={[rehypeSanitize]}
                  components={{
                    a: ({node, ...props}) => {
                      if (props.href === '#citation') {
                        return (
                          <Badge variant="secondary" className="px-1.5 py-0 text-[10px] font-mono cursor-pointer hover:bg-[#0077ff]/10 text-[#0077ff] align-super mx-0.5">
                            {props.children}
                          </Badge>
                        );
                      }
                      return <a {...props} />;
                    }
                  }}
                >
                  {message.content.replace(/\[(Sumber[^\]]*|\d+)\](?!\()/gi, "[$1](#citation)")}
                </ReactMarkdown>

                {/* Action Items Box */}
                {Array.isArray(message.actionItems) && message.actionItems.length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    transition={{ delay: 0.5 }}
                    className="mt-6 p-4 bg-[#F2C300]/10 rounded-xl border border-[#F2C300]/30"
                  >
                    <div className="flex items-center gap-2 text-[#d8a815] font-semibold text-xs uppercase tracking-wide mb-2">
                      <Zap className="w-4 h-4" /> Recommended Action
                    </div>
                    <ul className="space-y-2 text-sm text-slate-700">
                      {message.actionItems.map((item: any, i: number) => (
                        <li key={i} className="flex gap-2">
                          <span className="text-[#F2C300] font-bold">&gt;</span>
                          <span>{item.draft_content || item.action_type}</span>
                        </li>
                      ))}
                    </ul>
                  </motion.div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Citations Section */}
          {Array.isArray(message.citations) && message.citations.length > 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.7 }}
              className="mt-4"
            >
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3 pl-2">
                Sources & Citations
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {message.citations.map((citation, index) => (
                  <CitationCard key={index} citation={citation} index={index} />
                ))}
              </div>
            </motion.div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
