import { AgentsAPI, AgentEvalsAPI } from './agents';

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string;
}

export interface ClientOptions {
  apiKey: string;
  baseUrl?: string;
  timeout?: number;
}

export class KleberAIError extends Error {
  constructor(message: string, public statusCode?: number, public body?: any) {
    super(message);
    this.name = 'KleberAIError';
  }
}

export class Client {
  private apiKey: string;
  private baseUrl: string;
  private timeout: number;
  public agents: AgentsAPI;
  public agentEvals: AgentEvalsAPI;

  constructor(options: ClientOptions) {
    this.apiKey = options.apiKey;
    this.baseUrl = (options.baseUrl || 'http://localhost:18080').replace(/\/$/, '');
    this.timeout = options.timeout || 60000;
    this.agents = new AgentsAPI(this);
    this.agentEvals = new AgentEvalsAPI(this);
  }

  private async request(method: string, path: string, body?: any): Promise<any> {
    const url = `${this.baseUrl}${path}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        method,
        headers: {
          'Authorization': `Bearer ${this.apiKey}`,
          'Content-Type': 'application/json',
        },
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({}));
        throw new KleberAIError(
          `HTTP error: ${response.status}`,
          response.status,
          errorBody
        );
      }

      return await response.json();
    } catch (error: any) {
      clearTimeout(timeoutId);
      if (error.name === 'AbortError') {
        throw new KleberAIError('Request timeout');
      }
      if (error instanceof KleberAIError) throw error;
      throw new KleberAIError(`Request failed: ${error.message}`);
    }
  }

  async chat(messages: string | ChatMessage[], options: { model?: string; [key: string]: any } = {}): Promise<any> {
    const formattedMessages = typeof messages === 'string' 
      ? [{ role: 'user', content: messages }] 
      : messages;

    return this.request('POST', '/v1/chat/completions', {
      model: options.model || 'default',
      messages: formattedMessages,
      ...options,
    });
  }

  async models(): Promise<any[]> {
    const response = await this.request('GET', '/v1/models');
    return response.data || [];
  }

  async embeddings(input: string | string[], model: string = 'default'): Promise<any> {
    const formattedInput = typeof input === 'string' ? [input] : input;
    return this.request('POST', '/v1/embeddings', {
      input: formattedInput,
      model,
    });
  }

  async ragQuery(question: string, fileIds?: string[], options: { model?: string; [key: string]: any } = {}): Promise<any> {
    return this.request('POST', '/client/rag/query', {
      question,
      file_ids: fileIds,
      model: options.model || 'default',
      ...options,
    });
  }
}
