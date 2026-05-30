import { useEffect, useState, useRef, useCallback } from 'react';
import { useAuthStore } from '../store/useAuthStore';

export type StreamStatus = 'connecting' | 'connected' | 'reconnecting' | 'failed';

export interface StreamEvent {
  event: string;
  run_id: string;
  timestamp: string;
  data: any;
}

export function useAgentRunStream(runId?: string) {
  const [status, setStatus] = useState<StreamStatus>('connecting');
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const retryCountRef = useRef(0);
  const maxRetries = 5;

  const token = useAuthStore((state) => state.token);

  const connect = useCallback(() => {
    if (!runId || !token) {
      setStatus('failed');
      setError('Missing runId or auth token');
      return;
    }

    if (socketRef.current) {
      socketRef.current.close();
    }

    const isDev = window.location.port === '5173' || window.location.port === '5174';
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = isDev ? 'localhost:8080' : window.location.host;
    const url = `${protocol}//${host}/v1/agents/runs/${runId}/stream?token=${encodeURIComponent(token)}`;

    setStatus(retryCountRef.current > 0 ? 'reconnecting' : 'connecting');
    setError(null);

    const ws = new WebSocket(url);
    socketRef.current = ws;

    ws.onopen = () => {
      setStatus('connected');
      retryCountRef.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        if (parsed.event) {
          setEvents((prev) => [...prev, parsed]);
        }
      } catch (err) {
        console.error('Error parsing WS message:', err);
      }
    };

    ws.onerror = (evt) => {
      console.error('WebSocket error:', evt);
      setError('WebSocket connection error');
    };

    ws.onclose = (evt) => {
      socketRef.current = null;
      
      if (evt.code === 1000) {
        setStatus('failed');
        return;
      }

      if (retryCountRef.current < maxRetries) {
        setStatus('reconnecting');
        const delay = Math.min(1000 * Math.pow(2, retryCountRef.current), 10000);
        retryCountRef.current += 1;
        reconnectTimeoutRef.current = window.setTimeout(() => {
          connect();
        }, delay);
      } else {
        setStatus('failed');
        setError('Connection failed after maximum retry attempts.');
      }
    };
  }, [runId, token]);

  useEffect(() => {
    if (!runId) {
      setStatus('failed');
      setEvents([]);
      setError(null);
      return;
    }

    retryCountRef.current = 0;
    setEvents([]);
    connect();

    return () => {
      if (socketRef.current) {
        socketRef.current.close(1000, 'Component unmounted');
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [runId, connect]);

  const sendCommand = useCallback((command: 'cancel' | 'pause' | 'resume') => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ command }));
    } else {
      console.warn('Cannot send command: WebSocket is not open.');
    }
  }, []);

  const clearLogs = useCallback(() => {
    setEvents([]);
  }, []);

  return {
    status,
    events,
    error,
    sendCommand,
    clearLogs,
  };
}
export default useAgentRunStream;
