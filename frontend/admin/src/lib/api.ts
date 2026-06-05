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

  // Agent Promotion & Environments
  getAgentEnvironments = (agentId: string) => this.request<any>('GET', `/admin/agents/${agentId}/environments`)
  getAgentLineage = (agentId: string) => this.request<any>('GET', `/admin/agent-registry/${agentId}/lineage`)
  promoteAgent = (agentId: string, data: { from_environment: string, to_environment: string, version_id: string, approve?: boolean }) => 
    this.request<any>('POST', `/admin/agents/${agentId}/promote`, data)
  rollbackAgent = (agentId: string, environment: string) => 
    this.request<any>('POST', `/admin/agents/${agentId}/rollback?environment=${environment}`)

  // Collaborative Chat
  listChatChannels = () => this.request<any[]>('GET', '/v1/chat/channels')
  createChatChannel = (c: any) => this.request<any>('POST', '/v1/chat/channels', c)
  listChatMessages = (channelId: string) => this.request<any[]>('GET', `/v1/chat/channels/${channelId}/messages`)
  postChatMessage = (channelId: string, content: string) => this.request<any>('POST', `/v1/chat/channels/${channelId}/messages`, { content })

  // Model Lifecycle & Supply Chain
  listModelLifecycle = () => this.request<{items: any[]}>('GET', '/admin/models/lifecycle')
  getModelLifecycle = (id: string) => this.request<any>('GET', `/admin/models/lifecycle/${id}`)
  transitionModelLifecycle = (id: string, state: string) => this.request<any>('POST', `/admin/models/lifecycle/${id}/transition`, { target_state: state })
  quarantineModelLifecycle = (id: string, reason: string) => this.request<any>('POST', `/admin/models/lifecycle/${id}/quarantine`, { reason })
  verifyModelChecksum = (id: string) => this.request<any>('POST', `/admin/models/lifecycle/${id}/verify`)

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
  deleteClient = (id: string) => this.request<void>('DELETE', `/admin/clients/${id}`)
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
  getCostsSummary = (params?: any) => this.request<any>('GET', '/api/admin/costs/summary', { params })
  getCostsByAgent = (params?: any) => this.request<any[]>('GET', '/api/admin/costs/by-agent', { params })
  getCostsByTool = (params?: any) => this.request<any[]>('GET', '/api/admin/costs/by-tool', { params })
  getCostsByTenant = () => this.request<any[]>('GET', '/api/admin/costs/by-tenant')
  exportCosts = (params: any) => this.request<any>('GET', '/api/admin/costs/export', { params, responseType: 'blob' })
  listInvoices = () => this.request<any[]>('GET', '/admin/billing/invoices')
  
  // Admin - Performance V2
  getPerformanceCapabilities = () => this.request<string[]>('GET', '/api/admin/performance/capabilities')
  listBackendPerformance = () => this.request<any[]>('GET', '/api/admin/performance/backends')
  getPerformanceRecommendations = () => this.request<any[]>('GET', '/api/admin/performance/recommendations')
  simulatePerformance = (payload: any) => this.request<any>('POST', '/api/admin/performance/simulate', { data: payload })

  listPayments = () => this.request<any[]>('GET', '/admin/billing/payments')

  // Admin - Enterprise Onboarding
  listEnterpriseProjects = () => this.request<any[]>('GET', '/admin/enterprise/onboarding/projects')
  createEnterpriseProject = (payload: any) => this.request<any>('POST', '/admin/enterprise/onboarding/projects', payload)

  // Admin - Agents
  listAgentRegistry = () => this.request<any[]>('GET', '/admin/agent-registry')
  listMarketplace = () => this.request<any[]>('GET', '/admin/agent-marketplace')
  getAnalyticsOverview = (days: number = 7) => this.request<any>('GET', `/api/v1/admin/agents/analytics/overview?days=${days}`)

  // Admin - RBAC
  listRbacUsers = () => this.request<any[]>('GET', '/admin/rbac/users')
  createRbacUser = (u: any) => this.request<any>('POST', '/admin/rbac/users', u)
  listRbacRoles = () => this.request<any[]>('GET', '/admin/rbac/roles')
  createRbacRole = (r: any) => this.request<any>('POST', '/admin/rbac/roles', r)
  listRbacPermissions = () => this.request<any[]>('GET', '/admin/rbac/permissions')
  listRbacAudit = (limit: number = 100) => this.request<any[]>('GET', `/admin/rbac/audit?limit=${limit}`)

  // Admin - Security & Abuse
  listSecurityEvents = () => this.request<any[]>('GET', '/admin/security/events')
  listAbuseEvents = (limit: number = 200) => this.request<any[]>('GET', `/admin/security/abuse/events?limit=${limit}`)
  getAbuseSummary = () => this.request<any>('GET', '/admin/security/abuse/summary')
  ackAbuseAction = (id: string) => this.request<any>('POST', `/admin/security/abuse/actions/${id}/ack`)
  suspendClient = (id: string, reason: string) => this.request<any>('POST', `/admin/security/abuse/clients/${id}/suspend?reason=${encodeURIComponent(reason)}`)
  unsuspendClient = (id: string, reason: string) => this.request<any>('POST', `/admin/security/abuse/clients/${id}/unsuspend?reason=${encodeURIComponent(reason)}`)

  // Admin - Billing Reconciliation
  getReconciliationOverview = () => this.request<any>('GET', '/admin/billing/reconciliation/overview')
  runReconciliation = (hours: number = 24) => this.request<any>('POST', '/admin/billing/reconciliation/run', { hours })
  listReconciliationMismatches = (limit: number = 100) => this.request<any[]>('GET', `/admin/billing/reconciliation/mismatches?limit=${limit}`)
  listBillingDisputes = (status?: string) => this.request<any[]>('GET', `/admin/billing/disputes${status ? `?status=${status}` : ''}`)
  resolveDispute = (id: string, data: any) => this.request<any>('POST', `/admin/billing/disputes/${id}/resolve`, data)

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
  getAgentAnalytics = (id: string) => this.request<any>('GET', `/api/v1/admin/agents/analytics/${id}`)

  // Studio
  listStudioFlows = () => this.request<any[]>('GET', '/admin/agents/studio/flows')
  createStudioFlow = (f: any) => this.request<any>('POST', '/admin/agents/studio/flows', f)

  // MCP
  listMcpServers = () => this.request<any[]>('GET', '/admin/agents/mcp/servers')
  registerMcpServer = (s: any) => this.request<any>('POST', '/admin/agents/mcp/servers', s)
  discoverMcpTools = (id: string) => this.request<any>('POST', `/admin/agents/mcp/servers/${id}/discover`)
  approveMcpTool = (id: string, tool: string) => this.request<any>('POST', `/admin/agents/mcp/servers/${id}/approve-tool`, { tool_name: tool })
  listMcpTools = () => this.request<any[]>('GET', '/admin/agents/mcp/tools')
  listMcpAudit = () => this.request<any[]>('GET', '/admin/agents/mcp/audit')

  // Agent Approvals
  listPendingApprovals = () => this.request<{items: any[]}>('GET', '/admin/agents/approval-portal/pending')
  decideApproval = (id: string, decision: string, reason?: string) => this.request<any>('POST', `/admin/agents/approval-portal/approvals/${id}/decide`, { decision, reason })

  // Agent Deployments
  listDeployments = () => this.request<any[]>('GET', '/admin/agents/deployments')
  rollbackDeployment = (id: string) => this.request<any>('POST', `/admin/agents/deployments/${id}/rollback`)
  promoteDeployment = (id: string) => this.request<any>('POST', `/admin/agents/deployments/${id}/promote`)
  pauseDeployment = (id: string) => this.request<any>('POST', `/admin/agents/deployments/${id}/pause`)
  resumeDeployment = (id: string) => this.request<any>('POST', `/admin/agents/deployments/${id}/resume`)
  archiveDeployment = (id: string) => this.request<any>('POST', `/admin/agents/deployments/${id}/archive`)

  // Agent Optimization & Tournaments
  listTournaments = () => this.request<any[]>('GET', '/admin/agents/optimization/tournaments')
  getTournament = (id: string) => this.request<any>('GET', `/admin/agents/optimization/tournaments/${id}`)
  createTournament = (agentId: string, candidateIds: string[]) => this.request<any>('POST', `/admin/agents/${agentId}/optimization/tournaments`, { candidate_ids: candidateIds })
  runTournament = (id: string) => this.request<any>('POST', `/admin/agents/optimization/tournaments/${id}/run`)
  approveWinner = (id: string) => this.request<any>('POST', `/admin/agents/optimization/tournaments/${id}/approve-winner`)
  applyWinner = (id: string) => this.request<any>('POST', `/admin/agents/optimization/tournaments/${id}/apply-winner`)

  listFederationPeers = () => this.request<any[]>('GET', '/admin/governance/federation/peers')
  registerFederationPeer = (p: any) => this.request<any>('POST', '/admin/governance/federation/peers', p)
  getFederationStatus = () => this.request<any>('GET', '/admin/governance/federation/status')
  getFederationConsistency = () => this.request<any>('GET', '/admin/governance/federation/consistency')
  listFederationAudit = () => this.request<any>('GET', '/admin/governance/federation/audit-trail')

  // GPU & Infra
  listGpuGroups = () => this.request<any[]>('GET', '/admin/infra/gpu/groups')
  getGpuAutoscalingStatus = () => this.request<any>('GET', '/admin/infra/gpu/autoscaling/status')

  // Prompts
  listPrompts = () => this.request<any[]>('GET', '/api/v1/admin/prompts/templates')
  getPrompt = (id: string) => this.request<any>('GET', `/api/v1/admin/prompts/templates/${id}`)
  createPromptTemplate = (p: any) => this.request<any>('POST', '/api/v1/admin/prompts/templates', p)
  createPromptVersion = (id: string, v: any) => this.request<any>('POST', `/api/v1/admin/prompts/templates/${id}/versions`, v)
  updatePrompt = (id: string, p: any) => this.request<any>('PATCH', `/api/v1/admin/prompts/templates/${id}`, p)

  // Portal
  listPlans = () => this.request<any[]>('GET', '/portal/plans')
  getProfile = () => this.request<any>('GET', '/portal/me')
  getUsageStats = () => this.request<any>('GET', '/portal/usage-stats')
}

const api = new APIClient()
export default api
