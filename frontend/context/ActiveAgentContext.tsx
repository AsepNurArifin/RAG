"use client";

import React, { createContext, useContext, useState } from "react";

export type ActiveAgentType = "idle" | "orchestrator" | "researcher" | "verifier" | "summarizer" | "executor";

interface ActiveAgentContextType {
  activeAgent: ActiveAgentType;
  setActiveAgent: (agent: ActiveAgentType) => void;
}

const ActiveAgentContext = createContext<ActiveAgentContextType | undefined>(undefined);

export function ActiveAgentProvider({ children }: { children: React.ReactNode }) {
  const [activeAgent, setActiveAgent] = useState<ActiveAgentType>("idle");

  return (
    <ActiveAgentContext.Provider value={{ activeAgent, setActiveAgent }}>
      {children}
    </ActiveAgentContext.Provider>
  );
}

export function useActiveAgent() {
  const context = useContext(ActiveAgentContext);
  if (!context) {
    throw new Error("useActiveAgent must be used within an ActiveAgentProvider");
  }
  return context;
}
