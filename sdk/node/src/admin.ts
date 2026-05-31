export class AdminAPI {
  constructor(private client: any) {}

  async listClients(): Promise<any[]> {
    return this.client.request('GET', '/admin/clients');
  }

  async createClient(clientDef: any): Promise<any> {
    return this.client.request('POST', '/admin/clients', clientDef);
  }

  async blockClient(clientId: string): Promise<any> {
    return this.client.request('POST', `/admin/clients/${clientId}/block`);
  }

  async unblockClient(clientId: string): Promise<any> {
    return this.client.request('POST', `/admin/clients/${clientId}/unblock`);
  }

  async listApiKeys(): Promise<any[]> {
    return this.client.request('GET', '/admin/api-keys');
  }

  async createApiKey(keyDef: any): Promise<any> {
    return this.client.request('POST', '/admin/api-keys', keyDef);
  }

  async deleteApiKey(apiKeyId: string): Promise<any> {
    return this.client.request('DELETE', `/admin/api-keys/${apiKeyId}`);
  }

  async listModels(): Promise<any[]> {
    return this.client.request('GET', '/admin/models');
  }

  async createModel(modelDef: any): Promise<any> {
    return this.client.request('POST', '/admin/models', modelDef);
  }

  async listBackends(): Promise<any[]> {
    return this.client.request('GET', '/admin/backends');
  }

  async createBackend(backendDef: any): Promise<any> {
    return this.client.request('POST', '/admin/backends', backendDef);
  }

  async getUsageSummary(): Promise<any> {
    return this.client.request('GET', '/admin/usage/summary');
  }

  async getRevenueSummary(): Promise<any> {
    return this.client.request('GET', '/admin/revenue/summary');
  }

  async listBillingPlans(): Promise<any[]> {
    return this.client.request('GET', '/admin/billing/plans');
  }

  async createBillingPlan(planDef: any): Promise<any> {
    return this.client.request('POST', '/admin/billing/plans', planDef);
  }

  async listInvoices(): Promise<any[]> {
    return this.client.request('GET', '/admin/billing/invoices');
  }

  async listPayments(): Promise<any[]> {
    return this.client.request('GET', '/admin/billing/payments');
  }

  async listSecurityEvents(): Promise<any[]> {
    return this.client.request('GET', '/admin/security/events');
  }

  async listRbacUsers(): Promise<any[]> {
    return this.client.request('GET', '/admin/rbac/users');
  }

  async createRbacUser(userDef: any): Promise<any> {
    return this.client.request('POST', '/admin/rbac/users', userDef);
  }

  async listRbacRoles(): Promise<any[]> {
    return this.client.request('GET', '/admin/rbac/roles');
  }

  async whoami(): Promise<any> {
    return this.client.request('GET', '/admin/tests/auth/whoami');
  }
}
