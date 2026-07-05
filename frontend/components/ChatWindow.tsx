"use client";

import { useState, useRef, useEffect } from "react";
import { useChatStream } from "../hooks/useChatStream";
import { MessageBubble } from "./MessageBubble";
import { LoadingIndicator } from "./LoadingIndicator";
import { Terminal, Send } from "lucide-react";

interface ChatWindowProps {
  onSessionChange?: (sessionId: string | undefined) => void;
  externalSessionId?: string;
}

export function ChatWindow({ onSessionChange, externalSessionId }: ChatWindowProps) {
  const { messages, isLoading, sendMessage, clearChat, messagesEndRef, sessionId, loadSessionHistory } = useChatStream();
  const [inputValue, setInputValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // When external session changes (from sidebar), load its history
  useEffect(() => {
    if (externalSessionId) {
      loadSessionHistory(externalSessionId);
    } else {
      clearChat();
    }
  }, [externalSessionId, loadSessionHistory, clearChat]);

  // Notify parent when sessionId changes
  useEffect(() => {
    onSessionChange?.(sessionId);
  }, [sessionId, onSessionChange]);

  // Auto-resize textarea
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
    <div className="w-full flex flex-col space-y-8 pb-32">
      
      {/* AI Answer Area (Messages List) */}
      <div className="flex flex-col space-y-8">
        {messages.length === 0 ? (
          <div className="text-center opacity-70 mt-20">
            <h3 className="font-h3 text-h3 text-on-surface mb-2">Awaiting Parameters</h3>
            <p className="font-body-md text-body-md text-on-surface-variant max-w-md mx-auto">
              Please enter your query below to initiate analysis across the EnterpriseMind Knowledge Vault.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-8 w-full max-w-lg mx-auto">
              {["Berapa hari cuti tahunan?", "Buatkan draft email peringatan SP1", "Analisis kebijakan WFH", "Siapa CEO perusahaan?"].map((suggestion, i) => (
                <button
                  key={i}
                  onClick={() => sendMessage(suggestion)}
                  className="p-3 text-sm text-left border border-outline bg-surface-container hover:bg-surface-container-highest rounded text-on-surface/80 hover:text-on-surface transition-colors cursor-pointer"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            {isLoading && <LoadingIndicator />}
            <div ref={messagesEndRef} className="h-1" />
          </>
        )}
      </div>

      {/* Technical Query Input (Fixed at bottom) */}
      <div className="fixed bottom-margin left-[280px] right-[64px] flex justify-center z-10 bg-background/80 backdrop-blur-sm pt-4 pb-4 px-gutter">
        <div className="w-full max-w-6xl">
          <label htmlFor="query-input" className="block font-data-label text-data-label text-on-surface-variant uppercase tracking-widest mb-2">
            Active Query Parameter
          </label>
          
          <form 
            onSubmit={handleSubmit}
            className="relative flex items-center w-full bg-surface-container-high border border-outline focus-within:border-secondary focus-within:ring-1 focus-within:ring-secondary transition-all rounded shadow-[inset_0_2px_4px_rgba(0,0,0,0.2)]"
          >
            <Terminal className="absolute left-4 text-outline-variant w-5 h-5" />
            <textarea
              id="query-input"
              ref={textareaRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              spellCheck="false"
              placeholder="ANALYZE correlation BETWEEN..."
              disabled={isLoading}
              rows={1}
              className="w-full bg-transparent border-none text-on-surface font-data-mono text-data-mono py-4 pl-12 pr-12 focus:ring-0 focus:outline-none resize-none placeholder:text-outline-variant/50"
            />
            <button
              type="submit"
              disabled={!inputValue.trim() || isLoading}
              className="absolute right-4 text-outline-variant hover:text-secondary transition-colors disabled:opacity-50 disabled:hover:text-outline-variant cursor-pointer flex items-center justify-center"
            >
              <Send className="w-5 h-5" />
            </button>
          </form>
        </div>
      </div>

    </div>
  );
}
