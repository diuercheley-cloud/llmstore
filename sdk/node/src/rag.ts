export class RAGAPI {
  constructor(private client: any) {}

  async query(question: string, options?: any): Promise<any> {
    return this.client.request('POST', '/v1/rag/query', { question, ...options });
  }

  async uploadFile(fileParams: any): Promise<any> {
    return this.client.request('POST', '/v1/rag/files', fileParams);
  }

  async listFiles(): Promise<any[]> {
    return this.client.request('GET', '/v1/rag/files');
  }

  async getFile(fileId: string): Promise<any> {
    return this.client.request('GET', `/v1/rag/files/${fileId}`);
  }

  async deleteFile(fileId: string): Promise<any> {
    return this.client.request('DELETE', `/v1/rag/files/${fileId}`);
  }

  async getUsage(): Promise<any> {
    return this.client.request('GET', '/v1/rag/usage');
  }

  async createCollection(collectionDef: any): Promise<any> {
    return this.client.request('POST', '/v1/rag/collections', collectionDef);
  }

  async listCollections(): Promise<any[]> {
    return this.client.request('GET', '/v1/rag/collections');
  }

  async getOverview(): Promise<any> {
    return this.client.request('GET', '/admin/rag/overview');
  }

  async listVaults(): Promise<any[]> {
    return this.client.request('GET', '/admin/rag/vaults');
  }

  async createVault(vaultDef: any): Promise<any> {
    return this.client.request('POST', '/admin/rag/vaults', vaultDef);
  }
}
