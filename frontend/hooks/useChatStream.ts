import { useState, useCallback, useRef, useEffect } from "react";
import { Message, QueryResponse } from "../types";
import { api } from "../lib/api";
import { useActiveAgent } from "../context/ActiveAgentContext";

export function useChatStream(initialSessionId?: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>(initialSessionId);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { setActiveAgent } = useActiveAgent();

  // Auto-scroll to bottom when messages change
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Agent cycling simulation while querying
  useEffect(() => {
    if (!isLoading) {
      setActiveAgent("idle");
      return;
    }

    setActiveAgent("orchestrator");
    const t1 = setTimeout(() => setActiveAgent("researcher"), 1000);
    const t2 = setTimeout(() => setActiveAgent("verifier"), 3000);
    const t3 = setTimeout(() => setActiveAgent("summarizer"), 5500);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
    };
  }, [isLoading, setActiveAgent]);

  // Load history for a given session
  const loadSessionHistory = useCallback(async (sid: string) => {
    try {
      const data = await api.getSessionMessages(sid);
      const loaded: Message[] = data.map((msg: any, i: number) => ({
        id: msg.id || `hist-${i}`,
        role: msg.role,
        content: msg.content,
        citations: msg.citations || [],
        actionItems: msg.action_items || [],
        confidenceScore: msg.confidence_score,
        latencyMs: msg.latency_ms,
      }));
      setMessages(loaded);
      setSessionId(sid);
    } catch (err) {
      console.error("Failed to load session history:", err);
    }
  }, []);

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return;

    // Add user message to UI immediately
    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content,
    };
    
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      // Call backend API
      const response: QueryResponse = await api.query(content, sessionId);
      
      // Update session ID if this is the first interaction
      if (!sessionId && response.session_id) {
        setSessionId(response.session_id);
      }

      // Add assistant response to UI
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response.answer,
        citations: response.citations,
        actionItems: response.action_items,
        confidenceScore: response.confidence_score,
        intent: response.intent,
        reflectionCount: response.reflection_count,
        latencyMs: response.latency_ms,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error("Error sending message:", error);
      
      // Add error message to UI
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "system",
        content: error instanceof Error ? error.message : "Terjadi kesalahan sistem. Silakan coba lagi.",
      };
      
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, isLoading]);

  const clearChat = useCallback(() => {
    setMessages([]);
    setSessionId(undefined);
  }, []);

  return {
    messages,
    isLoading,
    sendMessage,
    clearChat,
    messagesEndRef,
    sessionId,
    setSessionId,
    loadSessionHistory,
  };
}
