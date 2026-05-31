import { describe, it, expect, vi, beforeEach } from 'vitest'
import { APIError } from './api'

describe('APIError', () => {
  it('creates error with message and status', () => {
    const err = new APIError('not found', 404, { detail: 'not found' })
    expect(err.message).toBe('not found')
    expect(err.status).toBe(404)
    expect(err.data).toEqual({ detail: 'not found' })
    expect(err.name).toBe('APIError')
  })

  it('creates error without status', () => {
    const err = new APIError('generic error')
    expect(err.message).toBe('generic error')
    expect(err.status).toBeUndefined()
  })
})

describe('api client', () => {
  beforeEach(() => {
    vi.stubGlobal('useAuthStore', undefined)
  })

  it('exports default api instance', async () => {
    const api = (await import('./api')).default
    expect(api).toBeDefined()
    expect(typeof api.health).toBe('function')
    expect(typeof api.listModels).toBe('function')
    expect(typeof api.listAgents).toBe('function')
    expect(typeof api.listApiKeys).toBe('function')
    expect(typeof api.listStudioFlows).toBe('function')
  })
})
