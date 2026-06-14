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

  private async request<T = any>(
    method: string,
    path: string,
    data?: any,
    params?: any,
    headers?: Record<string, string>,
    extraConfig?: any,
  ): Promise<T> {
    const config: any = {
      method,
      url: path,
      data,
      headers,
      ...extraConfig,
    }

    if (params) {
      if (params instanceof URLSearchParams) {
        config.params = params
      } else {
        const searchParams = new URLSearchParams()
        Object.entries(params).forEach(([key, value]) => {
          if (value !== undefined && value !== null) {
            if (Array.isArray(value)) {
              value.forEach((v) => searchParams.append(key, String(v)))
            } else {
              searchParams.append(key, String(value))
            }
          }
        })
        config.params = searchParams
      }
    }

    const res = await this.client.request<T>(config)
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
  updateBackend = (id: string, b: any) => this.request<any>('PATCH', `/admin/backends/${id}`, b)
  listBackendModels = (b: any) => this.request<any>('POST', '/admin/backends/list-models', b)
  getBackendsHealth = () => this.request<any>('GET', '/admin/backends/health')
  getBackendHealth = (id: string) => this.request<any>('GET', `/admin/backends/${id}/health`)
  getBackendLogs = (id: string) => this.request<any>('GET', `/admin/backends/${id}/logs`)
  startBackend = (id: string) => this.request<any>('POST', `/admin/backends/${id}/start`)
  stopBackend = (id: string) => this.request<any>('POST', `/admin/backends/${id}/stop`)
  restartBackend = (id: string) => this.request<any>('POST', `/admin/backends/${id}/restart`)
  reconcileBackend = (id: string) => this.request<any>('POST', `/admin/backends/${id}/lifecycle/reconcile`)
  reconcileAllBackends = () => this.request<any>('POST', '/admin/backends/lifecycle/reconcile-all')
  getBackendLifecycleObserved = (id: string) => this.request<any>('GET', `/admin/backends/${id}/lifecycle/observed`)
  getBackendDriftHistory = () => this.request<any>('GET', '/admin/backends/lifecycle/drift-history')
  resetBackendCircuitBreaker = () => this.request<any>('POST', '/admin/backends/circuit-breaker/reset')

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
  getCostsSummary = (params?: any) => this.request<any>('GET', '/api/admin/costs/summary', undefined, params)
  getCostsByAgent = (params?: any) => this.request<any[]>('GET', '/api/admin/costs/by-agent', undefined, params)
  getCostsByTool = (params?: any) => this.request<any[]>('GET', '/api/admin/costs/by-tool', undefined, params)
  getCostsByTenant = (params?: any) => this.request<any[]>('GET', '/api/admin/costs/by-tenant', undefined, params)
  exportCosts = (params: any) => this.request<any>('GET', '/api/admin/costs/export', undefined, params, undefined, { responseType: 'blob' })
  listInvoices = () => this.request<any[]>('GET', '/admin/billing/invoices')
  previewInvoices = () => this.request<any>('GET', '/admin/billing/invoices/preview')
  previewClientInvoice = (clientId: string) => this.request<any>('GET', `/admin/billing/clients/${clientId}/invoice/preview`)
  generateInvoices = (payload: any) => this.request<any>('POST', '/admin/billing/invoices/generate', payload)
  runBillingCycle = () => this.request<any>('POST', '/admin/billing/run-cycle')
  listBillingPlansAdmin = () => this.request<any[]>('GET', '/admin/billing/plans')
  createBillingPlan = (payload: any) => this.request<any>('POST', '/admin/billing/plans', payload)
  updateBillingPlan = (id: string, payload: any) => this.request<any>('PATCH', `/admin/billing/plans/${id}`, payload)
  setBillingPlanModels = (id: string, allowedModels: string[]) => this.request<any>('PATCH', `/admin/billing/plans/${id}/models`, { allowed_models: allowedModels })
  listPricingRules = () => this.request<any[]>('GET', '/admin/billing/pricing-rules')
  
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
  listAdminAgentRuns = (tenantId?: string) => this.request<any[]>('GET', '/agents/runs', undefined, tenantId ? { tenant_id: tenantId } : undefined)
  getAdminAgentRun = (runId: string) => this.request<any>('GET', `/agents/runs/${runId}`)
  getAdminAgentRunSteps = (runId: string) => this.request<any[]>('GET', `/agents/runs/${runId}/steps`)
  cancelAdminAgentRun = (runId: string) => this.request<any>('POST', `/agents/runs/${runId}/cancel`)
  pauseAdminAgentRun = (runId: string) => this.request<any>('POST', `/agents/runs/${runId}/pause`)
  resumeAdminAgentRun = (runId: string) => this.request<any>('POST', `/agents/runs/${runId}/resume`)

  // Agent Analytics
  getAgentAnalytics = (id: string) => this.request<any>('GET', `/api/v1/admin/agents/analytics/${id}`)
  listAdminAgents = (tenantId?: string) => this.request<any[]>('GET', '/admin/agents', undefined, tenantId ? { tenant_id: tenantId } : undefined)
  createAdminAgent = (payload: any) => this.request<any>('POST', '/admin/agents', payload)
  updateAdminAgent = (id: string, payload: any) => this.request<any>('PATCH', `/admin/agents/${id}`, payload)
  activateAdminAgent = (id: string) => this.request<any>('POST', `/admin/agents/${id}/activate`)
  deprecateAdminAgent = (id: string) => this.request<any>('POST', `/admin/agents/${id}/deprecate`)
  getAdminAgentBudgets = () => this.request<any>('GET', '/admin/agents/budgets')
  validateAdminAgentBudget = (agentId: string, runId: string) => this.request<any>('POST', '/admin/agents/budgets/validate', undefined, { agent_id: agentId, run_id: runId })
  getAdminAgentSloClasses = () => this.request<any>('GET', '/admin/agents/slo/classes')
  getAdminAgentSloReport = (agentId?: string) => this.request<any>('GET', '/admin/agents/slo/report', undefined, agentId ? { agent_id: agentId } : undefined)
  listAdminAgentIncidentPlaybooks = () => this.request<any>('GET', '/admin/agents/incidents/playbooks')
  runAdminAgentIncidentPlaybook = (id: string, payload: any) => this.request<any>('POST', `/admin/agents/incidents/${id}/run-playbook`, payload)

  // Studio
  listStudioFlows = () => this.request<any[]>('GET', '/admin/agents/studio/flows')
  createStudioFlow = (f: any) => this.request<any>('POST', '/admin/agents/studio/flows', f)
  getStudioFlow = (id: string) => this.request<any>('GET', `/admin/agents/studio/flows/${id}`)
  validateStudioFlow = (id: string) => this.request<any>('POST', `/admin/agents/studio/flows/${id}/validate`)
  compileStudioFlow = (id: string) => this.request<any>('POST', `/admin/agents/studio/flows/${id}/compile`)
  explainStudioFlow = (id: string) => this.request<any>('POST', `/admin/agents/studio/flows/${id}/explain`)
  dryRunStudioFlow = (id: string, input?: any) => this.request<any>('POST', `/admin/agents/studio/flows/${id}/dry-run`, input || {})
  listStudioTemplates = () => this.request<any>('GET', '/admin/agents/studio/templates')
  getStudioTemplate = (id: string) => this.request<any>('GET', `/admin/agents/studio/templates/${id}`)
  saveStudioFlowVersion = (flowId: string, payload: any) => this.request<any>('POST', `/admin/agents/studio/flows/${flowId}/versions`, payload)
  getStudioVersionDag = (flowId: string, versionId: string) => this.request<any>('GET', `/admin/agents/studio/flows/${flowId}/versions/${versionId}/dag`)
  validateStudioVersion = (versionId: string) => this.request<any>('POST', `/admin/agents/studio/versions/${versionId}/validate`)
  compileStudioVersion = (versionId: string) => this.request<any>('POST', `/admin/agents/studio/versions/${versionId}/compile`)
  deployStudioVersionReal = (versionId: string, inputData: any) => this.request<any>('POST', `/admin/agents/studio/versions/${versionId}/deploy-real`, inputData)
  deployStudioFlow = (flowId: string, inputData?: any) => this.request<any>('POST', `/admin/agents/studio/flows/${flowId}/deploy`, inputData || {})
  getStudioRunTrace = (runId: string) => this.request<any>('GET', `/admin/agents/studio/flows/runs/${runId}/trace`)

  // MCP
  listMcpServers = () => this.request<any[]>('GET', '/admin/agents/mcp/servers')
  registerMcpServer = (s: any) => this.request<any>('POST', '/admin/agents/mcp/servers', s)
  discoverMcpTools = (id: string) => this.request<any>('POST', `/admin/agents/mcp/servers/${id}/discover`)
  approveMcpTool = (id: string, tool: string) => this.request<any>('POST', `/admin/agents/mcp/servers/${id}/approve-tool`, { tool_name: tool })
  listMcpTools = () => this.request<any[]>('GET', '/admin/agents/mcp/tools')
  listMcpAudit = () => this.request<any[]>('GET', '/admin/agents/mcp/audit')
  listProtocolMcpServers = (tenantId?: string) => this.request<any[]>('GET', '/admin/agents/protocols/mcp/servers', undefined, tenantId ? { tenant_id: tenantId } : undefined)
  approveProtocolMcpTool = (serverId: string, toolName: string) => this.request<any>('POST', `/admin/agents/protocols/mcp/servers/${serverId}/approve-tool`, undefined, { tool_name: toolName })
  listA2aPeers = (tenantId?: string) => this.request<any[]>('GET', '/admin/agents/protocols/a2a/peers', undefined, tenantId ? { tenant_id: tenantId } : undefined)
  dryRunA2aHandshake = (peerUrl: string) => this.request<any>('POST', '/admin/agents/protocols/a2a/handshake/dry-run', undefined, { peer_url: peerUrl })
  explainProtocolTrust = (protocol: string, entityId: string, action: string = 'access') => this.request<any>('GET', '/admin/agents/protocols/trust/explain', undefined, { protocol, entity_id: entityId, action })

  // Agent Approvals
  listPendingApprovals = () => this.request<{items: any[]}>('GET', '/admin/agents/approval-portal/pending')
  getApprovalRequest = (id: string) => this.request<any>('GET', `/admin/agents/approval-portal/approvals/${id}`)
  decideApproval = (id: string, decision: string, reason?: string) => this.request<any>('POST', `/admin/agents/approval-portal/approvals/${id}/decide`, { decision, reason })
  listAgentApprovalsAdmin = (params?: any) => this.request<any[]>('GET', '/admin/agent-approvals', undefined, params)
  getAgentApprovalAdmin = (id: string) => this.request<any>('GET', `/admin/agent-approvals/${id}`)
  approveAgentApprovalAdmin = (id: string, decisionReason?: string) => this.request<any>('POST', `/admin/agent-approvals/${id}/approve`, { decision_reason: decisionReason })
  rejectAgentApprovalAdmin = (id: string, decisionReason?: string) => this.request<any>('POST', `/admin/agent-approvals/${id}/reject`, { decision_reason: decisionReason })
  requestChangesAgentApprovalAdmin = (id: string, decisionReason?: string) => this.request<any>('POST', `/admin/agent-approvals/${id}/request-changes`, { decision_reason: decisionReason })

  // Agent Memory
  listAgentMemoryItems = (tenantId: string, agentId?: string) => this.request<any[]>('GET', '/admin/agents/memory/items', undefined, { tenant_id: tenantId, ...(agentId ? { agent_id: agentId } : {}) })
  listAgentMemoryAccessEvents = (tenantId: string, agentId?: string, limit: number = 100) => this.request<any[]>('GET', '/admin/agents/memory/access-events', undefined, { tenant_id: tenantId, limit, ...(agentId ? { agent_id: agentId } : {}) })
  listAgentMemoryPolicies = (tenantId: string) => this.request<any[]>('GET', '/admin/agents/memory/policies', undefined, { tenant_id: tenantId })
  createAgentMemoryPolicy = (payload: any) => this.request<any>('POST', '/admin/agents/memory/policies', payload)
  listAgentMemoryConsents = (tenantId: string) => this.request<any[]>('GET', '/admin/agents/memory/consents', undefined, { tenant_id: tenantId })
  createAgentMemoryConsent = (payload: any) => this.request<any>('POST', '/admin/agents/memory/consents', payload)
  searchAgentMemory = (payload: any) => this.request<any[]>('POST', '/admin/agents/memory/search', payload)
  explainAgentMemory = (memoryId: string) => this.request<any>('GET', `/admin/agents/memory/explain/${memoryId}`)
  summarizeAgentMemory = (payload: any) => this.request<any>('POST', '/admin/agents/memory/summarize', payload)
  exportAgentMemory = (payload: any) => this.request<any[]>('POST', '/admin/agents/memory/export', payload)
  createAgentMemoryDeleteRequest = (payload: any) => this.request<any>('POST', '/admin/agents/memory/delete-request', payload)
  runAgentMemoryRetention = () => this.request<any>('POST', '/admin/agents/memory/retention/run')
  deleteAgentMemoryItem = (itemId: string, tenantId: string) => this.request<any>('DELETE', `/admin/agents/memory/items/${itemId}`, undefined, { tenant_id: tenantId })

  // Agent Tools
  listAgentToolsAdmin = (params?: any) => this.request<any[]>('GET', '/admin/agent-tools', undefined, params)
  createAgentToolAdmin = (payload: any) => this.request<any>('POST', '/admin/agent-tools', payload)
  updateAgentToolAdmin = (id: string, payload: any) => this.request<any>('PATCH', `/admin/agent-tools/${id}`, payload)
  enableAgentToolAdmin = (id: string) => this.request<any>('POST', `/admin/agent-tools/${id}/enable`)
  disableAgentToolAdmin = (id: string) => this.request<any>('POST', `/admin/agent-tools/${id}/disable`)
  listAgentToolInvocations = (id: string) => this.request<any[]>('GET', `/admin/agent-tools/${id}/invocations`)
  dryRunAgentTool = (id: string, parameters: any, tenantId: string = 'default') => this.request<any>('POST', `/admin/agent-tools/${id}/dry-run`, { parameters }, { tenant_id: tenantId })
  executeAgentToolAdmin = (id: string, parameters: any, tenantId: string = 'default') => this.request<any>('POST', `/admin/agent-tools/${id}/execute`, { parameters }, { tenant_id: tenantId })
  rollbackAgentToolInvocation = (id: string, tenantId: string = 'default') => this.request<any>('POST', `/admin/agent-tools/invocations/${id}/rollback`, undefined, { tenant_id: tenantId })
  listAgentToolSideEffects = (tenantId: string = 'default') => this.request<any[]>('GET', '/admin/agent-tools/side-effects', undefined, { tenant_id: tenantId })
  listAgentToolCredentials = (tenantId: string = 'default') => this.request<any[]>('GET', '/admin/agent-tools/credentials', undefined, { tenant_id: tenantId })
  createAgentToolCredential = (payload: any) => this.request<any>('POST', '/admin/agent-tools/credentials', payload)
  revokeAgentToolCredential = (id: string, tenantId: string = 'default') => this.request<any>('POST', `/admin/agent-tools/credentials/${id}/revoke`, undefined, { tenant_id: tenantId })
  listAgentToolQuotas = (tenantId: string = 'default') => this.request<any[]>('GET', '/admin/agent-tools/quotas', undefined, { tenant_id: tenantId })

  // Agent Observability
  getAgentObservabilityOverview = () => this.request<any>('GET', '/admin/agents/observability/overview')
  getAgentObservabilityMetricsSummary = (agentId?: string) => this.request<any>('GET', '/admin/agents/observability/metrics/summary', undefined, agentId ? { agent_id: agentId } : undefined)
  getAgentRunTimeline = (runId: string) => this.request<any[]>('GET', `/admin/agents/observability/runs/${runId}/timeline`)
  getAgentRunTrace = (runId: string) => this.request<any>('GET', `/admin/agents/observability/runs/${runId}/trace`)
  getAgentRunTraceCompat = (runId: string) => this.request<any>('GET', `/admin/agents/observability/traces/${runId}`)
  exportAgentTrace = (payload: any) => this.request<any>('POST', '/admin/agents/observability/traces/export', payload)
  getAgentTelemetryStatus = () => this.request<any>('GET', '/admin/agents/observability/telemetry/status')
  replayAgentRun = (runId: string) => this.request<any>('POST', `/admin/agents/observability/runs/${runId}/replay`)

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

  // Agent Evaluation Framework
  listAgentBenchmarks = () => this.request<any[]>('GET', '/admin/evaluation/agent-evaluation/benchmarks')
  runAgentBenchmark = (payload: { agent_id: string; model_name: string; benchmark: string }) => 
    this.request<any>('POST', '/admin/evaluation/agent-evaluation/runs', undefined, payload)
  listAgentBenchmarkReports = () => this.request<any[]>('GET', '/admin/evaluation/agent-evaluation/runs')
  exportAgentBenchmarkReport = (runId: string, benchmark: string, format: 'json' | 'csv' | 'md' = 'json') =>
    this.request<any>('GET', `/admin/evaluation/agent-evaluation/runs/${runId}/export`, undefined, { benchmark, format })
  createAgentEvalDataset = (payload: any) => this.request<any>('POST', '/admin/agent-evals/datasets', payload)
  createAgentEvalDatasetVersion = (id: string, payload: any) => this.request<any>('POST', `/admin/agent-evals/datasets/${id}/versions`, payload)
  runAgentEvalAdmin = (payload: any) => this.request<any>('POST', '/admin/agent-evals/run', payload)
  getAgentEvalReportAdmin = (agentId: string) => this.request<any>('GET', `/admin/agent-evals/reports/${agentId}`)
  checkAgentPromotionGateAdmin = (agentId: string, payload: any) => this.request<any>('POST', `/admin/agent-evals/promotion-check/${agentId}`, payload)

  // MLOps
  listDatasets = () => this.request<any[]>('GET', '/admin/mlops/datasets')
  createDataset = (d: any) => this.request<any>('POST', '/admin/mlops/datasets', d)
  approveDataset = (id: string) => this.request<any>('POST', `/admin/mlops/datasets/${id}/approve`)
  createDatasetVersion = (id: string, v: any) => this.request<any>('POST', `/admin/mlops/datasets/${id}/versions`, v)
  listExperiments = () => this.request<any[]>('GET', '/admin/mlops/experiments')
  getFineTuningJob = (id: string) => this.request<any>('GET', `/admin/mlops/fine-tuning/jobs/${id}`)
  createFineTuningJob = (j: any) => this.request<any>('POST', '/admin/mlops/fine-tuning/jobs', j)
  getModelLineage = (modelId: string) => this.request<any>('GET', `/admin/mlops/model-lineage/${modelId}`)
  
  // Inference Backends (vLLM)
  getVllmHealth = () => this.request<any>('GET', '/admin/inference/backends/vllm/health')
  listVllmModels = () => this.request<any[]>('GET', '/admin/inference/backends/vllm/models')
  testVllm = (req: { prompt: string, model?: string, stream?: boolean }) => this.request<any>('POST', '/admin/inference/backends/vllm/test', req)

  // Vector Stores
  listVectorStores = () => this.request<any>('GET', '/admin/vectorstores/health')
  getVectorStoreProvider = () => this.request<any>('GET', '/admin/vectorstores/provider')
  testVectorStoreConnection = (provider: string) => this.request<any>('POST', `/admin/vectorstores/test?provider=${provider}`)

  // Worker DLQ
  listDlqMessages = () => this.request<any[]>('GET', '/admin/agents/worker/dlq')
  retryDlqItem = (id: string) => this.request<any>('POST', `/admin/agents/worker/dlq/${id}/retry`)
  deleteDlqItem = (id: string) => this.request<any>('DELETE', `/admin/agents/worker/dlq/${id}`)
  getWorkerStatus = () => this.request<any>('GET', '/admin/agents/worker/status')

  // Code Interpreter
  runCode = (payload: { code: string, agent_id?: string, tenant_id?: string }) => this.request<any>('POST', '/admin/agents/code-interpreter/run', payload)
  getCodeRun = (id: string) => this.request<any>('GET', `/admin/agents/code-interpreter/runs/${id}`)
  getCodeArtifact = (id: string) => this.request<any>('GET', `/admin/agents/code-interpreter/artifacts/${id}`)
  cancelCodeRun = (id: string) => this.request<any>('POST', `/admin/agents/code-interpreter/runs/${id}/cancel`)

  // Agent Workspaces / Artifacts
  listAgentWorkspaces = (tenantId: string = 'default') => this.request<any[]>('GET', '/admin/agents/workspaces', undefined, { tenant_id: tenantId })
  createAgentWorkspace = (payload: any) => this.request<any>('POST', '/admin/agents/workspaces', payload)
  listWorkspaceArtifacts = (workspaceId: string, tenantId: string = 'default') => this.request<any[]>('GET', `/admin/agents/workspaces/${workspaceId}/artifacts`, undefined, { tenant_id: tenantId })
  createWorkspaceArtifact = (workspaceId: string, payload: any, tenantId: string = 'default') => this.request<any>('POST', `/admin/agents/workspaces/${workspaceId}/artifacts`, payload, { tenant_id: tenantId })
  getAgentArtifact = (id: string, tenantId: string = 'default') => this.request<any>('GET', `/admin/agents/artifacts/${id}`, undefined, { tenant_id: tenantId })
  listAgentArtifactVersions = (id: string, tenantId: string = 'default') => this.request<any[]>('GET', `/admin/agents/artifacts/${id}/versions`, undefined, { tenant_id: tenantId })
  getAgentArtifactDiff = (id: string, fromVersion: number, toVersion: number, tenantId: string = 'default') => this.request<any>('GET', `/admin/agents/artifacts/${id}/diff`, undefined, { from_version: fromVersion, to_version: toVersion, tenant_id: tenantId })
  lockAgentArtifact = (id: string, payload: any, tenantId: string = 'default') => this.request<any>('POST', `/admin/agents/artifacts/${id}/lock`, payload, { tenant_id: tenantId })
  unlockAgentArtifact = (id: string, holderId: string, tenantId: string = 'default') => this.request<any>('POST', `/admin/agents/artifacts/${id}/unlock`, undefined, { holder_id: holderId, tenant_id: tenantId })
  reviewAgentArtifact = (id: string, payload: any, tenantId: string = 'default') => this.request<any>('POST', `/admin/agents/artifacts/${id}/review`, payload, { tenant_id: tenantId })
  commentAgentArtifact = (id: string, payload: any, tenantId: string = 'default') => this.request<any>('POST', `/admin/agents/artifacts/${id}/comments`, payload, { tenant_id: tenantId })
  exportAgentArtifact = (id: string, tenantId: string = 'default') => this.request<any>('GET', `/admin/agents/artifacts/${id}/export`, undefined, { tenant_id: tenantId })
  listAgentArtifactEvents = (id: string, tenantId: string = 'default') => this.request<any[]>('GET', `/admin/agents/artifacts/${id}/events`, undefined, { tenant_id: tenantId })

  // Agent Routing
  listAgentRoutingCapabilities = () => this.request<any[]>('GET', '/admin/agents/routing/capabilities')
  createAgentRoutingPolicy = (payload: any) => this.request<any>('POST', '/admin/agents/routing/policies', payload)
  simulateAgentRouting = (payload: any) => this.request<any>('POST', '/admin/agents/routing/simulate', payload)
  listAgentRoutingDecisions = (runId?: string) => this.request<any[]>('GET', '/admin/agents/routing/decisions', undefined, runId ? { run_id: runId } : undefined)

  // Agent Readiness
  getAgentReadiness = () => this.request<any>('GET', '/admin/agents/readiness')
  runAgentReadiness = () => this.request<any>('POST', '/admin/agents/readiness/run')

  // Agent Teams
  listAgentTeams = () => this.request<any[]>('GET', '/admin/agents/teams')
  createAgentTeam = (payload: any) => this.request<any>('POST', '/admin/agents/teams', payload)
  runAgentTeam = (id: string, payload: any) => this.request<any>('POST', `/admin/agents/teams/${id}/runs`, payload)
  getAgentTeamTrace = (runId: string) => this.request<any[]>('GET', `/admin/agents/teams/runs/${runId}/trace`)

  // Agent Workflows
  createAgentWorkflow = (payload: any) => this.request<any>('POST', '/admin/agents/workflows', payload)
  runAgentWorkflow = (id: string, payload: any) => this.request<any>('POST', `/admin/agents/workflows/${id}/run`, payload)
  getAgentWorkflowRun = (id: string, runId: string) => this.request<any>('GET', `/admin/agents/workflows/${id}/run/${runId}`)
  signalAgentWorkflow = (id: string, runId: string, payload: any) => this.request<any>('POST', `/admin/agents/workflows/${id}/run/${runId}/signal`, payload)
  cancelAgentWorkflow = (id: string, runId: string) => this.request<any>('POST', `/admin/agents/workflows/${id}/run/${runId}/cancel`)
  createAgentWorkflowWebhookWait = (id: string, runId: string) => this.request<any>('POST', `/admin/agents/workflows/${id}/run/${runId}/webhook-wait`)
  createAgentWorkflowPollingJob = (id: string, runId: string, payload: any) => this.request<any>('POST', `/admin/agents/workflows/${id}/run/${runId}/polling-job`, payload)
  listAgentWorkflowExternalEvents = (id: string, runId: string) => this.request<any[]>('GET', `/admin/agents/workflows/${id}/run/${runId}/external-events`)

  // Sovereign/Airgap Governance
  listAirgapPackages = () => this.request<any[]>('GET', '/admin/governance/airgap/packages')
  createAirgapPackage = (p: any) => this.request<any>('POST', '/admin/governance/airgap/packages', p)
  exportAirgapPackage = (id: string, payload: any) => this.request<any>('POST', `/admin/governance/airgap/packages/${id}/export`, payload)
  importAirgapPackage = (bundle: any) => this.request<any>('POST', '/admin/governance/airgap/packages/import', { package_bundle: bundle })
  verifyAirgapPackage = (id: string) => this.request<any>('POST', `/admin/governance/airgap/packages/${id}/verify`)
  rejectAirgapPackage = (id: string, reason: string) => this.request<any>('POST', `/admin/governance/airgap/packages/${id}/reject`, { reason })
  
  // Operational Attestation (Runtime)
  listAttestations = () => this.request<any[]>('GET', '/admin/attestation/runtime')
  getAttestationDetail = (id: string) => this.request<any>('GET', `/admin/attestation/runtime/${id}`)
  verifyAttestation = (id: string) => this.request<any>('POST', `/admin/attestation/runtime/${id}/verify`)
  getAttestationSummary = () => this.request<any>('GET', '/admin/attestation/runtime/summary')
  listAttestationEvidence = () => this.request<any[]>('GET', '/admin/attestation/evidence')
  listAttestationChallenges = () => this.request<any[]>('GET', '/admin/attestation/challenges')
  issueAttestationChallenge = (payload: any) => this.request<any>('POST', '/admin/attestation/challenges', payload)
  respondAttestationChallenge = (id: string, payload: any) => this.request<any>('POST', `/admin/attestation/challenges/${id}/respond`, payload)
  listAttestationDrift = () => this.request<any[]>('GET', '/admin/attestation/drift')
  detectAttestationDrift = (id: string, payload: any) => this.request<any>('POST', `/admin/attestation/runtime/${id}/drift`, payload)
  revokeAttestation = (id: string, payload: any) => this.request<any>('POST', `/admin/attestation/runtime/${id}/revoke`, payload)
  computeAttestationTrustScore = (id: string) => this.request<any>('POST', `/admin/attestation/runtime/${id}/trust-score`)

  // AIOps
  getAIOpsStatus = () => this.request<any>('GET', '/admin/aiops/status')
  getAIOpsForecasts = (limit: number = 50) => this.request<any[]>('GET', '/admin/aiops/forecasts', undefined, { limit })
  getAIOpsAnomalies = (limit: number = 50) => this.request<any[]>('GET', '/admin/aiops/anomalies', undefined, { limit })
  getAIOpsRecommendations = (limit: number = 50) => this.request<any[]>('GET', '/admin/aiops/recommendations', undefined, { limit })
  getAIOpsRiskTrends = (limit: number = 50) => this.request<any[]>('GET', '/admin/aiops/risk-trends', undefined, { limit })
  runAIOpsCycle = () => this.request<any>('POST', '/admin/aiops/run-cycle')

  // Commercial Workflows
  getWorkflowGovernanceStatus = () => this.request<any>('GET', '/admin/workflows/status')
  listWorkflowDefinitions = () => this.request<any>('GET', '/admin/workflows/definitions')
  createWorkflowDefinition = (payload: any) => this.request<any>('POST', '/admin/workflows/definitions', payload)
  listWorkflowExecutions = (tenantId?: string) => this.request<any>('GET', '/admin/workflows/executions', undefined, tenantId ? { tenant_id: tenantId } : undefined)
  createWorkflowExecution = (payload: any) => this.request<any>('POST', '/admin/workflows/executions', payload)
  getWorkflowExecution = (id: string) => this.request<any>('GET', `/admin/workflows/executions/${id}`)
  pauseWorkflowExecution = (id: string) => this.request<any>('POST', `/admin/workflows/executions/${id}/pause`)
  resumeWorkflowExecution = (id: string, resumeToken?: string) => this.request<any>('POST', `/admin/workflows/executions/${id}/resume`, undefined, resumeToken ? { resume_token: resumeToken } : undefined)
  rollbackWorkflowExecution = (id: string, checkpointId: string) => this.request<any>('POST', `/admin/workflows/executions/${id}/rollback`, { checkpoint_id: checkpointId })
  getWorkflowGovernanceExecution = (id: string) => this.request<any>('GET', `/admin/workflows/governance/executions/${id}`)
  getWorkflowGovernanceLedger = (id: string) => this.request<any>('GET', `/admin/workflows/governance/executions/${id}/ledger`)
  getWorkflowGovernanceSnapshots = (id: string) => this.request<any>('GET', `/admin/workflows/governance/executions/${id}/snapshots`)
  listWorkflowCheckpoints = (id: string) => this.request<any>('GET', `/admin/workflows/executions/${id}/checkpoints`)
  listWorkflowApprovals = (executionId?: string) => this.request<any>('GET', '/admin/workflows/approvals', undefined, executionId ? { execution_id: executionId } : undefined)
  requestWorkflowApproval = (executionId: string, stageKey: string, payload: any) => this.request<any>('POST', `/admin/workflows/approvals/executions/${executionId}/stages/${stageKey}/request`, payload)
  decideWorkflowApproval = (chainId: string, payload: any) => this.request<any>('POST', `/admin/workflows/approvals/${chainId}/decide`, payload)
  listWorkflowReplaySessions = (executionId?: string) => this.request<any>('GET', '/admin/workflows/replay-sessions', undefined, executionId ? { execution_id: executionId } : undefined)
  createWorkflowReplaySession = (payload: any) => this.request<any>('POST', '/admin/workflows/replay-sessions', payload)
  completeWorkflowReplaySession = (id: string) => this.request<any>('POST', `/admin/workflows/replay-sessions/${id}/complete`)
  listWorkflowReplays = () => this.request<any>('GET', '/admin/workflows/replays')
  createWorkflowReplay = (executionId: string) => this.request<any>('POST', `/admin/workflows/replay/${executionId}`)
  attachWorkflowReplayExecution = (replayId: string, replayExecutionId: string) => this.request<any>('POST', `/admin/workflows/replay/${replayId}/attach/${replayExecutionId}`)
  verifyWorkflowReplay = (replayId: string) => this.request<any>('POST', `/admin/workflows/replay/${replayId}/verify`)
  listWorkflowReports = () => this.request<any>('GET', '/admin/workflows/reports')

  // Model Supply Chain
  getSupplyChainRegistry = () => this.request<any>('GET', '/supply-chain/registry')
  registerSupplyChainModel = (payload: any) => this.request<any>('POST', '/supply-chain/register', payload)
  verifySupplyChainEntry = (id: string) => this.request<any>('POST', `/supply-chain/${id}/verify`)
  approveSupplyChainEntry = (id: string, payload: any) => this.request<any>('POST', `/supply-chain/${id}/approve`, payload)
  quarantineSupplyChainEntry = (id: string, payload: any) => this.request<any>('POST', `/supply-chain/${id}/quarantine`, payload)
  revokeSupplyChainEntry = (id: string, payload: any) => this.request<any>('POST', `/supply-chain/${id}/revoke`, payload)
  getSupplyChainProvenance = () => this.request<any>('GET', '/supply-chain/provenance')
  createSupplyChainProvenance = (payload: any) => this.request<any>('POST', '/supply-chain/provenance', payload)
  getSupplyChainBundles = () => this.request<any>('GET', '/supply-chain/bundles')
  createSupplyChainBundle = (payload: any) => this.request<any>('POST', '/supply-chain/bundles', payload)
  verifySupplyChainBundle = (id: string) => this.request<any>('POST', `/supply-chain/bundles/${id}/verify`)
  promoteSupplyChainBundle = (id: string) => this.request<any>('POST', `/supply-chain/bundles/${id}/promote`)
  rejectSupplyChainBundle = (id: string, payload: any) => this.request<any>('POST', `/supply-chain/bundles/${id}/reject`, payload)
  getSupplyChainStatus = () => this.request<any>('GET', '/supply-chain/status')
  getIntegrityScans = (limit: number = 100) => this.request<any>('GET', '/integrity/scans', undefined, { limit })
  runIntegrityScan = (payload: any) => this.request<any>('POST', '/integrity/scan', payload)
  getIntegrityEvents = (limit: number = 100) => this.request<any>('GET', '/integrity/events', undefined, { limit })
  getIntegrityAttestations = (limit: number = 100) => this.request<any>('GET', '/integrity/attestations', undefined, { limit })
  quarantineIntegrityEntry = (id: string) => this.request<any>('POST', `/integrity/quarantine/${id}`)
  reverifyIntegrityEntry = (id: string) => this.request<any>('POST', `/integrity/reverify/${id}`)
  getIntegrityStatus = () => this.request<any>('GET', '/integrity/status')

  // Security / Offline CRL / Hardware Attestation
  listOfflineCrl = () => this.request<any[]>('GET', '/admin/security/offline-crl')
  applyOfflineCrl = (id: string) => this.request<any>('POST', `/admin/security/offline-crl/${id}/apply`)
  listHardwareAttestations = () => this.request<any>('GET', '/admin/security/hardware-attestation')
  verifyHardwareAttestation = (recordId: string) => this.request<any>('POST', '/admin/security/hardware-attestation/verify', { record_id: recordId })

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

  // DLP Dashboard
  listDlpViolations = (tenantId?: string) => this.client.get<any[]>(`/admin/agents/governance/dlp/violations${tenantId ? `?tenant_id=${tenantId}` : ''}`).then(res => res.data)
  getDlpStats = (tenantId?: string) => this.client.get<any>(`/admin/agents/governance/dlp/stats${tenantId ? `?tenant_id=${tenantId}` : ''}`).then(res => res.data)

  // Backups
  listBackups = () => this.request<any[]>('GET', '/admin/backup')
  getBackup = (id: string) => this.request<any>('GET', `/admin/backup/${id}`)
  createLogicalAgentBackup = () => this.request<any>('POST', '/admin/backup', { scope: 'logical-agent-backup' })
  createFullBackup = () => this.createLogicalAgentBackup() // Deprecated alias
  verifyBackup = (id: string) => this.request<any>('POST', `/admin/backup/${id}/verify`)
  restoreBackup = (id: string, dryRun: boolean = false) => this.request<any>('POST', `/admin/backup/${id}/restore`, { dry_run: dryRun })
  createRestoreRequest = (backupId: string, dryRun: boolean) => this.request<any>('POST', '/admin/backup/restore-requests', { backup_id: backupId, dry_run: dryRun })
  approveRestoreRequest = (id: string) => this.request<any>('POST', `/admin/backup/restore-requests/${id}/approve`)
  executeRestoreRequest = (id: string, token: string) => this.request<any>('POST', `/admin/backup/restore-requests/${id}/execute`, { token })
}

const api = new APIClient()
export default api
