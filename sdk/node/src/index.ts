import { AgentsAPI, AgentEvalsAPI, AdminAgentsAPI } from './agents.js';
import { MemoryAPI } from './memory.js';
import { ToolsAPI } from './tools.js';
import { MarketplaceAPI } from './marketplace.js';
import { StudioAPI } from './studio.js';
import { WorkflowsAPI } from './workflows.js';
import { KnowledgeGraphAPI } from './knowledge_graph.js';
import { SessionsAPI } from './sessions.js';
import { MCPAPI } from './mcp.js';
import { DeploymentsAPI } from './deployments.js';
import { RAGAPI } from './rag.js';
import { AdminAPI } from './admin.js';
import { SystemAPI } from './system.js';

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
  public adminAgents: AdminAgentsAPI;
  public memory: MemoryAPI;
  public tools: ToolsAPI;
  public marketplace: MarketplaceAPI;
  public studio: StudioAPI;
  public workflows: WorkflowsAPI;
  public knowledgeGraph: KnowledgeGraphAPI;
  public sessions: SessionsAPI;
  public mcp: MCPAPI;
  public deployments: DeploymentsAPI;
  public rag: RAGAPI;
  public admin: AdminAPI;
  public system: SystemAPI;

  constructor(options: ClientOptions) {
    this.apiKey = options.apiKey;
    this.baseUrl = (options.baseUrl || 'http://localhost:18080').replace(/\/$/, '');
    this.timeout = options.timeout || 60000;
    this.agents = new AgentsAPI(this);
    this.agentEvals = new AgentEvalsAPI(this);
    this.adminAgents = new AdminAgentsAPI(this);
    this.memory = new MemoryAPI(this);
    this.tools = new ToolsAPI(this);
    this.marketplace = new MarketplaceAPI(this);
    this.studio = new StudioAPI(this);
    this.workflows = new WorkflowsAPI(this);
    this.knowledgeGraph = new KnowledgeGraphAPI(this);
    this.sessions = new SessionsAPI(this);
    this.mcp = new MCPAPI(this);
    this.deployments = new DeploymentsAPI(this);
    this.rag = new RAGAPI(this);
    this.admin = new AdminAPI(this);
    this.system = new SystemAPI(this);
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
      ? [{ role: 'user' as const, content: messages }]
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

  async responses(input: string | ChatMessage[], options: { model?: string; [key: string]: any } = {}): Promise<any> {
    const formattedInput = typeof input === 'string'
      ? [{ role: 'user' as const, content: input }]
      : input;
    return this.request('POST', '/v1/responses', {
      model: options.model || 'default',
      input: formattedInput,
      ...options,
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
