import json
import os

import requests

# Configuration from environment variables
BASE_URL = os.getenv("BASE_URL", "http://localhost:18080")
API_KEY = os.getenv("CLIENT_API_KEY")

if not API_KEY:
    print("Error: CLIENT_API_KEY is not set.")
    exit(1)


def main():
    url = f"{BASE_URL}/v1/chat/completions"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "default",
        "messages": [
            {"role": "user", "content": "Tell me a story about a brave robot in 3 paragraphs."}
        ],
        "stream": True,
        "temperature": 0.7,
    }

    print(f"Sending streaming request to {url}...")
    response = requests.post(url, headers=headers, json=data, stream=True)

    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        return

    print("Response stream:")
    for line in response.iter_lines():
        if line:
            line_str = line.decode("utf-8")
            if line_str.startswith("data: "):
                content = line_str[6:]
                if content == "[DONE]":
                    break
                try:
                    chunk = json.loads(content)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    if "content" in delta:
                        print(delta["content"], end="", flush=True)
                except json.JSONDecodeError:
                    pass
    print("\nStream finished.")


if __name__ == "__main__":
    main()
