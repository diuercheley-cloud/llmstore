export class SessionsAPI {
  constructor(private client: any) {}

  async create(agentId: string, params?: any): Promise<any> {
    return this.client.request('POST', `/v1/agents/sessions/${agentId}`, params || {});
  }

  async list(): Promise<any[]> {
    return this.client.request('GET', '/v1/agents/sessions');
  }

  async get(sessionId: string): Promise<any> {
    return this.client.request('GET', `/v1/agents/sessions/${sessionId}`);
  }

  async delete(sessionId: string): Promise<any> {
    return this.client.request('DELETE', `/v1/agents/sessions/${sessionId}`);
  }

  async update(sessionId: string, params: any): Promise<any> {
    return this.client.request('PATCH', `/v1/agents/sessions/${sessionId}`, params);
  }

  async sendMessage(sessionId: string, message: any): Promise<any> {
    return this.client.request('POST', `/v1/agents/sessions/${sessionId}/messages`, message);
  }

  async listMessages(sessionId: string): Promise<any[]> {
    return this.client.request('GET', `/v1/agents/sessions/${sessionId}/messages`);
  }

  async run(sessionId: string, inputData: any): Promise<any> {
    return this.client.request('POST', `/v1/agents/sessions/${sessionId}/runs`, inputData);
  }
}
