export interface Citation {
  source: string;
  date: string;
  excerpt: string;
  relevance_score: number;
}

export interface ActionItem {
  action_type: string;
  draft_content: string;
  requires_human_review: boolean;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  citations?: Citation[];
  actionItems?: ActionItem[];
  confidenceScore?: number;
  intent?: string;
  reflectionCount?: number;
  latencyMs?: number;
  isStreaming?: boolean;
}

export interface QueryResponse {
  answer: string;
  citations: Citation[];
  action_items: ActionItem[];
  confidence_score: number;
  intent: string;
  reflection_count: number;
  latency_ms: number;
  session_id: string;
}
