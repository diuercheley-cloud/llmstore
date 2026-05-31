export class KnowledgeGraphAPI {
  constructor(private client: any) {}

  async extract(text: string, options?: any): Promise<any> {
    return this.client.request('POST', '/admin/agents/knowledge-graph/extract', { text, ...options });
  }

  async listEntities(): Promise<any[]> {
    return this.client.request('GET', '/admin/agents/knowledge-graph/entities');
  }

  async listRelations(): Promise<any[]> {
    return this.client.request('GET', '/admin/agents/knowledge-graph/relations');
  }

  async query(query: any): Promise<any> {
    return this.client.request('POST', '/admin/agents/knowledge-graph/query', query);
  }

  async queryAgent(agentId: string, query: any): Promise<any> {
    return this.client.request('POST', `/agents/${agentId}/knowledge/query`, query);
  }
}
