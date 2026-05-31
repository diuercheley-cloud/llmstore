export class StudioAPI {
  constructor(private client: any) {}

  async createFlow(flowDef: any): Promise<any> {
    return this.client.request('POST', '/admin/agents/studio/flows', flowDef);
  }

  async listFlows(): Promise<any[]> {
    return this.client.request('GET', '/admin/agents/studio/flows');
  }

  async getFlow(flowId: string): Promise<any> {
    return this.client.request('GET', `/admin/agents/studio/flows/${flowId}`);
  }

  async validateFlow(flowId: string): Promise<any> {
    return this.client.request('POST', `/admin/agents/studio/flows/${flowId}/validate`);
  }

  async compileFlow(flowId: string): Promise<any> {
    return this.client.request('POST', `/admin/agents/studio/flows/${flowId}/compile`);
  }

  async debugRun(runId: string): Promise<any> {
    return this.client.request('GET', `/admin/agents/studio/debug/${runId}`);
  }

  async createVersion(flowId: string, versionDef: any): Promise<any> {
    return this.client.request('POST', `/admin/agents/studio/flows/${flowId}/versions`, versionDef);
  }

  async validateVersion(versionId: string): Promise<any> {
    return this.client.request('POST', `/admin/agents/studio/versions/${versionId}/validate`);
  }

  async compileVersion(versionId: string): Promise<any> {
    return this.client.request('POST', `/admin/agents/studio/versions/${versionId}/compile`);
  }

  async listTemplates(): Promise<any[]> {
    return this.client.request('GET', '/admin/agents/studio/templates');
  }

  async getTemplate(templateId: string): Promise<any> {
    return this.client.request('GET', `/admin/agents/studio/templates/${templateId}`);
  }

  async deployFlow(flowId: string): Promise<any> {
    return this.client.request('POST', `/admin/agents/studio/flows/${flowId}/deploy`);
  }

  async getDag(flowId: string, versionId: string): Promise<any> {
    return this.client.request('GET', `/admin/agents/studio/flows/${flowId}/versions/${versionId}/dag`);
  }
}
