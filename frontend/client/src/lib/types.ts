export interface Agent {
  id: string;
  name: string;
  version: string;
  status: 'draft' | 'active' | 'paused' | 'deprecated';
}

export interface AgentDetail extends Agent {
  instructions: string;
  model_id: string;
  allowed_tools: string[] | null;
}

export interface Session {
  id: string;
  tenant_id: string;
  user_id: string | null;
  agent_id: string;
  title: string | null;
  status: 'active' | 'archived' | 'deleted';
  retention_policy: Record<string, unknown> | null;
  metadata: Record<string, unknown> | null;
  last_message_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SessionMessage {
  id: string;
  thread_id: string;
  session_id: string;
  run_id: string | null;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  content_hash: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface RunResponse {
  id: string;
  session_id: string | null;
  status: string;
  started_at: string;
}

export interface RunStatus {
  id: string;
  agent_id: string;
  status: string;
  total_steps: number;
  started_at: string;
  completed_at: string | null;
  failure_reason: string | null;
}

export interface ToolCall {
  name: string;
  arguments: Record<string, unknown>;
  result?: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'approval_required';
}

export interface StreamEvent {
  event_type: string;
  payload: Record<string, unknown>;
}

export interface ToolActivityItem {
  id: string;
  type: 'tool_call' | 'memory_read' | 'approval_required' | 'step' | 'status';
  name?: string;
  status: string;
  detail?: string;
  timestamp: string;
}

export interface ChatAttachment {
  file: File;
  preview?: string;
  mimeType: string;
}

export interface PortalProfile {
  id: string;
  name: string;
  billing_status: string;
  is_blocked: boolean;
  demo_mode: boolean;
  plan: {
    code: string;
    name: string;
    monthly_price: number;
    currency: string;
    rag_enabled: boolean;
    tts_enabled: boolean;
    // ... rest of plan fields
  };
}

export interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  masked_key: string;
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
  expires_at: string | null;
}

export interface Invoice {
  id: string;
  status: string;
  total_amount: number;
  currency: string;
  period_start: string;
  period_end: string;
  due_at: string | null;
  paid_at: string | null;
}

export interface Wallet {
  balance_brl: number;
  available_brl: number;
  low_balance: boolean;
  transactions: WalletTransaction[];
}

export interface WalletTransaction {
  id: string;
  type: string;
  amount_brl: number;
  balance_after_brl: number;
  created_at: string;
}

export interface RagUsage {
  rag_enabled: boolean;
  plan: string;
  usage: {
    documents_count: number;
    storage_mb: number;
    queries_month: number;
  };
  limits: {
    max_documents: number | null;
    max_storage_mb: number | null;
    max_queries_per_month: number | null;
  };
}

export interface RagDocument {
  id: string;
  original_filename: string;
  content_type: string;
  file_size_bytes: number;
  status: string;
  created_at: string;
}
