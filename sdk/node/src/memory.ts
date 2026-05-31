export class MemoryAPI {
  constructor(private client: any) {}

  async listPolicies(): Promise<any[]> {
    return this.client.request('GET', '/admin/agents/memory/policies');
  }

  async createPolicy(policy: any): Promise<any> {
    return this.client.request('POST', '/admin/agents/memory/policies', policy);
  }

  async listConsents(): Promise<any[]> {
    return this.client.request('GET', '/admin/agents/memory/consents');
  }

  async createConsent(consent: any): Promise<any> {
    return this.client.request('POST', '/admin/agents/memory/consents', consent);
  }

  async search(query: any): Promise<any> {
    return this.client.request('POST', '/admin/agents/memory/search', query);
  }

  async export(params: any): Promise<any> {
    return this.client.request('POST', '/admin/agents/memory/export', params);
  }

  async deleteRequest(request: any): Promise<any> {
    return this.client.request('POST', '/admin/agents/memory/delete-request', request);
  }

  async runRetention(): Promise<any> {
    return this.client.request('POST', '/admin/agents/memory/retention/run');
  }

  async listItems(): Promise<any[]> {
    return this.client.request('GET', '/admin/agents/memory/items');
  }

  async deleteItem(itemId: string): Promise<any> {
    return this.client.request('DELETE', `/admin/agents/memory/items/${itemId}`);
  }
}
