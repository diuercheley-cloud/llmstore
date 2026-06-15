import json
import subprocess
import sys
import time
from datetime import datetime

import requests


def get_resource_usage(container_name):
    try:
        # Get Docker stats
        docker_stats = subprocess.check_output(
            [
                "docker",
                "stats",
                "--no-stream",
                "--format",
                "{{.MemUsage}} {{.CPUPerc}}",
                container_name,
            ],
            encoding="utf-8",
        ).strip()

        # Get VRAM usage
        vram_stats = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            encoding="utf-8",
        ).strip()

        return docker_stats, vram_stats
    except Exception as e:
        return f"Error: {e}", "Error"


def run_benchmark(config, output_file):
    base_url = "http://localhost:8081"
    prompt = "Explique detalhadamente o que é inferência de LLMs e como otimizar para GPUs com pouca VRAM."
    payload = {"prompt": prompt, "n_predict": 128, "n_min": 64, "stream": False}

    print(f"Running benchmark for config: {config}")

    # Wait for service to be healthy
    max_retries = 120
    for i in range(max_retries):
        try:
            resp = requests.get(f"{base_url}/health")
            if resp.status_code == 200:
                break
        except:
            pass
        time.sleep(1)
    else:
        print("Service failed to become healthy")
        return

    # Baseline usage
    container_name = "llm-inference-stack-data-plane-gemma-1"
    baseline_docker, baseline_vram = get_resource_usage(container_name)

    start_time = time.time()
    try:
        # We use a separate thread or just capture peak if possible.
        # For simplicity, we capture during the request.
        response = requests.post(f"{base_url}/completion", json=payload, timeout=60)
        end_time = time.time()

        # Capture usage immediately after/during (simulated peak)
        peak_docker, peak_vram = get_resource_usage(container_name)

        if response.status_code == 200:
            data = response.json()
            timings = data.get("timings", {})

            result = {
                "timestamp": datetime.now().isoformat(),
                "config": config,
                "metrics": {
                    "tokens_per_s": timings.get("predicted_per_second"),
                    "latency_first_token_ms": timings.get(
                        "prompt_ms"
                    ),  # Approximation for first token if n_keep=0
                    "latency_total_ms": (end_time - start_time) * 1000,
                    "vram_used_mb": peak_vram,
                    "ram_usage": peak_docker.split()[0],
                    "cpu_usage": peak_docker.split()[-1],
                },
                "raw_timings": timings,
            }

            with open(output_file, "a") as f:
                f.write(json.dumps(result) + "\n")

            print(
                f"Result: {result['metrics']['tokens_per_s']} t/s, {result['metrics']['vram_used_mb']} MB VRAM"
            )
        else:
            print(f"Request failed: {response.status_code}")
    except Exception as e:
        print(f"Error during request: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: benchmark_runner.py <config_json> <output_file>")
        sys.exit(1)

    config = json.loads(sys.argv[1])
    output_file = sys.argv[2]
    run_benchmark(config, output_file)
