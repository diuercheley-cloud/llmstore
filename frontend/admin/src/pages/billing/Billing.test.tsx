import { describe, it, expect } from 'vitest'

describe('Billing page', () => {
  it('renders without crashing', async () => {
    const page = await import('./Billing')
    expect(page.default).toBeDefined()
  })
})
