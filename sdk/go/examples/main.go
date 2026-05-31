package main

import (
	"fmt"
	"log"
	"time"

	"github.com/llm-inference-stack/sdk-go"
)

func main() {
	client := kleberai.NewClient("your-api-key", "http://localhost:18080", 30*time.Second)

	// System health
	health, err := client.System.Status()
	if err != nil {
		log.Fatalf("health check failed: %v", err)
	}
	fmt.Printf("System status: %v\n", health["status"])

	// List models
	models, err := client.Models()
	if err != nil {
		log.Fatalf("list models failed: %v", err)
	}
	fmt.Printf("Models: %d available\n", len(models))

	// Chat completion
	resp, err := client.Chat(
		[]map[string]string{{"role": "user", "content": "Hello, world!"}},
		"default",
	)
	if err != nil {
		log.Fatalf("chat failed: %v", err)
	}
	fmt.Printf("Chat response: %v\n", resp)

	// List agents
	agents, err := client.Agents.List()
	if err != nil {
		log.Fatalf("list agents failed: %v", err)
	}
	fmt.Printf("Agents: %d\n", len(agents))
}
