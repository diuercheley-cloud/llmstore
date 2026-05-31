export class DeploymentsAPI {
  constructor(private client: any) {}

  async create(agentId: string, deploymentDef: any): Promise<any> {
    return this.client.request('POST', `/${agentId}/deployments`, deploymentDef);
  }

  async list(): Promise<any[]> {
    return this.client.request('GET', '/deployments');
  }

  async get(deploymentId: string): Promise<any> {
    return this.client.request('GET', `/deployments/${deploymentId}`);
  }

  async pause(deploymentId: string): Promise<any> {
    return this.client.request('POST', `/deployments/${deploymentId}/pause`);
  }

  async resume(deploymentId: string): Promise<any> {
    return this.client.request('POST', `/deployments/${deploymentId}/resume`);
  }

  async archive(deploymentId: string): Promise<any> {
    return this.client.request('POST', `/deployments/${deploymentId}/archive`);
  }

  async getUsage(deploymentId: string): Promise<any> {
    return this.client.request('GET', `/deployments/${deploymentId}/usage`);
  }

  async getSla(deploymentId: string): Promise<any> {
    return this.client.request('GET', `/deployments/${deploymentId}/sla`);
  }
}
