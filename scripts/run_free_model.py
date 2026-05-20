#!/usr/bin/env python3
import json
import os
import sys
import subprocess
import urllib.request
import urllib.error
import uuid

# Helper functions to load and save keys in untracked .env.local
def load_env_val(key_name):
    # 1. Check OS environment first
    val = os.environ.get(key_name)
    if val:
        return val
        
    # 2. Check .env.local or .env in the project root
    for filename in [".env.local", ".env"]:
        if os.path.exists(filename):
            try:
                with open(filename, "r") as f:
                    for line in f:
                        if line.strip().startswith(f"{key_name}="):
                            raw_val = line.strip().split("=", 1)[1]
                            if raw_val.startswith('"') and raw_val.endswith('"'):
                                raw_val = raw_val[1:-1]
                            elif raw_val.startswith("'") and raw_val.endswith("'"):
                                raw_val = raw_val[1:-1]
                            return raw_val
            except Exception:
                pass
    return None

def save_env_val(key_name, value):
    # Save to .env.local (which is in .gitignore)
    filename = ".env.local"
    lines = []
    updated = False
    
    if os.path.exists(filename):
        try:
            with open(filename, "r") as f:
                for line in f:
                    if line.strip().startswith(f"{key_name}="):
                        lines.append(f"{key_name}={value}\n")
                        updated = True
                    else:
                        lines.append(line)
        except Exception:
            pass
            
    if not updated:
        lines.append(f"\n# Added by run_free_model utility script\n{key_name}={value}\n")
        
    try:
        with open(filename, "w") as f:
            f.writelines(lines)
        print(f"Saved {key_name} to .env.local for future runs.")
    except Exception as e:
        print(f"Warning: Could not save {key_name} to .env.local: {e}")

# Securely load configuration keys
OPENROUTER_KEY = load_env_val("OPENROUTER_API_KEY")
if not OPENROUTER_KEY:
    print("OpenRouter API Key not found in environment or .env.local.")
    OPENROUTER_KEY = input("Please paste your OpenRouter API Key (sk-or-...): ").strip()
    if OPENROUTER_KEY:
        save_env_val("OPENROUTER_API_KEY", OPENROUTER_KEY)
    else:
        print("Error: OpenRouter API key is required.")
        sys.exit(1)

LOCAL_API_KEY = load_env_val("LOCAL_API_KEY")
if not LOCAL_API_KEY:
    print("Local Gateway API Key not found in environment or .env.local.")
    LOCAL_API_KEY = input("Please paste your Local Gateway API Key (sk-local-...): ").strip()
    if LOCAL_API_KEY:
        save_env_val("LOCAL_API_KEY", LOCAL_API_KEY)
    else:
        print("Error: Local API key is required.")
        sys.exit(1)

LOCAL_URL = "http://localhost:18080/v1/chat/completions"

def get_admin_token():
    """Gets the admin token dynamically from the running control-plane container."""
    cmd = [
        "docker", "exec", "-i", "llm-inference-stack-control-plane-1",
        "env"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        for line in res.stdout.splitlines():
            if line.strip().startswith("ADMIN_TOKEN="):
                return line.strip().split("=", 1)[1].strip()
    return None

def reload_gateway_cache(admin_token):
    """Triggers a model cache reload on the local gateway."""
    if not admin_token:
        print("Warning: Skipping gateway cache reload (no Admin Token available).", file=sys.stderr)
        return False
    print("Triggering control-plane model cache reload...")
    url = "http://localhost:18080/admin/models/reload"
    req = urllib.request.Request(
        url,
        headers={"X-Admin-Token": admin_token},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode())
            print(f"Gateway cache reload status: {res_data.get('status', 'unknown')} - {res_data.get('detail', '')}")
            return True
    except Exception as e:
        print(f"Warning: Failed to trigger model cache reload: {e}", file=sys.stderr)
        return False

# Securely load admin token key
ADMIN_TOKEN = load_env_val("ADMIN_TOKEN")
if not ADMIN_TOKEN:
    print("Admin Token not found in environment or .env.local. Attempting docker environment discovery...")
    ADMIN_TOKEN = get_admin_token()
    if ADMIN_TOKEN:
        save_env_val("ADMIN_TOKEN", ADMIN_TOKEN)
    else:
        print("Warning: Could not dynamically discover ADMIN_TOKEN from control-plane container.")
        ADMIN_TOKEN = input("Please paste your Admin Token (optional, press Enter to skip): ").strip()
        if ADMIN_TOKEN:
            save_env_val("ADMIN_TOKEN", ADMIN_TOKEN)

def run_sql(query):
    """Executes a SQL query in the local postgres container and returns the output."""
    cmd = [
        "docker", "exec", "-i", "llm-inference-stack-postgres-1",
        "psql", "-U", "llm_gateway", "-d", "llm_gateway", "-t", "-A", "-c", query
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error running database query: {res.stderr}", file=sys.stderr)
        return []
    return [line.strip() for line in res.stdout.strip().split("\n") if line.strip()]

def fetch_free_models():
    """Fetches free models from OpenRouter."""
    print("Fetching models from OpenRouter...")
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/models",
        headers={"Authorization": f"Bearer {OPENROUTER_KEY}"}
    )
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
    except Exception as e:
        print(f"Failed to fetch models from OpenRouter: {e}", file=sys.stderr)
        sys.exit(1)

    free_models = []
    for model in data.get("data", []):
        pricing = model.get("pricing", {})
        prompt_price = pricing.get("prompt", "?")
        completion_price = pricing.get("completion", "?")
        # Identify free models
        try:
            if float(prompt_price) == 0.0 and float(completion_price) == 0.0:
                free_models.append(model["id"])
        except ValueError:
            if prompt_price == "0" and completion_price == "0":
                free_models.append(model["id"])
                
    return sorted(free_models)

def register_model_if_needed(model_id):
    """Checks database for the model and registers it if not present, healing fields if necessary."""
    # Get OpenRouter backend ID
    backend_query = "SELECT id FROM inference_backends WHERE provider = 'openrouter' AND is_active = true LIMIT 1;"
    backend_rows = run_sql(backend_query)
    if not backend_rows:
        print("Error: Active OpenRouter backend not found in inference_backends database.", file=sys.stderr)
        sys.exit(1)
    backend_id = backend_rows[0].strip()
    
    # Check if already registered
    check_query = f"SELECT id, inference_backend_id FROM model_registry WHERE model_id = '{model_id}';"
    rows = run_sql(check_query)
    
    modified = False
    
    if rows:
        parts = rows[0].split("|")
        model_uuid = parts[0].strip()
        existing_backend_id = parts[1].strip() if len(parts) > 1 else ""
        
        print(f"Model '{model_id}' is already registered (ID: {model_uuid}).")
        
        # Self-healing for inference_backend_id in model_registry
        if not existing_backend_id or existing_backend_id != backend_id:
            print(f"Updating inference_backend_id in model_registry to active OpenRouter backend ({backend_id})...")
            update_query = f"""
            UPDATE model_registry 
            SET inference_backend_id = '{backend_id}', updated_at = now() 
            WHERE id = '{model_uuid}';
            """
            run_sql(update_query)
            modified = True
            
        # Check if route is missing in model_backend_routes
        route_query = f"SELECT id FROM model_backend_routes WHERE model_registry_id = '{model_uuid}' AND inference_backend_id = '{backend_id}';"
        route_rows = run_sql(route_query)
        if not route_rows:
            print("Backend route missing in model_backend_routes. Adding backend route...")
            route_uuid = str(uuid.uuid4())
            insert_route = f"""
            INSERT INTO model_backend_routes (id, model_registry_id, inference_backend_id, priority, weight, state, created_at, updated_at)
            VALUES ('{route_uuid}', '{model_uuid}', '{backend_id}', 1, 100, 'healthy', now(), now());
            """
            run_sql(insert_route)
            modified = True
            
        if modified:
            print("Self-healing updates completed successfully.")
    else:
        print(f"Model '{model_id}' not found in registry. Registering dynamically...")
        model_uuid = str(uuid.uuid4())
        route_uuid = str(uuid.uuid4())
        alias = model_id.split("/")[-1].replace(":free", "")
        
        # Insert into model_registry with inference_backend_id
        insert_model = f"""
        INSERT INTO model_registry (id, model_id, model_alias, inference_backend_id, provider, model_file, is_active, is_default, context_length, created_at, updated_at)
        VALUES ('{model_uuid}', '{model_id}', '{alias}', '{backend_id}', 'openrouter', '{model_id}', true, false, 8192, now(), now());
        """
        run_sql(insert_model)
        
        # Insert into model_backend_routes
        insert_route = f"""
        INSERT INTO model_backend_routes (id, model_registry_id, inference_backend_id, priority, weight, state, created_at, updated_at)
        VALUES ('{route_uuid}', '{model_uuid}', '{backend_id}', 1, 100, 'healthy', now(), now());
        """
        run_sql(insert_route)
        modified = True
        print(f"Successfully registered '{model_id}' with alias '{alias}' in local gateway!")
        
    # Always reload gateway cache if modified
    if modified:
        reload_gateway_cache(ADMIN_TOKEN)

def call_local_gateway(model_id, prompt):
    """Sends a chat completions request to the local gateway."""
    print(f"\nSending chat completion request for model '{model_id}' to local gateway...")
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}]
    }
    data_bytes = json.dumps(payload).encode("utf-8")
    
    req = urllib.request.Request(
        LOCAL_URL,
        data=data_bytes,
        headers={
            "Authorization": f"Bearer {LOCAL_API_KEY}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode())
            print("\nResponse from local gateway (formatted):")
            print(json.dumps(res_data, indent=2, ensure_ascii=False))
    except urllib.error.HTTPError as e:
        print(f"\nHTTP Error from gateway: {e.code} - {e.reason}", file=sys.stderr)
        try:
            error_body = json.loads(e.read().decode())
            print(json.dumps(error_body, indent=2, ensure_ascii=False), file=sys.stderr)
        except Exception:
            pass
    except Exception as e:
        print(f"\nFailed to communicate with local gateway: {e}", file=sys.stderr)

def main():
    free_models = fetch_free_models()
    if not free_models:
        print("No free models found on OpenRouter.")
        return
        
    print("\n--- Available Free OpenRouter Models ---")
    for i, model in enumerate(free_models, 1):
        print(f"[{i:2d}] {model}")
        
    while True:
        try:
            selection = input(f"\nSelect a model by number (1-{len(free_models)}): ")
            idx = int(selection) - 1
            if 0 <= idx < len(free_models):
                selected_model = free_models[idx]
                break
            else:
                print("Invalid number. Please try again.")
        except ValueError:
            print("Please enter a valid integer.")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            sys.exit(0)
            
    print(f"\nYou selected: {selected_model}")
    
    # Ensure registered in local DB
    register_model_if_needed(selected_model)
    
    # Prompt user for question
    default_prompt = f"O que é o modelo {selected_model.split('/')[-1]}?"
    user_prompt = input(f"\nEnter prompt (default: '{default_prompt}'): ").strip()
    if not user_prompt:
        user_prompt = default_prompt
        
    # Execute query
    call_local_gateway(selected_model, user_prompt)

if __name__ == "__main__":
    main()
