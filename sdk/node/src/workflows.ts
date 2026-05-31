export class WorkflowsAPI {
  constructor(private client: any) {}

  async create(workflowDef: any): Promise<any> {
    return this.client.request('POST', '/admin/agents/workflows', workflowDef);
  }

  async run(workflowId: string, inputData: any): Promise<any> {
    return this.client.request('POST', `/admin/agents/workflows/${workflowId}/run`, inputData);
  }

  async getRun(workflowId: string, runId: string): Promise<any> {
    return this.client.request('GET', `/admin/agents/workflows/${workflowId}/run/${runId}`);
  }

  async signal(workflowId: string, runId: string, signalData: any): Promise<any> {
    return this.client.request('POST', `/admin/agents/workflows/${workflowId}/run/${runId}/signal`, signalData);
  }

  async cancelRun(workflowId: string, runId: string): Promise<any> {
    return this.client.request('POST', `/admin/agents/workflows/${workflowId}/run/${runId}/cancel`);
  }
}
