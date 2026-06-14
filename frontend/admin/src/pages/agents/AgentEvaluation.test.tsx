import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AgentEvaluation from './AgentEvaluation'
import api from '../../lib/api'

vi.mock('../../lib/api', () => ({
  default: {
    listAgentBenchmarks: vi.fn(),
    listAgentBenchmarkReports: vi.fn(),
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
  })

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
      expect(screen.getByText('llama-3')).toBeInTheDocument()
      expect(screen.getByText('85.0%')).toBeInTheDocument()
    })
  })

  it('triggers a new benchmark run', async () => {
    vi.mocked(api.listAgentBenchmarks).mockResolvedValue([])
    vi.mocked(api.listAgentBenchmarkReports).mockResolvedValue([])
    vi.mocked(api.runAgentBenchmark).mockResolvedValue({ status: 'started' })

    render(
      <QueryClientProvider client={queryClient}>
        <AgentEvaluation />
      </QueryClientProvider>
    )

    const runButton = screen.getByText('Run benchmark')
    fireEvent.click(runButton)

    await waitFor(() => {
      expect(api.runAgentBenchmark).toHaveBeenCalledWith(expect.objectContaining({
        benchmark: 'AgentBench'
      }))
    })
  })
})
