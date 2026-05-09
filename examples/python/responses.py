import os
import requests
import json

# Configuration from environment variables
BASE_URL = os.getenv("BASE_URL", "http://localhost:18080")
API_KEY = os.getenv("CLIENT_API_KEY")

if not API_KEY:
    print("Error: CLIENT_API_KEY is not set.")
    exit(1)

def main():
    url = f"{BASE_URL}/v1/responses"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "default",
        "input": "What is the capital of France?",
        "instructions": "Be very brief.",
        "temperature": 0.5,
        "metadata": {"example": "python"},
    }

    print(f"Sending request to {url}...")
    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        print("Response received:")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    main()
