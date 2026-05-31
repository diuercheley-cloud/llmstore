import type { Agent, AgentDetail, Session, SessionMessage, RunResponse } from './types';

export function getAuthToken(): string | null {
  try {
    return localStorage.getItem('client_api_token') || import.meta.env.VITE_API_TOKEN || null;
  } catch {
    return import.meta.env.VITE_API_TOKEN || null;
  }
}

export function setAuthToken(token: string) {
  localStorage.setItem('client_api_token', token);
}

export function clearAuthToken() {
  localStorage.removeItem('client_api_token');
}

function getBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL || '';
}

function authHeaders(): Record<string, string> {
  const token = getAuthToken();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${getBaseUrl()}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: { ...authHeaders(), ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  listAgents: () => request<Agent[]>('/v1/agents'),

  getAgent: (agentId: string) => request<AgentDetail>(`/v1/agents/${agentId}`),

  createSession: (agentId: string, title?: string) =>
    request<Session>(`/v1/agents/${agentId}/sessions`, {
      method: 'POST',
      body: JSON.stringify({ title: title || null }),
    }),

  // Mobile & PWA
  registerDevice: (token: string, platform: string, model?: string, version?: string) =>
    request<{ id: string }>(`/v1/mobile/devices/register`, {
      method: 'POST',
      body: JSON.stringify({ device_token: token, platform, model, app_version: version }),
    }),

  subscribePush: (subscription: PushSubscription) => {
    const p = subscription.toJSON();
    return request<{ status: string }>(`/v1/mobile/push/subscribe`, {
      method: 'POST',
      body: JSON.stringify({
        endpoint: p.endpoint,
        p256dh: p.keys?.p256dh,
        auth: p.keys?.auth,
      }),
    });
  },

  unsubscribePush: (endpoint: string) =>
    request<{ status: string }>(`/v1/mobile/push/unsubscribe`, {
      method: 'POST',
      body: JSON.stringify({ endpoint }),
    }),

  getMobileConfig: () => request<any>(`/v1/mobile/config`),

  listSessions: (agentId?: string, limit = 50) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (agentId) params.set('agent_id', agentId);
    return request<Session[]>(`/v1/agents/sessions?${params}`);
  },

  getSession: (sessionId: string) => request<Session>(`/v1/agents/sessions/${sessionId}`),


  getMessages: (sessionId: string, limit = 200) =>
    request<SessionMessage[]>(`/v1/agents/sessions/${sessionId}/messages?limit=${limit}`),

  startRun: (agentId: string, inputText: string, sessionId?: string) =>
    request<RunResponse>(`/v1/agents/${agentId}/runs`, {
      method: 'POST',
      body: JSON.stringify({ input_text: inputText, session_id: sessionId || null }),
    }),

  startSessionRun: (sessionId: string, inputText: string) =>
    request<{ run_id: string; session_id: string; status: string }>(`/v1/agents/sessions/${sessionId}/runs`, {
      method: 'POST',
      body: JSON.stringify({ input_text: inputText }),
    }),

  deleteSession: (sessionId: string) =>
    request<{ status: string }>(`/v1/agents/sessions/${sessionId}`, {
      method: 'DELETE',
    }),

  updateSession: (sessionId: string, data: { title?: string; status?: string }) =>
    request<Session>(`/v1/agents/sessions/${sessionId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  getRunStatus: (runId: string) => request<{ status: string }>(`/v1/agents/runs/${runId}`),

  cancelRun: (runId: string) =>
    request<{ status: string }>(`/v1/agents/runs/${runId}/cancel`, { method: 'POST' }),
};

export function buildWebSocketUrl(runId: string): string {
  const token = getAuthToken();
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const base = getBaseUrl();
  let host: string;
  if (base) {
    try {
      host = new URL(base).host;
    } catch {
      host = window.location.host;
    }
  } else {
    host = window.location.host;
  }
  const params = new URLSearchParams();
  if (token) params.set('token', token);
  return `${protocol}//${host}/v1/agents/runs/${runId}/stream?${params}`;
}
