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

export interface Document {
  id: string;
  filename: string;
  file_type: string;
  category: string;
  status: string;
  file_size_bytes: number;
  chunk_count: number;
  created_at: string;
  updated_at: string;
}

export interface Session {
  id: string;
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Metrics {
  total_queries: number;
  avg_latency_ms: number;
  avg_confidence_score: number;
  total_estimated_cost_usd: number;
  intent_distribution: Record<string, number>;
  recent_logs: QueryLog[];
  total_documents: number;
}

export interface QueryLog {
  id: string;
  query: string;
  intent: string;
  agents_activated: string[];
  latency_ms: number;
  confidence_score: number;
  reflection_count: number;
  model_used: string;
  estimated_cost_usd: number;
  created_at: string;
}

export interface UserData {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface UploadResponse {
  workflow_id: string;
  filename: string;
  status: string;
  message: string;
}

export interface WorkflowStatusResponse {
  workflow_id: string;
  status: string;
  workflow_status: string;
  started_at: string | null;
  closed_at: string | null;
  error: string | null;
  document_id?: string;
  chunk_count?: number;
}
