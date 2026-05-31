export class MarketplaceAPI {
  constructor(private client: any) {}

  async listItems(): Promise<any[]> {
    return this.client.request('GET', '/v1/marketplace/items');
  }

  async publishItem(item: any): Promise<any> {
    return this.client.request('POST', '/v1/marketplace/items', item);
  }

  async getItem(itemId: string): Promise<any> {
    return this.client.request('GET', `/v1/marketplace/items/${itemId}`);
  }

  async rateItem(itemId: string, rating: any): Promise<any> {
    return this.client.request('POST', `/v1/marketplace/items/${itemId}/rate`, rating);
  }

  async listReviews(itemId: string): Promise<any[]> {
    return this.client.request('GET', `/v1/marketplace/items/${itemId}/reviews`);
  }

  async listCategories(): Promise<any[]> {
    return this.client.request('GET', '/v1/marketplace/categories');
  }

  async registerPublisher(info: any): Promise<any> {
    return this.client.request('POST', '/v1/marketplace/publishers/register', info);
  }

  async adminList(): Promise<any[]> {
    return this.client.request('GET', '/admin/agent-marketplace');
  }

  async adminInstall(installRequest: any): Promise<any> {
    return this.client.request('POST', '/admin/agent-marketplace/install', installRequest);
  }
}
