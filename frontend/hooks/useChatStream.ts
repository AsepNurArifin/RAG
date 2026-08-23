import { useState, useCallback, useRef, useEffect } from "react";
import { Message, QueryResponse } from "../types";
import { api } from "../lib/api";
import { useActiveAgent } from "../context/ActiveAgentContext";

export function useChatStream(initialSessionId?: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>(initialSessionId);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const abortControllerRef = useRef<AbortController | null>(null);

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

  // Agent cycling simulation while querying (REMOVED)
  useEffect(() => {
    if (!isLoading) {
      setActiveAgent("idle");
    }
  }, [isLoading, setActiveAgent]);

  // Load history for a given session
  const loadSessionHistory = useCallback(async (sid: string) => {
    try {
      const data = await api.getSessionMessages(sid);
      const loaded: Message[] = data.map((raw: Record<string, any>, i: number) => {
        let parsedCitations = raw.citations || [];
        let parsedActionItems = raw.action_items || [];
        
        if (typeof parsedCitations === 'string') {
          try { parsedCitations = JSON.parse(parsedCitations); } catch(e) { parsedCitations = []; }
        }
        if (typeof parsedActionItems === 'string') {
          try { parsedActionItems = JSON.parse(parsedActionItems); } catch(e) { parsedActionItems = []; }
        }

        return {
          id: raw.id || `hist-${i}`,
          role: raw.role,
          content: raw.content,
          citations: parsedCitations,
          actionItems: parsedActionItems,
          confidenceScore: raw.confidence_score,
          latencyMs: raw.latency_ms,
        };
      });
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
    setActiveAgent("orchestrator");

    // Cancel previous request if still running
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    api.queryStream(
      content,
      sessionId,
      (agent) => {
        // Map LangGraph node names to our UI active agent states
        if (agent.includes("orchestrator")) setActiveAgent("orchestrator");
        else if (agent.includes("researcher")) setActiveAgent("researcher");
        else if (agent.includes("verifier")) setActiveAgent("verifier");
        else if (agent.includes("summarizer")) setActiveAgent("summarizer");
        else if (agent.includes("executor")) setActiveAgent("executor");
      },
      (response: QueryResponse) => {
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
        setIsLoading(false);
      },
      (error: Error) => {
        if (error.name === "AbortError") {
          console.log("Stream query cancelled.");
          // Remove the user message that triggered this cancelled query
          setMessages((prev) => prev.slice(0, -1));
          setIsLoading(false);
          setActiveAgent("idle");
          return;
        }
        console.error("Error sending message:", error);
        
        // Add error message to UI
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: "system",
          content: error.message || "Terjadi kesalahan sistem. Silakan coba lagi.",
        };
        
        setMessages((prev) => [...prev, errorMessage]);
        setIsLoading(false);
      },
      controller.signal
    );
  }, [sessionId, isLoading, setActiveAgent]);

  // Cancel an in-flight query
  const cancelQuery = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsLoading(false);
    setActiveAgent("idle");
  }, [setActiveAgent]);

  // Edit a user message and resend (Claude-like: remove all messages after the edited one)
  const editAndResend = useCallback(async (messageId: string, newContent: string) => {
    if (!newContent.trim() || isLoading) return;

    // Find the message index
    const messageIndex = messages.findIndex(m => m.id === messageId);
    if (messageIndex === -1 || messages[messageIndex].role !== "user") return;

    // Cancel any in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    // Keep messages up to (and including) the edited message, update its content
    const updatedMessages = [
      ...messages.slice(0, messageIndex),
      { ...messages[messageIndex], content: newContent },
    ];

    setMessages(updatedMessages);
    setIsLoading(true);
    setActiveAgent("orchestrator");

    const controller = new AbortController();
    abortControllerRef.current = controller;

    api.queryStream(
      newContent,
      sessionId,
      (agent) => {
        if (agent.includes("orchestrator")) setActiveAgent("orchestrator");
        else if (agent.includes("researcher")) setActiveAgent("researcher");
        else if (agent.includes("verifier")) setActiveAgent("verifier");
        else if (agent.includes("summarizer")) setActiveAgent("summarizer");
        else if (agent.includes("executor")) setActiveAgent("executor");
      },
      (response: QueryResponse) => {
        if (!sessionId && response.session_id) {
          setSessionId(response.session_id);
        }

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
        setIsLoading(false);
      },
      (error: Error) => {
        if (error.name === "AbortError") {
          console.log("Edit-and-resend cancelled.");
          setIsLoading(false);
          setActiveAgent("idle");
          return;
        }
        console.error("Error in editAndResend:", error);
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: "system",
          content: error.message || "Terjadi kesalahan sistem. Silakan coba lagi.",
        };
        setMessages((prev) => [...prev, errorMessage]);
        setIsLoading(false);
        setActiveAgent("idle");
      },
      controller.signal
    );
  }, [messages, sessionId, isLoading, setActiveAgent]);

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
