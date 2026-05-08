#!/usr/bin/env python3
import asyncio
import json
import os
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path
try:
    import httpx
except ImportError:
    print("Error: httpx is required. Please install it or run within the poetry/venv environment.")
    sys.exit(1)

def get_git_info():
    try:
        import subprocess
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], encoding='utf-8').strip()
        branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], encoding='utf-8').strip()
        return commit, branch
    except Exception:
        return "unknown", "unknown"

def get_gpu_info():
    gpu_info = {
        "nvidia_smi_available": False,
        "gpu_name": "unknown",
        "vram_total_mb": 0,
        "vram_used_before_mb": 0,
        "vram_used_after_mb": 0
    }
    try:
        import subprocess
        # Check if nvidia-smi is available
        result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,memory.used', '--format=csv,noheader,nounits'], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if lines:
                parts = [p.strip() for p in lines[0].split(',')]
                gpu_info["nvidia_smi_available"] = True
                gpu_info["gpu_name"] = parts[0]
                gpu_info["vram_total_mb"] = int(parts[1])
                gpu_info["vram_used_before_mb"] = int(parts[2])
    except Exception:
        pass
    return gpu_info

def get_gpu_vram_used():
    try:
        import subprocess
        result = subprocess.run(['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if lines:
                return int(lines[0].strip())
    except Exception:
        pass
    return 0

async def run_single_request(client, url, headers, payload, is_streaming):
    start_time = time.perf_counter()
    ttft = None
    first_token_received = False
    chunks = []
    
    error_msg = None
    response_model = "unknown"
    fallback_used = False
    
    try:
        if is_streaming:
            async with client.stream("POST", url, headers=headers, json=payload, timeout=60.0) as response:
                response.raise_for_status()
                async for chunk in response.aiter_lines():
                    if chunk:
                        if not first_token_received:
                            ttft = (time.perf_counter() - start_time) * 1000
                            first_token_received = True
                        if chunk.startswith("data: "):
                            data_str = chunk[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                data_json = json.loads(data_str)
                                chunks.append(data_json)
                                if "model" in data_json:
                                    response_model = data_json["model"]
                                # detect mock fallback
                                if "choices" in data_json and data_json["choices"]:
                                    delta = data_json["choices"][0].get("delta", {})
                                    content = delta.get("content", "")
                                    if "fallback backend" in content.lower():
                                        fallback_used = True
                            except json.JSONDecodeError:
                                pass
        else:
            response = await client.post(url, headers=headers, json=payload, timeout=60.0)
            response.raise_for_status()
            data_json = response.json()
            chunks.append(data_json)
            if "model" in data_json:
                response_model = data_json["model"]
            if "choices" in data_json and data_json["choices"]:
                msg = data_json["choices"][0].get("message", {})
                content = msg.get("content", "")
                if "fallback backend" in content.lower():
                    fallback_used = True
    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
    except Exception as e:
        error_msg = str(e)
        
    total_time = (time.perf_counter() - start_time) * 1000
    
    prompt_tokens = 0
    completion_tokens = 0
    
    if not is_streaming and chunks and "usage" in chunks[0]:
        usage = chunks[0]["usage"]
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
    elif is_streaming and chunks:
        # Simple estimation for streaming if usage not provided in last chunk
        completion_tokens = len(chunks)
        prompt_tokens = payload.get("max_tokens", 10) # rough estimate
        
    return {
        "success": error_msg is None,
        "error": error_msg,
        "ttft_ms": ttft,
        "total_time_ms": total_time,
        "model_resolved": response_model,
        "fallback_used": fallback_used,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens
    }

async def run_benchmark(args):
    # Setup args handling
    if args.quick:
        args.tokens = 10
        args.runs = 1
        args.concurrency = 1
        
    prompt_text = args.prompt
    if args.prompt_file:
        try:
            with open(args.prompt_file, 'r') as f:
                prompt_text = f.read()
        except Exception as e:
            print(f"Error reading prompt file: {e}")
            sys.exit(1)
            
    if not prompt_text:
        prompt_text = "What is the capital of France? Explain in detail."

    headers = {
        "Content-Type": "application/json"
    }
    if args.client_api_key:
        headers["Authorization"] = f"Bearer {args.client_api_key}"

    payload = {
        "model": args.model,
        "messages": [{"role": "user", "content": prompt_text}],
        "max_tokens": args.tokens,
        "stream": args.streaming == 'true'
    }

    gpu_info = get_gpu_info()
    
    url = f"{args.base_url.rstrip('/')}/v1/chat/completions"
    
    print(f"Starting benchmark for model '{args.model}'...")
    print(f"Concurrency: {args.concurrency}, Runs per concurrent worker: {args.runs}")
    
    results = []
    
    async with httpx.AsyncClient() as client:
        # Warmup / health check (optional, but good)
        try:
            # We skip explicit warmup to just run the load
            pass
        except Exception:
            pass
            
        tasks = []
        for _ in range(args.concurrency * args.runs):
            tasks.append(run_single_request(client, url, headers, payload, args.streaming == 'true'))
            
        start_benchmark = time.perf_counter()
        all_responses = await asyncio.gather(*tasks)
        total_benchmark_time = time.perf_counter() - start_benchmark

    gpu_info["vram_used_after_mb"] = get_gpu_vram_used()
    
    # Aggregate metrics
    successful_runs = [r for r in all_responses if r["success"]]
    error_runs = [r for r in all_responses if not r["success"]]
    
    total_prompt_tokens = sum(r["prompt_tokens"] for r in successful_runs)
    total_completion_tokens = sum(r["completion_tokens"] for r in successful_runs)
    total_tokens = total_prompt_tokens + total_completion_tokens
    
    avg_ttft = sum(r["ttft_ms"] for r in successful_runs if r["ttft_ms"]) / len([r for r in successful_runs if r["ttft_ms"]]) if successful_runs and any(r["ttft_ms"] for r in successful_runs) else 0
    avg_total_time = sum(r["total_time_ms"] for r in successful_runs) / len(successful_runs) if successful_runs else 0
    
    tokens_per_second = total_completion_tokens / total_benchmark_time if total_benchmark_time > 0 else 0
    requests_per_second = len(successful_runs) / total_benchmark_time if total_benchmark_time > 0 else 0
    
    error_rate = len(error_runs) / len(all_responses) if all_responses else 0
    
    commit, branch = get_git_info()
    
    model_resolved = successful_runs[0]["model_resolved"] if successful_runs else "unknown"
    fallback_used = any(r["fallback_used"] for r in successful_runs)
    
    metrics = {
        "model_requested": args.model,
        "model_resolved": model_resolved,
        "backend": args.backend or "unknown",
        "fallback_used": fallback_used,
        "fallback_reason": "unknown", # Cannot easily infer reason from client side without admin API
        "runs": args.concurrency * args.runs,
        "concurrency": args.concurrency,
        "prompt_tokens": total_prompt_tokens,
        "completion_tokens": total_completion_tokens,
        "total_tokens": total_tokens,
        "time_to_first_token_ms": avg_ttft,
        "total_latency_ms": avg_total_time,
        "tokens_per_second": tokens_per_second,
        "requests_per_second": requests_per_second,
        "error_rate": error_rate,
        "cache_hit": "unknown",
        "queue_wait_ms": "unknown",
        "created_at": datetime.now().isoformat(),
        "git_commit": commit,
        "branch": branch,
        "nvidia_smi_available": gpu_info["nvidia_smi_available"],
        "gpu_name": gpu_info["gpu_name"],
        "vram_total_mb": gpu_info["vram_total_mb"],
        "vram_used_before_mb": gpu_info["vram_used_before_mb"],
        "vram_used_after_mb": gpu_info["vram_used_after_mb"]
    }

    # Generate Reports
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_model = args.model.replace("/", "_").replace(":", "_")
    out_dir = Path(args.output_dir) / safe_model / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)
    
    logs_dir = out_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # JSON Report
    with open(out_dir / "benchmark.json", "w") as f:
        json.dump(metrics, f, indent=2)
        
    # JSONL Raw Results
    with open(out_dir / "raw-results.jsonl", "w") as f:
        for r in all_responses:
            f.write(json.dumps(r) + "\n")
            
    # Markdown Report
    
    recommendation = "unknown"
    if error_rate > 0.5:
        recommendation = "Not recommended (high error rate)"
    elif tokens_per_second > 50 and avg_total_time < 2000:
        recommendation = "safe_for_free"
    elif tokens_per_second > 20 and avg_total_time < 5000:
        recommendation = "safe_for_basic"
    else:
        recommendation = "safe_for_premium"
        
    md_content = f"""# Benchmark Report: {args.model}

## Overview
- **Date**: {metrics['created_at']}
- **Model Requested**: {metrics['model_requested']}
- **Model Resolved**: {metrics['model_resolved']}
- **Backend**: {metrics['backend']}
- **Concurrency**: {metrics['concurrency']}
- **Total Runs**: {metrics['runs']}
- **Streaming**: {args.streaming}

## Performance
- **Tokens/sec**: {metrics['tokens_per_second']:.2f}
- **Requests/sec**: {metrics['requests_per_second']:.2f}
- **Average Latency**: {metrics['total_latency_ms']:.2f} ms
- **Average TTFT**: {metrics['time_to_first_token_ms']:.2f} ms
- **Error Rate**: {metrics['error_rate'] * 100:.2f}%
- **Fallback Used**: {metrics['fallback_used']}

## Hardware
- **GPU**: {metrics['gpu_name']}
- **VRAM Total**: {metrics['vram_total_mb']} MB
- **VRAM Used (Before)**: {metrics['vram_used_before_mb']} MB
- **VRAM Used (After)**: {metrics['vram_used_after_mb']} MB

## Recommendation
**{recommendation}**
"""
    with open(out_dir / "benchmark.md", "w") as f:
        f.write(md_content)
        
    print(f"\nBenchmark completed.")
    print(f"Output saved to: {out_dir}")
    print(f"Tokens/s: {metrics['tokens_per_second']:.2f}")
    print(f"Latency: {metrics['total_latency_ms']:.2f} ms")
    print(f"Recommendation: {recommendation}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Local Model Benchmark")
    parser.add_argument("--model", required=True, help="Model or alias to benchmark")
    parser.add_argument("--backend", default="", help="Backend ID or name")
    parser.add_argument("--prompt", default="", help="Prompt text")
    parser.add_argument("--prompt-file", default="", help="Path to prompt text file")
    parser.add_argument("--tokens", type=int, default=50, help="Max completion tokens")
    parser.add_argument("--concurrency", type=int, default=1, help="Number of concurrent requests")
    parser.add_argument("--runs", type=int, default=3, help="Number of runs per concurrent worker")
    parser.add_argument("--streaming", choices=['true', 'false'], default='false', help="Use streaming")
    parser.add_argument("--client-api-key", default="", help="Client API key")
    parser.add_argument("--base-url", default="http://localhost:18080", help="Base API URL")
    parser.add_argument("--output-dir", default="artifacts/model-benchmarks", help="Output directory")
    parser.add_argument("--quick", action="store_true", help="Run a quick benchmark")
    
    args = parser.parse_args()
    asyncio.run(run_benchmark(args))
