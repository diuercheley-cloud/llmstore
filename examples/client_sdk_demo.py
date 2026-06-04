import os
import sys
from pathlib import Path

# Add scripts directory to sys.path to import the client
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR / "scripts"))

from llm_stack_client import LLMStackClient


def main():
    # In a real scenario, these would come from env vars or config
    API_KEY = os.environ.get("API_KEY", "demo-default")
    BASE_URL = os.environ.get("BASE_URL", "http://localhost:18080")

    print("--- LLM Stack Client Demo ---")
    print(f"Connecting to: {BASE_URL}")

    try:
        client = LLMStackClient(api_key=API_KEY, base_url=BASE_URL)

        # 1. List Models
        print("\n[1] Available Models:")
        models = client.list_models()
        for m in models:
            print(f" - {m.get('id')} ({m.get('alias', 'no alias')})")

        # 2. Chat Completion
        print("\n[2] Sending Chat Completion request...")
        response = client.chat_completions(
            messages=[{"role": "user", "content": "What is the capital of France?"}],
            model="unsloth/gemma-4-E4B-it-GGUF" # Adjust if needed
        )
        content = response["choices"][0]["message"]["content"]
        print(f"Response: {content}")

        # 3. Get Account Info
        print("\n[3] Account Info:")
        me = client.get_account_info()
        print(f" Name: {me.get('name')}")
        print(f" Plan: {me.get('plan', {}).get('name')}")

        # 4. Usage
        print("\n[4] Usage Statistics:")
        usage = client.get_usage()
        daily = usage.get("daily_usage", {})
        print(f" Daily Used Tokens: {daily.get('used_tokens')} / {daily.get('quota')}")

        # 5. RAG Example (if a file exists)
        test_file = Path("test_rag.txt")
        if not test_file.exists():
            test_file.write_text("The secret code is 12345. Paris is beautiful in spring.")
        
        print(f"\n[5] Uploading RAG document: {test_file}")
        try:
            upload_res = client.rag_upload(test_file)
            print(f" Upload success: {upload_res.get('original_filename')} (ID: {upload_res.get('id')})")
            
            print("\n[6] Querying RAG...")
            query_res = client.rag_query("What is the secret code?")
            print(f" Answer: {query_res.get('answer')}")
        except Exception as e:
            print(f" RAG Demo skipped or failed (is RAG enabled?): {e}")
        finally:
            if test_file.exists():
                test_file.unlink()

    except Exception as e:
        print(f"\nError: {e}")
        print("\nMake sure the stack is running and your API_KEY is correct.")

if __name__ == "__main__":
    main()
