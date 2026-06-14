import React from 'react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, fireEvent, cleanup } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AgentEvaluation from './AgentEvaluation'
import api from '../../lib/api'

vi.mock('../../lib/api', () => ({
  default: {
    listAgentBenchmarks: vi.fn(),
    listAgentBenchmarkReports: vi.fn(),
    listAdminAgents: vi.fn(),
    getAgentEvalReportAdmin: vi.fn(),
    runAgentBenchmark: vi.fn(),
    exportAgentBenchmarkReport: vi.fn(),
  }
}))

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
})

describe('AgentEvaluation Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.listAdminAgents).mockResolvedValue([{ id: 'agent-1', name: 'Agent One' }])
    vi.mocked(api.getAgentEvalReportAdmin).mockResolvedValue({})
  })

  afterEach(() => cleanup())

  it('renders benchmark list and reports', async () => {
    vi.mocked(api.listAgentBenchmarks).mockResolvedValue([
      { name: 'AgentBench', tasks: 10, supports: { vision: true } }
    ])
    vi.mocked(api.listAgentBenchmarkReports).mockResolvedValue([
      { run_id: 'run-1', benchmark: 'AgentBench', model_name: 'llama-3', metrics: { success_rate: 0.85 } }
    ])

    render(
      <QueryClientProvider client={queryClient}>
        <AgentEvaluation />
      </QueryClientProvider>
    )

    await waitFor(() => {
      expect(screen.getByText('AgentBench')).toBeInTheDocument()
      expect(document.body.textContent).toContain('llama-3')
      expect(document.body.textContent).toContain('0.85')
    })
  })

  it('triggers a new benchmark run', async () => {
    vi.mocked(api.listAgentBenchmarks).mockResolvedValue([{ name: 'AgentBench' }])
    vi.mocked(api.listAgentBenchmarkReports).mockResolvedValue([])
    vi.mocked(api.runAgentBenchmark).mockResolvedValue({ status: 'started' })

    render(
      <QueryClientProvider client={queryClient}>
        <AgentEvaluation />
      </QueryClientProvider>
    )

    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'agent-1' } })
    const runButton = await screen.findByText('AgentBench')
    fireEvent.click(runButton)

    await waitFor(() => {
      expect(api.runAgentBenchmark).toHaveBeenCalledWith(expect.objectContaining({
        agent_id: 'agent-1',
        model_name: 'llama-3-70b',
        benchmark: 'AgentBench',
      }))
    })
  })
})
