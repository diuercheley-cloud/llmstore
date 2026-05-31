import { describe, it, expect } from 'vitest'

describe('Rag page', () => {
  it('renders without crashing', async () => {
    const page = await import('./Rag')
    expect(page.default).toBeDefined()
  })
})
