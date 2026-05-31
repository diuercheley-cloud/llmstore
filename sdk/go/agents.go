package kleberai

import "encoding/json"

// AgentsAPI provides access to agent endpoints.
type AgentsAPI struct{ client *Client }

func (a *AgentsAPI) List() ([]map[string]interface{}, error) {
	data, err := a.client.request("GET", "/v1/agents", nil)
	if err != nil {
		return nil, err
	}
	var result []map[string]interface{}
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, err
	}
	return result, nil
}

func (a *AgentsAPI) Get(id string) (map[string]interface{}, error) {
	data, err := a.client.request("GET", "/v1/agents/"+id, nil)
	if err != nil {
		return nil, err
	}
	var result map[string]interface{}
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, err
	}
	return result, nil
}

func (a *AgentsAPI) Create(agent map[string]interface{}) (map[string]interface{}, error) {
	data, err := a.client.request("POST", "/v1/agents", agent)
	if err != nil {
		return nil, err
	}
	var result map[string]interface{}
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, err
	}
	return result, nil
}

func (a *AgentsAPI) GetRuns(id string) ([]map[string]interface{}, error) {
	data, err := a.client.request("GET", "/v1/agents/"+id+"/runs", nil)
	if err != nil {
		return nil, err
	}
	var result []map[string]interface{}
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// AgentEvalsAPI provides access to agent evaluation endpoints.
type AgentEvalsAPI struct{ client *Client }

func (a *AgentEvalsAPI) List() ([]map[string]interface{}, error) {
	data, err := a.client.request("GET", "/admin/agents/evals", nil)
	if err != nil {
		return nil, err
	}
	var result []map[string]interface{}
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// AdminAgentsAPI provides access to admin agent endpoints.
type AdminAgentsAPI struct{ client *Client }

func (a *AdminAgentsAPI) List() ([]map[string]interface{}, error) {
	data, err := a.client.request("GET", "/admin/agents", nil)
	if err != nil {
		return nil, err
	}
	var result []map[string]interface{}
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// MemoryAPI provides access to agent memory endpoints.
type MemoryAPI struct{ client *Client }

func (m *MemoryAPI) List() ([]map[string]interface{}, error) {
	data, err := m.client.request("GET", "/v1/memory", nil)
	if err != nil {
		return nil, err
	}
	var result []map[string]interface{}
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// ToolsAPI provides access to tool endpoints.
type ToolsAPI struct{ client *Client }

func (t *ToolsAPI) List() ([]map[string]interface{}, error) {
	data, err := t.client.request("GET", "/v1/tools", nil)
	if err != nil {
		return nil, err
	}
	var result []map[string]interface{}
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// MarketplaceAPI provides access to agent marketplace endpoints.
type MarketplaceAPI struct{ client *Client }

func (m *MarketplaceAPI) List() ([]map[string]interface{}, error) {
	data, err := m.client.request("GET", "/v1/marketplace/agents", nil)
	if err != nil {
		return nil, err
	}
	var result []map[string]interface{}
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// StudioAPI provides access to agent studio endpoints.
type StudioAPI struct{ client *Client }

func (s *StudioAPI) ListFlows() ([]map[string]interface{}, error) {
	data, err := s.client.request("GET", "/admin/agents/studio/flows", nil)
	if err != nil {
		return nil, err
	}
	var result []map[string]interface{}
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, err
	}
	return result, nil
}

func (s *StudioAPI) CreateFlow(flow map[string]interface{}) (map[string]interface{}, error) {
	data, err := s.client.request("POST", "/admin/agents/studio/flows", flow)
	if err != nil {
		return nil, err
	}
	var result map[string]interface{}
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// WorkflowsAPI provides access to workflow endpoints.
type WorkflowsAPI struct{ client *Client }

func (w *WorkflowsAPI) List() ([]map[string]interface{}, error) {
	data, err := w.client.request("GET", "/v1/workflows", nil)
	if err != nil {
		return nil, err
	}
	var result []map[string]interface{}
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// KnowledgeGraphAPI provides access to knowledge graph endpoints.
type KnowledgeGraphAPI struct{ client *Client }

func (k *KnowledgeGraphAPI) Query(query map[string]interface{}) (map[string]interface{}, error) {
	data, err := k.client.request("POST", "/v1/knowledge-graph/query", query)
	if err != nil {
		return nil, err
	}
	var result map[string]interface{}
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// SessionsAPI provides access to agent session endpoints.
type SessionsAPI struct{ client *Client }

func (s *SessionsAPI) List() ([]map[string]interface{}, error) {
	data, err := s.client.request("GET", "/v1/sessions", nil)
	if err != nil {
		return nil, err
	}
	var result []map[string]interface{}
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// MCPAPI provides access to MCP tool endpoints.
type MCPAPI struct{ client *Client }

func (m *MCPAPI) ListTools() ([]map[string]interface{}, error) {
	data, err := m.client.request("GET", "/v1/mcp/tools", nil)
	if err != nil {
		return nil, err
	}
	var result []map[string]interface{}
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// DeploymentsAPI provides access to agent deployment endpoints.
type DeploymentsAPI struct{ client *Client }

func (d *DeploymentsAPI) List() ([]map[string]interface{}, error) {
	data, err := d.client.request("GET", "/v1/deployments", nil)
	if err != nil {
		return nil, err
	}
	var result []map[string]interface{}
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// RAGAPI provides access to RAG endpoints.
type RAGAPI struct{ client *Client }

func (r *RAGAPI) ListCollections() ([]map[string]interface{}, error) {
	data, err := r.client.request("GET", "/v1/rag/collections", nil)
	if err != nil {
		return nil, err
	}
	var result []map[string]interface{}
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, err
	}
	return result, nil
}

func (r *RAGAPI) CreateCollection(collection map[string]interface{}) (map[string]interface{}, error) {
	data, err := r.client.request("POST", "/v1/rag/collections", collection)
	if err != nil {
		return nil, err
	}
	var result map[string]interface{}
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// AdminAPI provides access to admin endpoints.
type AdminAPI struct{ client *Client }

func (a *AdminAPI) ListModels() ([]map[string]interface{}, error) {
	data, err := a.client.request("GET", "/admin/models", nil)
	if err != nil {
		return nil, err
	}
	var result []map[string]interface{}
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, err
	}
	return result, nil
}

func (a *AdminAPI) ListClients() ([]map[string]interface{}, error) {
	data, err := a.client.request("GET", "/admin/clients", nil)
	if err != nil {
		return nil, err
	}
	var result []map[string]interface{}
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, err
	}
	return result, nil
}

func (a *AdminAPI) ListApiKeys() ([]map[string]interface{}, error) {
	data, err := a.client.request("GET", "/admin/api-keys", nil)
	if err != nil {
		return nil, err
	}
	var result []map[string]interface{}
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, err
	}
	return result, nil
}

func (a *AdminAPI) Health() (map[string]interface{}, error) {
	data, err := a.client.request("GET", "/health", nil)
	if err != nil {
		return nil, err
	}
	var result map[string]interface{}
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, err
	}
	return result, nil
}

// SystemAPI provides access to system endpoints.
type SystemAPI struct{ client *Client }

func (s *SystemAPI) Status() (map[string]interface{}, error) {
	data, err := s.client.request("GET", "/status", nil)
	if err != nil {
		return nil, err
	}
	var result map[string]interface{}
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, err
	}
	return result, nil
}

func (s *SystemAPI) Ready() (map[string]interface{}, error) {
	data, err := s.client.request("GET", "/ready", nil)
	if err != nil {
		return nil, err
	}
	var result map[string]interface{}
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, err
	}
	return result, nil
}
