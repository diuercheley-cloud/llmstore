export class SystemAPI {
  constructor(private client: any) {}

  async health(): Promise<any> {
    return this.client.request('GET', '/health');
  }

  async ready(): Promise<any> {
    return this.client.request('GET', '/ready');
  }

  async status(): Promise<any> {
    return this.client.request('GET', '/status');
  }

  async deepHealth(): Promise<any> {
    return this.client.request('GET', '/admin/health/deep');
  }

  async capabilities(): Promise<any[]> {
    return this.client.request('GET', '/admin/capabilities');
  }

  async runtimeSummary(): Promise<any> {
    return this.client.request('GET', '/admin/runtime/summary');
  }

  async operationalReadiness(): Promise<any> {
    return this.client.request('GET', '/operational-readiness');
  }
}
