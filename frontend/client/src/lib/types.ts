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
