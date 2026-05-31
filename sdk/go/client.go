package kleberai

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

// KleberAIError represents an API error.
type KleberAIError struct {
	StatusCode int
	Body       string
}

func (e *KleberAIError) Error() string {
	return fmt.Sprintf("kleberai: HTTP %d - %s", e.StatusCode, e.Body)
}

// Client is the Kleber AI API client.
type Client struct {
	apiKey  string
	baseURL string
	http    *http.Client

	Agents        *AgentsAPI
	AgentEvals    *AgentEvalsAPI
	AdminAgents   *AdminAgentsAPI
	Memory        *MemoryAPI
	Tools         *ToolsAPI
	Marketplace   *MarketplaceAPI
	Studio        *StudioAPI
	Workflows     *WorkflowsAPI
	KnowledgeGraph *KnowledgeGraphAPI
	Sessions      *SessionsAPI
	MCP           *MCPAPI
	Deployments   *DeploymentsAPI
	RAG           *RAGAPI
	Admin         *AdminAPI
	System        *SystemAPI
}

// NewClient creates a new Kleber AI API client.
func NewClient(apiKey, baseURL string, timeout time.Duration) *Client {
	if baseURL == "" {
		baseURL = "http://localhost:18080"
	}
	if timeout == 0 {
		timeout = 60 * time.Second
	}
	c := &Client{
		apiKey:  apiKey,
		baseURL: baseURL,
		http: &http.Client{Timeout: timeout},
	}
	c.Agents = &AgentsAPI{client: c}
	c.AgentEvals = &AgentEvalsAPI{client: c}
	c.AdminAgents = &AdminAgentsAPI{client: c}
	c.Memory = &MemoryAPI{client: c}
	c.Tools = &ToolsAPI{client: c}
	c.Marketplace = &MarketplaceAPI{client: c}
	c.Studio = &StudioAPI{client: c}
	c.Workflows = &WorkflowsAPI{client: c}
	c.KnowledgeGraph = &KnowledgeGraphAPI{client: c}
	c.Sessions = &SessionsAPI{client: c}
	c.MCP = &MCPAPI{client: c}
	c.Deployments = &DeploymentsAPI{client: c}
	c.RAG = &RAGAPI{client: c}
	c.Admin = &AdminAPI{client: c}
	c.System = &SystemAPI{client: c}
	return c
}

func (c *Client) request(method, path string, body interface{}) ([]byte, error) {
	var reqBody io.Reader
	if body != nil {
		data, err := json.Marshal(body)
		if err != nil {
			return nil, fmt.Errorf("kleberai: marshal request: %w", err)
		}
		reqBody = bytes.NewReader(data)
	}

	req, err := http.NewRequest(method, c.baseURL+path, reqBody)
	if err != nil {
		return nil, fmt.Errorf("kleberai: create request: %w", err)
	}
	req.Header.Set("Authorization", "Bearer "+c.apiKey)
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.http.Do(req)
	if err != nil {
		return nil, fmt.Errorf("kleberai: execute request: %w", err)
	}
	defer resp.Body.Close()

	respData, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("kleberai: read response: %w", err)
	}

	if resp.StatusCode >= 400 {
		return nil, &KleberAIError{StatusCode: resp.StatusCode, Body: string(respData)}
	}
	return respData, nil
}

// Chat sends a chat completion request.
func (c *Client) Chat(messages interface{}, model string, opts ...map[string]interface{}) (map[string]interface{}, error) {
	payload := map[string]interface{}{
		"model":    model,
		"messages": messages,
	}
	for _, opt := range opts {
		for k, v := range opt {
			payload[k] = v
		}
	}
	data, err := c.request("POST", "/v1/chat/completions", payload)
	if err != nil {
		return nil, err
	}
	var result map[string]interface{}
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, fmt.Errorf("kleberai: unmarshal response: %w", err)
	}
	return result, nil
}

// Models lists available models.
func (c *Client) Models() ([]map[string]interface{}, error) {
	data, err := c.request("GET", "/v1/models", nil)
	if err != nil {
		return nil, err
	}
	var result struct {
		Data []map[string]interface{} `json:"data"`
	}
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, fmt.Errorf("kleberai: unmarshal response: %w", err)
	}
	return result.Data, nil
}

// Embeddings generates embeddings for the given input.
func (c *Client) Embeddings(input interface{}, model string) (map[string]interface{}, error) {
	payload := map[string]interface{}{
		"model": model,
		"input": input,
	}
	data, err := c.request("POST", "/v1/embeddings", payload)
	if err != nil {
		return nil, err
	}
	var result map[string]interface{}
	if err := json.Unmarshal(data, &result); err != nil {
		return nil, fmt.Errorf("kleberai: unmarshal response: %w", err)
	}
	return result, nil
}
