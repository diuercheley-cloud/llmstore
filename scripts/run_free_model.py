#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
import uuid


# Helper functions to load and save keys in untracked .env.local
def load_env_val(key_name):
    # 1. Check OS environment first
    val = os.environ.get(key_name)
    if val:
        return val
        
    # 2. Check env files
    for filename in [".env.local", ".env", ".local/demo-client.env", ".local/demo-commercial-clients.env"]:
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

GATEWAY_BASE_URL = "http://localhost:18080"

def get_openrouter_key():
    key = load_env_val("OPENROUTER_API_KEY")
    if key:
        masked = f"{key[:10]}...{key[-5:]}" if len(key) > 15 else key
        print(f"\nCurrent OpenRouter API Key: {masked}")
        new_key = input("Enter new OpenRouter API Key (press Enter to keep current): ").strip()
        if new_key:
            key = new_key
            save_env_val("OPENROUTER_API_KEY", key)
    else:
        print("\nOpenRouter API Key not found in environment or .env.local.")
        key = input("Please paste your OpenRouter API Key (sk-or-...): ").strip()
        if key:
            save_env_val("OPENROUTER_API_KEY", key)
        else:
            print("Error: OpenRouter API key is required.")
            sys.exit(1)
    return key

def get_nvidia_key():
    key = load_env_val("NVIDIA_API_KEY")
    default_nv_key = "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"
    if key:
        masked = f"{key[:10]}...{key[-5:]}" if len(key) > 15 else key
        print(f"\nCurrent Nvidia API Key: {masked}")
        new_key = input("Enter new Nvidia API Key (press Enter to keep current): ").strip()
        if new_key:
            key = new_key
            save_env_val("NVIDIA_API_KEY", key)
    else:
        print("\nNvidia API Key not found in environment or .env.local.")
        print(f"Default Nvidia key: {default_nv_key[:10]}...{default_nv_key[-10:]}")
        new_key = input("Enter custom Nvidia API Key (press Enter to use default): ").strip()
        if new_key:
            key = new_key
            save_env_val("NVIDIA_API_KEY", key)
        else:
            key = default_nv_key
            save_env_val("NVIDIA_API_KEY", key)
    return key

def get_available_client_keys():
    keys = {}
    files_to_scan = [
        ".env.local",
        ".env",
        ".local/demo-client.env",
        ".local/demo-commercial-clients.env"
    ]
    
    # 1. From environment variables
    for k, v in os.environ.items():
        if (k.endswith("API_KEY") or k == "API_KEY") and v.startswith("sk-local-"):
            name = k.replace("_API_KEY", "").replace("DEMO_CLIENT_", "").replace("DEMO_", "").replace("LOCAL_", "").replace("_", " ").title()
            keys[name] = v
            
    # 2. From files
    for filename in files_to_scan:
        if os.path.exists(filename):
            try:
                with open(filename, "r") as f:
                    for line in f:
                        line = line.strip()
                        if "=" in line and not line.startswith("#"):
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip()
                            if v.startswith('"') and v.endswith('"'):
                                v = v[1:-1]
                            elif v.startswith("'") and v.endswith("'"):
                                v = v[1:-1]
                            if v.startswith("sk-local-"):
                                name = k.replace("_API_KEY", "").replace("DEMO_CLIENT_", "").replace("DEMO_", "").replace("LOCAL_", "").replace("_", " ").title()
                                if name not in keys:
                                    keys[name] = v
            except Exception:
                pass
                
    return keys

def get_gateway_base_url():
    url = load_env_val("BASE_URL") or load_env_val("GATEWAY_BASE_URL")
    if not url:
        url = "http://localhost:18080"
    print(f"Using Gateway Base URL: {url}")
    return url

def get_client_api_key():
    while True:
        try:
            print("\n--- Client API Key ---")
            key = input("Please paste your Client API Key (sk-local-...): ").strip()
            if key:
                save_env_val("CLIENT_API_KEY", key)
                return key
            print("Error: Client API key is required.")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            sys.exit(0)

def get_local_api_key():
    return get_client_api_key()

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

def get_admin_token_cached():
    token = load_env_val("ADMIN_TOKEN")
    if not token:
        print("Admin Token not found in environment or .env.local. Attempting docker environment discovery...")
        token = get_admin_token()
        if token:
            save_env_val("ADMIN_TOKEN", token)
        else:
            print("Warning: Could not dynamically discover ADMIN_TOKEN from control-plane container.")
            token = input("Please paste your Admin Token (optional, press Enter to skip): ").strip()
            if token:
                save_env_val("ADMIN_TOKEN", token)
    return token

def reload_gateway_cache(admin_token):
    """Triggers a model cache reload on the local gateway."""
    if not admin_token:
        print("Warning: Skipping gateway cache reload (no Admin Token available).", file=sys.stderr)
        return False
    print("Triggering control-plane model cache reload...")
    url = f"{GATEWAY_BASE_URL.rstrip('/')}/admin/models/reload"
    req = urllib.request.Request(
        url,
        headers={"X-Admin-Token": admin_token},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            res_data = json.loads(response.read().decode())
            print(f"Gateway cache reload status: {res_data.get('status', 'unknown')} - {res_data.get('detail', '')}")
            return True
    except Exception as e:
        print(f"Warning: Failed to trigger model cache reload: {e}", file=sys.stderr)
        return False

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

def fetch_openrouter_free_models(api_key):
    """Fetches free models from OpenRouter."""
    print("Fetching models from OpenRouter...")
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/models",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
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
                
    return sorted(list(set(free_models)))

def fetch_nvidia_models(api_key):
    """Fetches models from Nvidia API."""
    print("Fetching models from Nvidia...")
    req = urllib.request.Request(
        "https://integrate.api.nvidia.com/v1/models",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            data = json.loads(response.read().decode())
    except Exception as e:
        print(f"Failed to fetch models from Nvidia: {e}", file=sys.stderr)
        sys.exit(1)

    models = []
    for model in data.get("data", []):
        if "id" in model:
            models.append(model["id"])
                
    return sorted(list(set(models)))

def register_nvidia_backend_if_needed(nvidia_key, admin_token):
    check_query = "SELECT id, metadata_json FROM inference_backends WHERE name = 'nvidia-cloud';"
    rows = run_sql(check_query)
    backend_id = None
    
    expected_metadata = json.dumps({"api_key": nvidia_key})
    
    if rows:
        parts = rows[0].split("|")
        backend_id = parts[0].strip()
        existing_metadata = parts[1].strip() if len(parts) > 1 else ""
        
        try:
            meta_data = json.loads(existing_metadata) if existing_metadata else {}
            if meta_data.get("api_key") != nvidia_key:
                print("Updating Nvidia API Key in inference_backends...")
                safe_metadata = expected_metadata.replace("'", "''")
                update_query = f"""
                UPDATE inference_backends
                SET metadata_json = '{safe_metadata}', updated_at = now()
                WHERE id = '{backend_id}';
                """
                run_sql(update_query)
                reload_gateway_cache(admin_token)
        except Exception as e:
            print(f"Warning: could not parse metadata: {e}")
    else:
        backend_id = str(uuid.uuid4())
        print("Registering nvidia-cloud backend in database...")
        safe_metadata = expected_metadata.replace("'", "''")
        insert_query = f"""
        INSERT INTO inference_backends (
            id, name, provider, backend_url, healthcheck_path, is_active, is_default, status, max_parallel_requests, current_running, metadata_json, created_at, updated_at
        ) VALUES (
            '{backend_id}', 'nvidia-cloud', 'openai_compatible', 'https://integrate.api.nvidia.com', '/v1/models', true, false, 'configured', 10, 0, '{safe_metadata}', now(), now()
        );
        """
        run_sql(insert_query)
        reload_gateway_cache(admin_token)
        
    return backend_id

def fetch_custom_models(backend_url, api_key):
    """Fetches models from a custom OpenAI-compatible API URL."""
    if "/v1" in backend_url:
        models_url = backend_url.rstrip("/") + "/models"
    else:
        models_url = backend_url.rstrip("/") + "/v1/models"

    print(f"Fetching models from custom URL: {models_url}...")
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    req = urllib.request.Request(
        models_url,
        headers=headers
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            data = json.loads(response.read().decode())
    except Exception as e:
        if "/v1/models" in models_url:
            alt_url = backend_url.rstrip("/") + "/models"
            print(f"Failed with /v1/models. Retrying with alternate URL: {alt_url}...")
            try:
                req = urllib.request.Request(alt_url, headers=headers)
                with urllib.request.urlopen(req, timeout=60) as response:
                    data = json.loads(response.read().decode())
            except Exception as alt_e:
                print(f"Failed to fetch models from custom API: {alt_e}", file=sys.stderr)
                sys.exit(1)
        else:
            print(f"Failed to fetch models from custom API: {e}", file=sys.stderr)
            sys.exit(1)

    models = []
    for model in data.get("data", []):
        if "id" in model:
            models.append(model["id"])
                
    return sorted(list(set(models)))

def register_custom_backend_if_needed(backend_name, backend_url, api_key, admin_token):
    import re
    backend_slug = re.sub(r'[^a-zA-Z0-9-]', '-', backend_name.lower().strip())
    if not backend_slug:
        backend_slug = "custom-backend"
        
    check_query = f"SELECT id, metadata_json, backend_url FROM inference_backends WHERE name = '{backend_slug}';"
    rows = run_sql(check_query)
    backend_id = None
    
    expected_metadata = json.dumps({"api_key": api_key})
    healthcheck_path = '/models' if '/v1' in backend_url else '/v1/models'
    
    if rows:
        parts = rows[0].split("|")
        backend_id = parts[0].strip()
        existing_metadata = parts[1].strip() if len(parts) > 1 else ""
        existing_url = parts[2].strip() if len(parts) > 2 else ""
        
        try:
            meta_data = json.loads(existing_metadata) if existing_metadata else {}
            if meta_data.get("api_key") != api_key or existing_url != backend_url:
                print(f"Updating custom backend '{backend_slug}' in inference_backends...")
                safe_metadata = expected_metadata.replace("'", "''")
                update_query = f"""
                UPDATE inference_backends
                SET backend_url = '{backend_url}',
                    healthcheck_path = '{healthcheck_path}',
                    metadata_json = '{safe_metadata}',
                    updated_at = now()
                WHERE id = '{backend_id}';
                """
                run_sql(update_query)
                reload_gateway_cache(admin_token)
        except Exception as e:
            print(f"Warning: could not parse metadata: {e}")
    else:
        backend_id = str(uuid.uuid4())
        print(f"Registering custom backend '{backend_slug}' in database...")
        safe_metadata = expected_metadata.replace("'", "''")
        insert_query = f"""
        INSERT INTO inference_backends (
            id, name, provider, backend_url, healthcheck_path, is_active, is_default, status, max_parallel_requests, current_running, metadata_json, created_at, updated_at
        ) VALUES (
            '{backend_id}', '{backend_slug}', 'openai_compatible', '{backend_url}', '{healthcheck_path}', true, false, 'configured', 10, 0, '{safe_metadata}', now(), now()
        );
        """
        run_sql(insert_query)
        reload_gateway_cache(admin_token)
        
    return backend_id, backend_slug

def get_unique_alias(base_alias, model_id):
    """Generates a unique model_alias that does not exist in model_registry for a different model_id."""
    alias = base_alias
    counter = 1
    while True:
        check_query = f"SELECT model_id FROM model_registry WHERE model_alias = '{alias}';"
        rows = run_sql(check_query)
        if not rows:
            return alias
        existing_model_id = rows[0].strip()
        if existing_model_id == model_id:
            return alias
        alias = f"{base_alias}-{counter}"
        counter += 1

def register_model_if_needed(model_id, provider_choice, key, admin_token, custom_name=None, custom_url=None):
    """Checks database for the model and registers it if not present, healing fields if necessary."""
    modified = False
    
    if provider_choice == "nvidia":
        backend_id = register_nvidia_backend_if_needed(key, admin_token)
        db_provider = "openai_compatible"
    elif provider_choice == "custom":
        backend_id, backend_slug = register_custom_backend_if_needed(custom_name, custom_url, key, admin_token)
        db_provider = "openai_compatible"
    else:
        # Get OpenRouter backend ID and metadata
        backend_query = "SELECT id, metadata_json FROM inference_backends WHERE provider = 'openrouter' AND is_active = true LIMIT 1;"
        backend_rows = run_sql(backend_query)
        if not backend_rows:
            print("Error: Active OpenRouter backend not found in inference_backends database.", file=sys.stderr)
            sys.exit(1)
        parts = backend_rows[0].split("|")
        backend_id = parts[0].strip()
        existing_metadata = parts[1].strip() if len(parts) > 1 else ""
        
        # Ensure OpenRouter backend key is synced if the user provided a custom key
        expected_metadata = json.dumps({"api_key": key})
        try:
            meta_data = json.loads(existing_metadata) if existing_metadata else {}
            if meta_data.get("api_key") != key:
                print("Updating OpenRouter API Key in inference_backends...")
                safe_metadata = expected_metadata.replace("'", "''")
                update_query = f"""
                UPDATE inference_backends
                SET metadata_json = '{safe_metadata}', updated_at = now()
                WHERE id = '{backend_id}';
                """
                run_sql(update_query)
                modified = True
        except Exception as e:
            print(f"Warning: could not parse metadata: {e}")
            
        db_provider = "openrouter"
    
    # Check if already registered
    check_query = f"SELECT id, inference_backend_id FROM model_registry WHERE model_id = '{model_id}';"
    rows = run_sql(check_query)
    
    if rows:
        parts = rows[0].split("|")
        model_uuid = parts[0].strip()
        existing_backend_id = parts[1].strip() if len(parts) > 1 else ""
        
        print(f"Model '{model_id}' is already registered (ID: {model_uuid}).")
        
        # Self-healing for inference_backend_id in model_registry
        if not existing_backend_id or existing_backend_id != backend_id:
            print(f"Updating inference_backend_id in model_registry to active backend ({backend_id})...")
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
        base_alias = model_id.split("/")[-1].replace(":free", "")
        alias = get_unique_alias(base_alias, model_id)
        
        # Insert into model_registry with inference_backend_id
        insert_model = f"""
        INSERT INTO model_registry (id, model_id, model_alias, inference_backend_id, provider, model_file, is_active, is_default, context_length, created_at, updated_at)
        VALUES ('{model_uuid}', '{model_id}', '{alias}', '{backend_id}', '{db_provider}', '{model_id}', true, false, 8192, now(), now());
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
        reload_gateway_cache(admin_token)

def call_local_gateway(model_id, prompt, local_api_key):
    """Sends a chat completions request to the local gateway."""
    url = f"{GATEWAY_BASE_URL.rstrip('/')}/v1/chat/completions"
    print(f"\nSending chat completion request for model '{model_id}' to local gateway at {url}...")
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}]
    }
    data_bytes = json.dumps(payload).encode("utf-8")
    
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={
            "Authorization": f"Bearer {local_api_key}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
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
    # Resolve Gateway base URL and client key first
    global GATEWAY_BASE_URL
    GATEWAY_BASE_URL = get_gateway_base_url()
    
    local_api_key = get_client_api_key()
    admin_token = get_admin_token_cached()

    print("\n--- Select Provider ---")
    print("[1] OpenRouter (Free models)")
    print("[2] Nvidia (NIM Cloud API)")
    print("[3] Custom OpenAI-Compatible API (User API)")
    
    while True:
        try:
            prov_sel = input("\nSelect a provider by number (1-3): ").strip()
            if prov_sel == "1":
                provider_choice = "openrouter"
                break
            elif prov_sel == "2":
                provider_choice = "nvidia"
                break
            elif prov_sel == "3":
                provider_choice = "custom"
                break
            else:
                print("Invalid selection. Please choose 1, 2, or 3.")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            sys.exit(0)
            
    custom_name = None
    custom_url = None
    
    if provider_choice == "openrouter":
        openrouter_key = get_openrouter_key()
        models = fetch_openrouter_free_models(openrouter_key)
        key_to_use = openrouter_key
    elif provider_choice == "nvidia":
        nvidia_key = get_nvidia_key()
        models = fetch_nvidia_models(nvidia_key)
        key_to_use = nvidia_key
    else:
        print("\n--- Configure Custom OpenAI-Compatible Provider ---")
        cached_name = load_env_val("CUSTOM_PROVIDER_NAME") or "custom-backend"
        cached_url = load_env_val("CUSTOM_PROVIDER_URL") or "https://api.openai.com/v1"
        cached_key = load_env_val("CUSTOM_PROVIDER_API_KEY")
        
        custom_name = input(f"Enter custom provider name (slug, e.g. deepseek) [default: {cached_name}]: ").strip()
        if not custom_name:
            custom_name = cached_name
        save_env_val("CUSTOM_PROVIDER_NAME", custom_name)
        
        custom_url = input(f"Enter custom provider base URL [default: {cached_url}]: ").strip()
        if not custom_url:
            custom_url = cached_url
        if not custom_url.startswith("http://") and not custom_url.startswith("https://"):
            custom_url = "https://" + custom_url
        save_env_val("CUSTOM_PROVIDER_URL", custom_url)
        
        if cached_key:
            masked_key = f"{cached_key[:10]}...{cached_key[-5:]}" if len(cached_key) > 15 else cached_key
            print(f"Current Custom Provider API Key: {masked_key}")
            new_key = input("Enter new API Key (press Enter to keep current): ").strip()
            if new_key:
                key_to_use = new_key
                save_env_val("CUSTOM_PROVIDER_API_KEY", new_key)
            else:
                key_to_use = cached_key
        else:
            key_to_use = input("Enter API Key (press Enter if none required): ").strip()
            if key_to_use:
                save_env_val("CUSTOM_PROVIDER_API_KEY", key_to_use)
                
        models = fetch_custom_models(custom_url, key_to_use)
        
    if not models:
        print(f"No models found on {provider_choice.capitalize()}.")
        return
        
    print(f"\n--- Available {provider_choice.capitalize()} Models ---")
    for i, model in enumerate(models, 1):
        print(f"[{i:2d}] {model}")
        
    while True:
        try:
            selection = input(f"\nSelect a model by number (1-{len(models)}): ")
            idx = int(selection) - 1
            if 0 <= idx < len(models):
                selected_model = models[idx]
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
    register_model_if_needed(selected_model, provider_choice, key_to_use, admin_token, custom_name=custom_name, custom_url=custom_url)
    
    # Prompt user for question
    default_prompt = f"O que é o modelo {selected_model.split('/')[-1]}?"
    user_prompt = input(f"\nEnter prompt (default: '{default_prompt}'): ").strip()
    if not user_prompt:
        user_prompt = default_prompt
        
    # Execute query
    call_local_gateway(selected_model, user_prompt, local_api_key)

if __name__ == "__main__":
    main()
