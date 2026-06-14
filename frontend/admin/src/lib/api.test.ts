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
    vi.stubGlobal('useAuthStore', {
      getState: () => ({ token: 'test-token', logout: vi.fn() })
    })
    vi.clearAllMocks()
  })

  it('exports default api instance', async () => {
    const api = (await import('./api')).default
    expect(api).toBeDefined()
    expect(typeof api.health).toBe('function')
  })

  it('sends GET request without params', async () => {
    const api = (await import('./api')).default
    const spy = vi.spyOn((api as any).client, 'request').mockResolvedValue({ data: { status: 'ok' } })
    
    await api.health()
    
    expect(spy).toHaveBeenCalledWith(expect.objectContaining({
      method: 'GET',
      url: '/health'
    }))
    expect((spy.mock.calls[0][0] as any).params).toBeUndefined()
  })

  it('sends GET request with params', async () => {
    const api = (await import('./api')).default
    const spy = vi.spyOn((api as any).client, 'request').mockResolvedValue({ data: [] })
    
    await api.getCostsSummary({ period: 'last_7_days' })
    
    const call = spy.mock.calls[0][0] as any
    expect(call.method).toBe('GET')
    expect(call.url).toBe('/api/admin/costs/summary')
    expect(call.params).toBeInstanceOf(URLSearchParams)
    expect((call.params as URLSearchParams).get('period')).toBe('last_7_days')
  })

  it('sends POST request with body', async () => {
    const api = (await import('./api')).default
    const spy = vi.spyOn((api as any).client, 'request').mockResolvedValue({ data: {} })
    
    await api.createModel({ name: 'test-model' })
    
    expect(spy).toHaveBeenCalledWith(expect.objectContaining({
      method: 'POST',
      url: '/admin/models',
      data: { name: 'test-model' }
    }))
  })

  it('handles API error correctly', async () => {
    const api = (await import('./api')).default
    vi.spyOn((api as any).client, 'request').mockRejectedValue(new APIError('Bad Request', 400))
    
    await expect(api.health()).rejects.toThrow('Bad Request')
  })
})
