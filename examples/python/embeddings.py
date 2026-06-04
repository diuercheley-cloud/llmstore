import os

import requests

# Exemplo de uso do endpoint /v1/embeddings com Python

API_KEY = os.getenv("CLIENT_API_KEY", "your-api-key")
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080/v1")

def test_embeddings():
    url = f"{BASE_URL}/embeddings"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "text-embedding-3-small",
        "input": "This is a test of the local embedding system."
    }
    
    print(f"Sending request to {url}...")
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print("Success!")
        print(f"Model: {data['model']}")
        print(f"Number of embeddings: {len(data['data'])}")
        print(f"Embedding dimension: {len(data['data'][0]['embedding'])}")
        print(f"Usage: {data['usage']}")
        # print(f"First 5 values: {data['data'][0]['embedding'][:5]}")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_embeddings()
