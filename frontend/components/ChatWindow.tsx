"use client";

import { useState, useRef, useEffect } from "react";
import { useChatStream } from "../hooks/useChatStream";
import { MessageBubble } from "./MessageBubble";
import { LoadingIndicator } from "./LoadingIndicator";
import { Terminal, Send, Lightbulb, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card } from "@/components/ui/card";
import { motion } from "framer-motion";

interface ChatWindowProps {
  onSessionChange?: (sessionId: string | undefined) => void;
  externalSessionId?: string;
}

export function ChatWindow({ onSessionChange, externalSessionId }: ChatWindowProps) {
  const { messages, isLoading, sendMessage, clearChat, messagesEndRef, sessionId, loadSessionHistory } = useChatStream();
  const [inputValue, setInputValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (externalSessionId) {
      loadSessionHistory(externalSessionId);
    } else {
      clearChat();
    }
  }, [externalSessionId, loadSessionHistory, clearChat]);

  useEffect(() => {
    onSessionChange?.(sessionId);
  }, [sessionId, onSessionChange]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [inputValue]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (inputValue.trim() && !isLoading) {
      sendMessage(inputValue);
      setInputValue("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm relative">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-gradient-to-r from-[#004790] to-[#0077ff]">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-white/20 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-white font-semibold text-base leading-tight">EnterpriseMind AI</h1>
            <p className="text-white/70 text-xs">Multi-Agent Knowledge Assistant</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 text-[11px] text-white/80 bg-white/10 px-2.5 py-1 rounded-full">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            System Active
          </span>
        </div>
      </div>

      {/* Messages Area */}
      <ScrollArea className="flex-1 min-h-0 p-6 pb-40">
        <div className="max-w-4xl mx-auto flex flex-col gap-6">
          {messages.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center mt-24"
            >
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-[#0077ff]/10 text-[#0077ff] mb-6 shadow-sm">
                <Lightbulb className="w-8 h-8" />
              </div>
              <h3 className="text-2xl font-bold text-slate-800 mb-3">Apa yang ingin Anda ketahui?</h3>
              <p className="text-slate-500 max-w-md mx-auto mb-10">
                Tanyakan seputar kebijakan, dokumen internal, atau analisis khusus berdasarkan EnterpriseMind Knowledge Vault.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-2xl mx-auto">
                {[
                  "Berapa hari cuti tahunan?",
                  "Buatkan draft email peringatan SP1",
                  "Analisis kebijakan WFH",
                  "Siapa CEO perusahaan?",
                ].map((suggestion, i) => (
                  <motion.div
                    key={i}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    <Card
                      onClick={() => sendMessage(suggestion)}
                      className="p-4 flex items-center justify-center text-sm font-medium text-slate-600 hover:text-[#0077ff] hover:border-[#0077ff]/30 hover:bg-[#0077ff]/5 bg-white border-slate-200 cursor-pointer transition-colors h-full shadow-sm text-center"
                    >
                      "{suggestion}"
                    </Card>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          ) : (
            <div className="pt-4">
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              {isLoading && <LoadingIndicator />}
              <div ref={messagesEndRef} className="h-4" />
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Floating Input Area */}
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-white via-white to-transparent pt-10 pb-6 px-6 pointer-events-none">
        <div className="max-w-4xl mx-auto pointer-events-auto">
          <motion.form
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.2 }}
            onSubmit={handleSubmit}
            className="relative flex items-end bg-white border border-slate-300 shadow-lg rounded-2xl p-2 focus-within:ring-2 focus-within:ring-[#0077ff]/20 focus-within:border-[#0077ff] transition-all"
          >
            <div className="flex-shrink-0 p-3 text-slate-400">
              <Terminal className="w-5 h-5" />
            </div>

            <textarea
              id="query-input"
              ref={textareaRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              spellCheck="false"
              placeholder="Tanyakan sesuatu..."
              disabled={isLoading}
              rows={1}
              className="flex-1 bg-transparent border-none py-3 px-2 focus:ring-0 focus:outline-none resize-none min-h-[44px] max-h-[120px] text-slate-800 placeholder:text-slate-400"
            />

            <div className="p-1 flex-shrink-0">
              <Button
                type="submit"
                size="icon"
                disabled={!inputValue.trim() || isLoading}
                className={`h-10 w-10 rounded-xl transition-all ${
                  inputValue.trim() && !isLoading
                    ? "bg-[#0077ff] hover:bg-[#0047b3] text-white shadow-md"
                    : "bg-slate-100 text-slate-400"
                }`}
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>
          </motion.form>
          <div className="text-center mt-2">
            <span className="text-[10px] text-slate-400 font-medium">EnterpriseMind AI dapat melakukan kesalahan. Harap verifikasi informasi penting.</span>
          </div>
        </div>
      </div>
    </div>
  );
}
