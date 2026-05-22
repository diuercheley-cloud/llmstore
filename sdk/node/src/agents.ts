export class AgentsAPI {
  constructor(private client: any) {}

  async list(): Promise<any[]> {
    return this.client.request('GET', '/client/agents');
  }

  async create(manifest: any): Promise<any> {
    return this.client.request('POST', '/client/agents', manifest);
  }

  async run(agentId: string, inputData: any, correlationId?: string): Promise<any> {
    return this.client.request('POST', `/client/agents/${agentId}/run`, {
      input_data: inputData,
      correlation_id: correlationId,
    });
  }

  async getRun(runId: string): Promise<any> {
    return this.client.request('GET', `/client/agents/runs/${runId}`);
  }

  async cancelRun(runId: string): Promise<any> {
    return this.client.request('POST', `/client/agents/runs/${runId}/cancel`);
  }

  async streamEvents(runId: string): Promise<any> {
    return this.client.request('GET', `/client/agents/runs/${runId}/events`);
  }
}

export class AgentEvalsAPI {
  constructor(private client: any) {}

  async run(agentId: string, suiteId?: string): Promise<any> {
    return this.client.request('POST', `/client/agents/${agentId}/evals/run`, {
      suite_id: suiteId,
    });
  }
}
