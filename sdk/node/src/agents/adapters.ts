export interface AdapterManifest {
  id: string;
  name: string;
  version: string;
  compatibility_version: string;
  description?: string;
  author?: string;
  metadata: Record<string, any>;
  permissions: string[];
}

export abstract class AdapterABI {
  abstract manifest(): Promise<AdapterManifest>;
  abstract schema(): Promise<Record<string, any>>;
  abstract healthcheck(): Promise<boolean>;
  abstract dry_run(params: Record<string, any>): Promise<[boolean, string]>;
}

export abstract class ToolAdapterV1 extends AdapterABI {
  abstract execute(
    toolInput: Record<string, any>,
    context: Record<string, any>
  ): Promise<Record<string, any>>;
}

export abstract class MemoryProviderV1 extends AdapterABI {
  abstract store(
    agentId: string,
    runId: string,
    item: Record<string, any>
  ): Promise<boolean>;

  abstract retrieve(
    agentId: string,
    query: string,
    limit?: number
  ): Promise<Record<string, any>[]>;
}

export abstract class EvalProviderV1 extends AdapterABI {
  abstract evaluate(
    runId: string,
    criteria: string[]
  ): Promise<Record<string, any>>;
}

export abstract class PlannerProviderV1 extends AdapterABI {
  abstract plan(
    goal: string,
    availableTools: string[],
    history: Record<string, any>[]
  ): Promise<Record<string, any>>;
}
