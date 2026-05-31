import axios, { AxiosError } from 'axios'
import type { AxiosInstance } from 'axios'
import { useAuthStore } from '../store/useAuthStore'

export class APIError extends Error {
  status?: number
  data?: unknown

  constructor(message: string, status?: number, data?: unknown) {
    super(message)
    this.name = 'APIError'
    this.status = status
    this.data = data
  }
}

class APIClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({ baseURL: '/' })
    this.client.interceptors.request.use((config) => {
      const token = useAuthStore.getState().token
      if (token) config.headers['X-Admin-Token'] = token
      return config
    })
    this.client.interceptors.response.use(
      (res) => res,
      (err: AxiosError) => {
        const apiErr = new APIError(
          (err.response?.data as any)?.detail || err.message,
          err.response?.status,
          err.response?.data,
        )
        if (err.response?.status === 401) useAuthStore.getState().logout()
        return Promise.reject(apiErr)
      },
    )
  }

  private async request<T = any>(method: string, path: string, data?: unknown): Promise<T> {
    const res = await this.client.request<T>({ method, url: path, data })
    return res.data
  }

  get<T = any>(path: string, config?: Record<string, unknown>) {
    return this.client.get<T>(path, config)
  }

  post<T = any>(path: string, data?: unknown, config?: Record<string, unknown>) {
    return this.client.post<T>(path, data, config)
  }

  put<T = any>(path: string, data?: unknown, config?: Record<string, unknown>) {
    return this.client.put<T>(path, data, config)
  }

  patch<T = any>(path: string, data?: unknown, config?: Record<string, unknown>) {
    return this.client.patch<T>(path, data, config)
  }

  delete<T = any>(path: string, config?: Record<string, unknown>) {
    return this.client.delete<T>(path, config)
  }

  // System
  health = () => this.request<{ status: string }>('GET', '/health')
  ready = () => this.request<{ ready: boolean }>('GET', '/ready')
  status = () => this.request<any>('GET', '/status')

  // Admin - Models
  listModels = () => this.request<any[]>('GET', '/admin/models')
  createModel = (m: any) => this.request<any>('POST', '/admin/models', m)
  updateModel = (id: string, m: any) => this.request<any>('PATCH', `/admin/models/${id}`, m)
  deleteModel = (id: string) => this.request<void>('DELETE', `/admin/models/${id}`)

  // Admin - Backends
  listBackends = () => this.request<any[]>('GET', '/admin/backends')
  createBackend = (b: any) => this.request<any>('POST', '/admin/backends', b)
  testConnection = (b: any) => this.request<any>('POST', '/admin/backends/test-connection', b)

  // Admin - Clients
  listClients = () => this.request<any[]>('GET', '/admin/clients')
  createClient = (c: any) => this.request<any>('POST', '/admin/clients', c)
  blockClient = (id: string) => this.request<any>('POST', `/admin/clients/${id}/block`)
  unblockClient = (id: string) => this.request<any>('POST', `/admin/clients/${id}/unblock`)

  // Admin - API Keys
  listApiKeys = () => this.request<any[]>('GET', '/admin/api-keys')
  createApiKey = (k: any) => this.request<any>('POST', '/admin/api-keys', k)
  rotateApiKey = (id: string) => this.request<any>('POST', `/admin/api-keys/${id}/rotate`)
  deleteApiKey = (id: string) => this.request<void>('DELETE', `/admin/api-keys/${id}`)

  // Admin - Usage & Billing
  getUsageSummary = () => this.request<any>('GET', '/admin/usage/summary')
  getRevenueSummary = () => this.request<any>('GET', '/admin/revenue/summary')
  listInvoices = () => this.request<any[]>('GET', '/admin/billing/invoices')
  listPayments = () => this.request<any[]>('GET', '/admin/billing/payments')

  // Admin - RBAC
  listRbacUsers = () => this.request<any[]>('GET', '/admin/rbac/users')
  createRbacUser = (u: any) => this.request<any>('POST', '/admin/rbac/users', u)
  listRbacRoles = () => this.request<any[]>('GET', '/admin/rbac/roles')
  createRbacRole = (r: any) => this.request<any>('POST', '/admin/rbac/roles', r)

  // Admin - Security
  listSecurityEvents = () => this.request<any[]>('GET', '/admin/security/events')

  // RAG
  getRagUsage = () => this.request<any>('GET', '/admin/rag/usage')
  listRagCollections = () => this.request<any[]>('GET', '/v1/rag/collections')
  createRagCollection = (c: any) => this.request<any>('POST', '/v1/rag/collections', c)

  // Agents
  listAgents = () => this.request<any[]>('GET', '/v1/agents')
  getAgent = (id: string) => this.request<any>('GET', `/v1/agents/${id}`)
  createAgent = (a: any) => this.request<any>('POST', '/v1/agents', a)
  getAgentRuns = (id: string) => this.request<any[]>('GET', `/v1/agents/${id}/runs`)

  // Agent Analytics
  getAnalyticsOverview = () => this.request<any>('GET', '/api/v1/admin/agents/analytics/overview')
  getAgentAnalytics = (id: string) => this.request<any>('GET', `/api/v1/admin/agents/analytics/${id}`)

  // Studio
  listStudioFlows = () => this.request<any[]>('GET', '/admin/agents/studio/flows')
  createStudioFlow = (f: any) => this.request<any>('POST', '/admin/agents/studio/flows', f)

  // Prompts
  listPrompts = () => this.request<any[]>('GET', '/admin/prompts')
  getPrompt = (id: string) => this.request<any>('GET', `/admin/prompts/${id}`)
  createPrompt = (p: any) => this.request<any>('POST', '/admin/prompts', p)
  updatePrompt = (id: string, p: any) => this.request<any>('PATCH', `/admin/prompts/${id}`, p)

  // Portal
  listPlans = () => this.request<any[]>('GET', '/portal/plans')
  getProfile = () => this.request<any>('GET', '/portal/me')
  getUsageStats = () => this.request<any>('GET', '/portal/usage-stats')
}

const api = new APIClient()
export default api
