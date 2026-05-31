import { describe, expect, it } from 'vitest'

describe('Admin app shell', () => {
  it('loads the routed admin application', async () => {
    const app = await import('./App')
    expect(app.default).toBeDefined()
  })
})
