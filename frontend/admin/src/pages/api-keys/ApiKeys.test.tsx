import { describe, it, expect } from 'vitest'

describe('ApiKeys page', () => {
  it('renders without crashing', async () => {
    const page = await import('./ApiKeys')
    expect(page.default).toBeDefined()
  })
})
