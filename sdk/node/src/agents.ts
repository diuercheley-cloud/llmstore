export class AgentsAPI {
  constructor(private client: any) {}

  async list(): Promise<any[]> {
    return this.client.request('GET', '/v1/agents');
  }

  async create(manifest: any): Promise<any> {
    return this.client.request('POST', '/v1/agents', manifest);
  }

  async get(agentId: string): Promise<any> {
    return this.client.request('GET', `/v1/agents/${agentId}`);
  }

  async run(agentId: string, inputData: any, correlationId?: string): Promise<any> {
    return this.client.request('POST', `/v1/agents/${agentId}/runs`, {
      input_data: inputData,
      correlation_id: correlationId,
    });
  }

  async getRun(runId: string): Promise<any> {
    return this.client.request('GET', `/v1/agents/runs/${runId}`);
  }

  async cancelRun(runId: string): Promise<any> {
    return this.client.request('POST', `/v1/agents/runs/${runId}/cancel`);
  }

  async streamEvents(runId: string): Promise<any> {
    return this.client.request('GET', `/v1/agents/runs/${runId}/events`);
  }

  async update(agentId: string, manifest: any): Promise<any> {
    return this.client.request('PATCH', `/admin/agents/${agentId}`, manifest);
  }

  async activate(agentId: string): Promise<any> {
    return this.client.request('POST', `/admin/agents/${agentId}/activate`);
  }

  async deprecate(agentId: string): Promise<any> {
    return this.client.request('POST', `/admin/agents/${agentId}/deprecate`);
  }
}

export class AgentEvalsAPI {
  constructor(private client: any) {}

  async run(agentId: string, suiteId?: string): Promise<any> {
    return this.client.request('POST', `/client/agents/${agentId}/evals/run`, {
      suite_id: suiteId,
    });
  }

  async createDataset(datasetDef: any): Promise<any> {
    return this.client.request('POST', '/admin/agent-evals/datasets', datasetDef);
  }

  async createDatasetVersion(datasetId: string, versionDef: any): Promise<any> {
    return this.client.request('POST', `/admin/agent-evals/datasets/${datasetId}/versions`, versionDef);
  }

  async getReports(agentId: string): Promise<any[]> {
    return this.client.request('GET', `/admin/agent-evals/reports/${agentId}`);
  }

  async runAdmin(evalDef: any): Promise<any> {
    return this.client.request('POST', '/admin/agent-evals/run', evalDef);
  }

  async promotionCheck(agentId: string): Promise<any> {
    return this.client.request('POST', `/admin/agent-evals/promotion-check/${agentId}`);
  }
}

export class AdminAgentsAPI {
  constructor(private client: any) {}

  async list(): Promise<any[]> {
    return this.client.request('GET', '/admin/agents');
  }

  async create(agentDef: any): Promise<any> {
    return this.client.request('POST', '/admin/agents', agentDef);
  }

  async update(agentId: string, agentDef: any): Promise<any> {
    return this.client.request('PATCH', `/admin/agents/${agentId}`, agentDef);
  }

  async getCatalog(): Promise<any[]> {
    return this.client.request('GET', '/admin/agents/catalog');
  }

  async listBudgets(): Promise<any[]> {
    return this.client.request('GET', '/admin/agents/budgets');
  }

  async validateBudget(budgetDef: any): Promise<any> {
    return this.client.request('POST', '/admin/agents/budgets/validate', budgetDef);
  }

  async registryList(): Promise<any[]> {
    return this.client.request('GET', '/admin/agent-registry');
  }

  async registryCreate(entryDef: any): Promise<any> {
    return this.client.request('POST', '/admin/agent-registry', entryDef);
  }

  async registryGet(entryId: string): Promise<any> {
    return this.client.request('GET', `/admin/agent-registry/${entryId}`);
  }

  async registryApprove(entryId: string): Promise<any> {
    return this.client.request('POST', `/admin/agent-registry/${entryId}/approve`);
  }

  async registryActivate(entryId: string): Promise<any> {
    return this.client.request('POST', `/admin/agent-registry/${entryId}/activate`);
  }

  async listJobs(): Promise<any[]> {
    return this.client.request('GET', '/admin/agents/execution/jobs');
  }

  async listWorkers(): Promise<any[]> {
    return this.client.request('GET', '/admin/agents/execution/workers');
  }

  async getReadiness(): Promise<any> {
    return this.client.request('GET', '/admin/agents/readiness');
  }

  async getAnalyticsOverview(): Promise<any> {
    return this.client.request('GET', '/api/v1/admin/agents/analytics/overview');
  }

  async getObservabilityOverview(): Promise<any> {
    return this.client.request('GET', '/admin/agents/observability/overview');
  }

  async a2aDiscover(): Promise<any[]> {
    return this.client.request('GET', '/admin/agents/a2a/discover');
  }

  async a2aGetProfile(agentId: string): Promise<any> {
    return this.client.request('GET', `/admin/agents/a2a/profile/${agentId}`);
  }

  async a2aAnnounce(announcement: any): Promise<any> {
    return this.client.request('POST', '/admin/agents/a2a/announce', announcement);
  }
}
