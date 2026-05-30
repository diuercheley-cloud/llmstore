import React from 'react';
import { createRoot } from 'react-dom/client';
import { expect, test, describe, vi } from 'vitest';
import DebuggerPanel from './DebuggerPanel';

// Mock the useAgentRunStream hook to simulate connection states and event list updates
vi.mock('../../../hooks/useAgentRunStream', () => {
  return {
    useAgentRunStream: (runId?: string) => {
      if (!runId) {
        return {
          status: 'failed',
          events: [],
          error: null,
          sendCommand: vi.fn(),
          clearLogs: vi.fn(),
        };
      }
      if (runId === 'error-run') {
        return {
          status: 'failed',
          events: [],
          error: 'Connection refused',
          sendCommand: vi.fn(),
          clearLogs: vi.fn(),
        };
      }
      return {
        status: 'connected',
        events: [
          {
            event: 'run.started',
            run_id: runId,
            timestamp: new Date().toISOString(),
            data: {},
          },
          {
            event: 'model.delta',
            run_id: runId,
            timestamp: new Date().toISOString(),
            data: { chunk: 'Thinking ' },
          },
          {
            event: 'model.delta',
            run_id: runId,
            timestamp: new Date().toISOString(),
            data: { chunk: 'process.' },
          },
          {
            event: 'tool.called',
            run_id: runId,
            timestamp: new Date().toISOString(),
            data: { tool_name: 'test_tool', parameters: { x: 1 } },
          },
        ],
        error: null,
        sendCommand: vi.fn(),
        clearLogs: vi.fn(),
      };
    },
  };
});

describe('DebuggerPanel Frontend Component', () => {
  test('sem runId mostra empty state', async () => {
    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = createRoot(container);
    root.render(<DebuggerPanel />);

    await new Promise((resolve) => setTimeout(resolve, 100));

    expect(container.querySelector('#debugger-panel-empty')).not.toBeNull();
    expect(container.textContent).toContain('No active debug run');
    
    root.unmount();
    document.body.removeChild(container);
  });

  test('renderiza eventos reais mockados', async () => {
    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = createRoot(container);
    root.render(<DebuggerPanel runId="valid-run-uuid" />);

    await new Promise((resolve) => setTimeout(resolve, 100));

    expect(container.querySelector('#debugger-panel-active')).not.toBeNull();
    expect(container.textContent).toContain('Run started');
    expect(container.textContent).toContain('Thinking process.');
    expect(container.textContent).toContain('Invoking test_tool');

    root.unmount();
    document.body.removeChild(container);
  });

  test('erro WebSocket mostra warning', async () => {
    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = createRoot(container);
    root.render(<DebuggerPanel runId="error-run" />);

    await new Promise((resolve) => setTimeout(resolve, 100));

    expect(container.querySelector('#debugger-panel-warning')).not.toBeNull();
    expect(container.textContent).toContain('Warning: WebSocket connection error - Connection refused');

    root.unmount();
    document.body.removeChild(container);
  });
});
