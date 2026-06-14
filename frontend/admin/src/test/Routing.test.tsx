import { describe, it, expect } from 'vitest'

describe('Admin Pages exist', () => {
  it('Agent Registry page exists', async () => {
    const page = await import('../pages/agents/AgentRegistry')
    expect(page.default).toBeDefined()
  })

  it('Agent Workspaces page exists', async () => {
    const page = await import('../pages/agents/AgentWorkspaces')
    expect(page.default).toBeDefined()
  })

  it('Runtime Nodes page exists', async () => {
    const page = await import('../pages/operations/RuntimeNodes')
    expect(page.default).toBeDefined()
  })
})
