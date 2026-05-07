import os
import requests
import json
import sys

# Configuration from environment variables
BASE_URL = os.getenv("BASE_URL", "http://localhost:18080")
API_KEY = os.getenv("CLIENT_API_KEY")

if not API_KEY:
    print("Error: CLIENT_API_KEY is not set.")
    exit(1)

def main():
    question = sys.argv[1] if len(sys.argv) > 1 else "What is in the uploaded documents?"
    
    url = f"{BASE_URL}/v1/rag/query"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "question": question,
        "model": "default",
        "top_k": 3,
        "max_tokens": 500,
        "temperature": 0.2
    }

    print(f"Sending RAG query to {url}...")
    print(f"Question: {question}")
    
    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        result = response.json()
        print("\nAnswer:")
        print(result.get("answer"))
        
        print("\nSources:")
        for source in result.get("sources", []):
            print(f"- {source['filename']} (Page {source['page']}, Score: {source['score']:.4f})")
            
        usage = result.get("usage", {})
        print(f"\nUsage: {usage.get('total_tokens')} tokens")
    elif response.status_code == 403:
        print("Error: RAG is disabled or feature blocked.")
        print(response.text)
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    main()
