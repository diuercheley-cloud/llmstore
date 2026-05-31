export class MCPAPI {
  constructor(private client: any) {}

  async listServers(): Promise<any[]> {
    return this.client.request('GET', '/admin/agents/mcp/servers');
  }

  async registerServer(serverDef: any): Promise<any> {
    return this.client.request('POST', '/admin/agents/mcp/servers', serverDef);
  }

  async discoverTools(serverId: string): Promise<any> {
    return this.client.request('POST', `/admin/agents/mcp/servers/${serverId}/discover`);
  }

  async callTool(toolName: string, params: any): Promise<any> {
    return this.client.request('POST', `/admin/agents/mcp/tools/${toolName}/call`, params);
  }

  async listTools(): Promise<any[]> {
    return this.client.request('GET', '/admin/agents/mcp/tools');
  }

  async listServerTools(): Promise<any[]> {
    return this.client.request('GET', '/mcp/tools');
  }

  async listServerResources(): Promise<any[]> {
    return this.client.request('GET', '/mcp/resources');
  }

  async listServerPrompts(): Promise<any[]> {
    return this.client.request('GET', '/mcp/prompts');
  }
}
