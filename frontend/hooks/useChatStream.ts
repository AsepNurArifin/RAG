import { useState, useCallback, useRef, useEffect } from "react";
import { ActionItem, Citation, Message, QueryResponse } from "../types";
import { api } from "../lib/api";
import { useActiveAgent, type ActiveAgentType } from "../context/ActiveAgentContext";

/**
 * Satu-satunya tempat mapping API response (live) ke Message.
 * History memakai mapper yang sama → shape pesan selalu identik.
 */
export function mapQueryResultToMessage(response: QueryResponse): Message {
  return {
    id: response.request_id || (Date.now() + 1).toString(),
    role: "assistant",
    content: response.answer,
    citations: response.citations ?? [],
    actionItems: response.action_items ?? [],
    followUpSuggestions: response.follow_up_suggestions ?? [],
    confidenceScore: response.confidence_score,
    intent: response.intent,
    intentType: response.intent_type,
    reflectionCount: response.reflection_count,
    latencyMs: response.latency_ms,
    requestId: response.request_id,
    traceId: response.trace_id ?? undefined,
    status: response.status,
  };
}

/** Shape pesan history dari API sessions (snake_case, JSONB bisa string/list). */
export interface HistoryMessageResponse {
  id?: string;
  role?: string;
  content?: string;
  citations?: unknown;
  action_items?: unknown;
  follow_up_suggestions?: unknown;
  confidence_score?: number;
  intent?: string;
  intent_type?: string;
  reflection_count?: number;
  latency_ms?: number;
  request_id?: string;
  trace_id?: string;
  status?: string;
  error_code?: string;
}

/** Mapping pesan history (snake_case dari API) ke Message — kontrak sama. */
export function mapHistoryToMessage(raw: HistoryMessageResponse): Message {
  const parseJsonArray = (v: unknown): unknown[] => {
    if (v === null || v === undefined) return [];
    if (typeof v === "string") {
      try { const p = JSON.parse(v); return Array.isArray(p) ? p : []; } catch { return []; }
    }
    return Array.isArray(v) ? (v as unknown[]) : [];
  };
  return {
    id: raw.id || `hist-${Date.now()}-${Math.random()}`,
    role: (raw.role === "assistant" || raw.role === "user" || raw.role === "system") ? raw.role : "assistant",
    content: raw.content || "",
    citations: parseJsonArray(raw.citations) as Citation[],
    actionItems: parseJsonArray(raw.action_items) as ActionItem[],
    followUpSuggestions: parseJsonArray(raw.follow_up_suggestions) as string[],
    confidenceScore: raw.confidence_score ?? undefined,
    intent: raw.intent ?? undefined,
    intentType: raw.intent_type ?? undefined,
    reflectionCount: raw.reflection_count ?? undefined,
    latencyMs: raw.latency_ms ?? undefined,
    requestId: raw.request_id ?? undefined,
    traceId: raw.trace_id ?? undefined,
    status: (raw.status === "completed" || raw.status === "degraded" || raw.status === "failed") ? raw.status : undefined,
    errorCode: raw.error_code ?? undefined,
  };
}

/**
 * Mapping eksplisit nama node backend → agent pipeline UI.
 * - "tools" adalah bagian dari tahap research (Tool Router jalan sebelum Researcher).
 * - "reflection" adalah bagian dari tahap verification (retry loop setelah Verifier).
 * Input dinormalisasi (trim + lowercase) agar variasi casing tidak jatuh ke "idle".
 */
const AGENT_ALIASES: Record<string, ActiveAgentType> = {
  orchestrator: "orchestrator",
  tools: "researcher",
  researcher: "researcher",
  verifier: "verifier",
  reflection: "verifier",
  summarizer: "summarizer",
  executor: "executor",
};

export function mapAgent(raw: string): ActiveAgentType {
  const key = (raw ?? "").trim().toLowerCase();
  return AGENT_ALIASES[key] ?? "idle";
}

export function useChatStream(initialSessionId?: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>(initialSessionId);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const abortControllerRef = useRef<AbortController | null>(null);
  // Guard race: callback dari request lama tidak boleh menimpa request baru.
  const activeRequestIdRef = useRef<string | null>(null);

  const { setActiveAgent } = useActiveAgent();

  // Cleanup abort controller on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // Auto-scroll to bottom when messages change
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Lifecycle activeAgent dikelola eksplisit di callback (onResult/onError/
  // cancelQuery/abort) — bukan via effect isLoading, agar tidak balapan
  // dengan event "agent" dari stream.

  // Load history for a given session
  const loadSessionHistory = useCallback(async (sid: string) => {
    try {
      const data = await api.getSessionMessages(sid);
      const loaded: Message[] = data.map((raw: HistoryMessageResponse) =>
        mapHistoryToMessage(raw)
      );
      setMessages(loaded);
      setSessionId(sid);
    } catch (err) {
      console.error("Failed to load session history:", err);
    }
  }, []);

  // Helper: hapus pesan by ID (bukan by array position) saat cancel.
  const removeMessageById = useCallback((id: string) => {
    setMessages((prev) => prev.filter((m) => m.id !== id));
  }, []);

  const runStream = useCallback(
    (content: string, userMessageId: string) => {
      const requestId = `req_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
      activeRequestIdRef.current = requestId;

      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      const controller = new AbortController();
      abortControllerRef.current = controller;

      api.queryStream(
        content,
        sessionId,
        (agent) => {
          if (activeRequestIdRef.current !== requestId) return;
          setActiveAgent(mapAgent(agent));
        },
        (response: QueryResponse) => {
          if (activeRequestIdRef.current !== requestId) return;
          if (!sessionId && response.session_id) {
            setSessionId(response.session_id);
          }
          const assistantMessage = mapQueryResultToMessage(response);
          setMessages((prev) => [...prev, assistantMessage]);
          setIsLoading(false);
          setActiveAgent("idle");
          activeRequestIdRef.current = null;
        },
        (error: Error) => {
          if (activeRequestIdRef.current !== requestId) return;
          if (error.name === "AbortError") {
            console.log("Stream query cancelled.");
            removeMessageById(userMessageId);
            setIsLoading(false);
            setActiveAgent("idle");
            return;
          }
          console.error("Error sending message:", error);
          setActiveAgent("idle");
          const errorMessage: Message = {
            id: `err_${Date.now()}`,
            role: "system",
            content: error.message || "Terjadi kesalahan sistem. Silakan coba lagi.",
          };
          setMessages((prev) => [...prev, errorMessage]);
          setIsLoading(false);
          activeRequestIdRef.current = null;
        },
        controller.signal
      );
    },
    [sessionId, setActiveAgent, removeMessageById]
  );

  const sendMessage = useCallback(
    (content: string) => {
      if (!content.trim() || isLoading) return;
      const userMessage: Message = {
        id: `usr_${Date.now()}`,
        role: "user",
        content,
      };
      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);
      setActiveAgent("orchestrator");
      runStream(content, userMessage.id);
    },
    [isLoading, setActiveAgent, runStream]
  );

  // Cancel an in-flight query
  const cancelQuery = useCallback(() => {
    activeRequestIdRef.current = null;
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsLoading(false);
    setActiveAgent("idle");
  }, [setActiveAgent]);

  // Edit a user message and resend (Claude-like: remove all messages after the edited one)
  const editAndResend = useCallback(
    (messageId: string, newContent: string) => {
      if (!newContent.trim() || isLoading) return;

      const messageIndex = messages.findIndex((m) => m.id === messageId);
      if (messageIndex === -1 || messages[messageIndex].role !== "user") return;

      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
      activeRequestIdRef.current = null;

      const updatedMessages = [
        ...messages.slice(0, messageIndex),
        { ...messages[messageIndex], content: newContent },
      ];

      setMessages(updatedMessages);
      setIsLoading(true);
      setActiveAgent("orchestrator");
      runStream(newContent, messages[messageIndex].id);
    },
    [messages, isLoading, setActiveAgent, runStream]
  );

  const clearChat = useCallback(() => {
    setMessages([]);
    setSessionId(undefined);
  }, []);

  return {
    messages,
    isLoading,
    sendMessage,
    cancelQuery,
    editAndResend,
    clearChat,
    messagesEndRef,
    sessionId,
    setSessionId,
    loadSessionHistory,
  };
}
