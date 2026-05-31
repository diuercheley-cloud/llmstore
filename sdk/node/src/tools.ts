export class ToolsAPI {
  constructor(private client: any) {}

  async list(): Promise<any[]> {
    return this.client.request('GET', '/admin/agent-tools');
  }

  async register(toolDef: any): Promise<any> {
    return this.client.request('POST', '/admin/agent-tools', toolDef);
  }

  async update(toolId: string, toolDef: any): Promise<any> {
    return this.client.request('PATCH', `/admin/agent-tools/${toolId}`, toolDef);
  }

  async enable(toolId: string): Promise<any> {
    return this.client.request('POST', `/admin/agent-tools/${toolId}/enable`);
  }

  async disable(toolId: string): Promise<any> {
    return this.client.request('POST', `/admin/agent-tools/${toolId}/disable`);
  }

  async execute(toolId: string, params: any): Promise<any> {
    return this.client.request('POST', `/admin/agent-tools/${toolId}/execute`, params);
  }

  async dryRun(toolId: string, params: any): Promise<any> {
    return this.client.request('POST', `/admin/agent-tools/${toolId}/dry-run`, params);
  }

  async listInvocations(toolId: string): Promise<any[]> {
    return this.client.request('GET', `/admin/agent-tools/${toolId}/invocations`);
  }

  async listCredentials(): Promise<any[]> {
    return this.client.request('GET', '/admin/agent-tools/credentials');
  }

  async createCredential(credential: any): Promise<any> {
    return this.client.request('POST', '/admin/agent-tools/credentials', credential);
  }

  async revokeCredential(credentialId: string): Promise<any> {
    return this.client.request('POST', `/admin/agent-tools/credentials/${credentialId}/revoke`);
  }
}
