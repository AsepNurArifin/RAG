"use client";

import { useState, useRef, useEffect } from "react";
import { Message } from "../types";
import { CitationCard } from "./CitationCard";
import { User, ShieldCheck, Zap, Bot, Pencil } from "lucide-react";
import ReactMarkdown from 'react-markdown';
import rehypeSanitize from 'rehype-sanitize';
import remarkGfm from 'remark-gfm';
import { Card, CardContent } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { motion } from "framer-motion";

interface MessageBubbleProps {
  message: Message;
  onEdit?: (messageId: string, newContent: string) => void;
  isLoading?: boolean;
}

export function MessageBubble({ message, onEdit, isLoading }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const [mounted, setMounted] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(message.content);
  const editTextareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Auto-resize edit textarea
  useEffect(() => {
    if (isEditing && editTextareaRef.current) {
      editTextareaRef.current.style.height = "auto";
      editTextareaRef.current.style.height = `${Math.min(editTextareaRef.current.scrollHeight, 200)}px`;
    }
  }, [isEditing, editContent]);

  // Focus edit textarea when entering edit mode
  useEffect(() => {
    if (isEditing && editTextareaRef.current) {
      editTextareaRef.current.focus();
      editTextareaRef.current.setSelectionRange(editContent.length, editContent.length);
    }
  }, [isEditing]);

  const handleEditKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      e.preventDefault();
      setIsEditing(false);
      setEditContent(message.content);
      return;
    }
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSaveAndResend();
    }
  };

  const handleSaveAndResend = () => {
    if (!editContent.trim() || isLoading) return;
    onEdit?.(message.id, editContent);
    setIsEditing(false);
  };

  const handleStartEdit = () => {
    setEditContent(message.content);
    setIsEditing(true);
  };

  // User Message
  if (isUser) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.3 }}
        className="w-full flex justify-end mb-6 group"
      >
        <div className="flex gap-4 max-w-[80%] items-start flex-row-reverse relative">
          <Avatar className="w-10 h-10 border border-slate-200 shadow-sm mt-1">
            <AvatarFallback className="bg-[#0077ff] text-white">
              <User className="w-5 h-5" />
            </AvatarFallback>
          </Avatar>

          {isEditing ? (
            <div className="bg-[#004790] text-white rounded-2xl rounded-tr-sm p-4 px-5 shadow-sm w-full">
              <textarea
                ref={editTextareaRef}
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                onKeyDown={handleEditKeyDown}
                spellCheck="false"
                rows={2}
                className="w-full bg-white/10 text-white placeholder:text-white/50 rounded-lg p-3 resize-none focus:outline-none focus:ring-2 focus:ring-white/30 text-sm leading-relaxed min-h-[60px]"
              />
              <div className="flex gap-2 mt-3 justify-end">
                <button
                  onClick={() => { setIsEditing(false); setEditContent(message.content); }}
                  className="px-4 py-1.5 bg-white/10 hover:bg-white/20 rounded-lg text-xs font-medium transition-colors"
                >
                  Batal
                </button>
                <button
                  onClick={handleSaveAndResend}
                  disabled={!editContent.trim() || isLoading}
                  className="px-4 py-1.5 bg-white/20 hover:bg-white/30 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg text-xs font-medium transition-colors"
                >
                  Kirim Ulang
                </button>
              </div>
              <p className="text-[10px] text-white/40 mt-2 text-right">
                Enter untuk kirim &middot; Shift+Enter untuk baris baru &middot; Esc untuk batal
              </p>
            </div>
          ) : (
            <div className="relative">
              <div className="bg-[#004790] text-white rounded-2xl rounded-tr-sm p-4 px-5 shadow-sm">
                <p className="text-sm font-medium leading-relaxed">
                  {message.content}
                </p>
              </div>
              {/* Edit button — desktop: visible on hover, mobile: always visible */}
              {onEdit && (
                <button
                  onClick={handleStartEdit}
                  disabled={isLoading}
                  className="absolute -left-9 top-1 p-1.5 rounded-md text-slate-400 hover:text-[#0077ff] hover:bg-[#0077ff]/10 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
                  title="Edit query"
                >
                  <Pencil className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          )}
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
                  remarkPlugins={[remarkGfm]}
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
