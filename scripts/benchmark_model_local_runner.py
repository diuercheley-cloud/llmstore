#!/usr/bin/env python3
import argparse
import asyncio
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

import psutil

try:
    import httpx
except ImportError:
    print("Error: httpx is required. Please install it or run within the poetry/venv environment.")
    sys.exit(1)

VERSION = "1.5.6"

def get_git_info():
    try:
        import subprocess
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], encoding='utf-8', stderr=subprocess.DEVNULL).strip()
        return commit
    except Exception:
        return "unknown"

def get_system_metrics():
    metrics = {
        "cpu_load": psutil.cpu_percent(interval=None),
        "memory_used_mb": psutil.virtual_memory().used / (1024 * 1024)
    }
    return metrics

def get_gpu_info():
    gpu_info = {
        "gpu_detected": False,
        "gpu_name": "unknown",
        "vram_total_mb": 0,
        "vram_used_before_mb": 0,
        "vram_used_after_mb": 0
    }
    try:
        import subprocess
        result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,memory.used', '--format=csv,noheader,nounits'], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if lines:
                parts = [p.strip() for p in lines[0].split(',')]
                gpu_info["gpu_detected"] = True
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

async def run_single_request(client, url, headers, payload, is_streaming, timeout):
    start_time = time.perf_counter()
    ttft = None
    first_token_received = False
    chunks = []
    
    error_msg = None
    timeout_occurred = False
    response_model = "unknown"
    fallback_used = False
    backend_id = "unknown"
    backend_type = "unknown"
    queue_wait_ms = 0
    cache_hit = False
    
    try:
        if is_streaming:
            async with client.stream("POST", url, headers=headers, json=payload, timeout=timeout) as response:
                response.raise_for_status()
                # Check for custom headers
                backend_id = response.headers.get("X-LLM-Backend", backend_id)
                backend_type = response.headers.get("X-LLM-Backend-Type", backend_type)
                queue_wait_ms = float(response.headers.get("X-LLM-Queue-Wait-Ms", 0))
                cache_hit = response.headers.get("X-LLM-Cache-Hit") == "true"
                
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
                                # detect fallback
                                if "choices" in data_json and data_json["choices"]:
                                    delta = data_json["choices"][0].get("delta", {})
                                    content = delta.get("content", "")
                                    if "fallback" in content.lower():
                                        fallback_used = True
                            except json.JSONDecodeError:
                                pass
        else:
            response = await client.post(url, headers=headers, json=payload, timeout=timeout)
            response.raise_for_status()
            
            backend_id = response.headers.get("X-LLM-Backend", backend_id)
            backend_type = response.headers.get("X-LLM-Backend-Type", backend_type)
            queue_wait_ms = float(response.headers.get("X-LLM-Queue-Wait-Ms", 0))
            cache_hit = response.headers.get("X-LLM-Cache-Hit") == "true"
            
            data_json = response.json()
            chunks.append(data_json)
            if "model" in data_json:
                response_model = data_json["model"]
            if "choices" in data_json and data_json["choices"]:
                msg = data_json["choices"][0].get("message", {})
                content = msg.get("content", "")
                if "fallback" in content.lower():
                    fallback_used = True
                    
    except httpx.TimeoutException:
        timeout_occurred = True
        error_msg = "Request timeout"
    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
    except Exception as e:
        error_msg = str(e)
        
    total_time = (time.perf_counter() - start_time) * 1000
    
    prompt_tokens = 0
    completion_tokens = 0
    
    if not timeout_occurred and not error_msg and chunks:
        if not is_streaming and "usage" in chunks[0]:
            usage = chunks[0]["usage"]
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
        elif is_streaming:
            # Try to get usage from last chunk if provided
            last_chunk = chunks[-1] if chunks else {}
            if "usage" in last_chunk and last_chunk["usage"]:
                usage = last_chunk["usage"]
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
            else:
                completion_tokens = len(chunks)
                prompt_tokens = payload.get("max_tokens", 10) # rough estimate
        
    return {
        "success": error_msg is None,
        "error": error_msg,
        "timeout": timeout_occurred,
        "ttft_ms": ttft,
        "total_time_ms": total_time,
        "model_resolved": response_model,
        "fallback_used": fallback_used,
        "backend": backend_id,
        "backend_type": backend_type,
        "queue_wait_ms": queue_wait_ms,
        "cache_hit": cache_hit,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens
    }

def get_recommendation(tps, latency_p95, error_rate):
    if error_rate > 0.1:
        return "not_recommended", "High error rate detected (>10%)"
    
    if tps >= 30 and latency_p95 < 2000:
        return "safe_for_free", "High throughput and low latency, suitable for high volume/free tier."
    if tps >= 15 and latency_p95 < 5000:
        return "safe_for_basic", "Moderate throughput, suitable for basic tier."
    if tps >= 5 or latency_p95 < 15000:
        return "safe_for_premium", "Low throughput or higher latency, recommended for premium/dedicated use."
    
    return "not_recommended", "Performance below minimum standards for reliable service."

async def run_benchmark(args):
    # Setup args handling based on modes
    if args.quick:
        args.max_tokens = 20
        args.runs = 1
        args.concurrency = 1
    elif args.standard:
        args.max_tokens = 100
        args.runs = 3
        args.concurrency = 1
    elif args.stress:
        print("!!! STRESS MODE DETECTED !!!")
        confirm = input("This will run a heavy load. Continue? (y/N): ")
        if confirm.lower() != 'y':
            print("Aborted.")
            return
        args.max_tokens = 256
        args.runs = 10
        args.concurrency = 5

    prompt_text = args.prompt
    if args.prompt_file:
        try:
            with open(args.prompt_file, 'r') as f:
                prompt_text = f.read()
        except Exception as e:
            print(f"Error reading prompt file: {e}")
            sys.exit(1)
            
    if not prompt_text:
        prompt_text = "Summarize the importance of local LLM inference in 3 paragraphs."

    headers = {
        "Content-Type": "application/json"
    }
    if args.client_api_key:
        headers["Authorization"] = f"Bearer {args.client_api_key}"

    payload = {
        "model": args.model,
        "messages": [{"role": "user", "content": prompt_text}],
        "max_tokens": args.max_tokens,
        "stream": args.streaming == 'true'
    }

    gpu_info = get_gpu_info()
    sys_before = get_system_metrics()
    
    url = f"{args.base_url.rstrip('/')}/v1/chat/completions"
    
    print(f"Starting benchmark for model '{args.model}'...")
    print(f"Mode: {'quick' if args.quick else 'stress' if args.stress else 'standard'}")
    print(f"Concurrency: {args.concurrency}, Total Runs: {args.concurrency * args.runs}")
    
    all_responses = []
    
    timeout = 120.0
    async with httpx.AsyncClient() as client:
        for r in range(args.runs):
            tasks = []
            for _ in range(args.concurrency):
                tasks.append(run_single_request(client, url, headers, payload, args.streaming == 'true', timeout))
            
            batch_results = await asyncio.gather(*tasks)
            all_responses.extend(batch_results)
            if args.runs > 1:
                print(f"Batch {r+1}/{args.runs} completed.")

    gpu_info["vram_used_after_mb"] = get_gpu_vram_used()
    sys_after = get_system_metrics()
    
    # Aggregate metrics
    successful_runs = [r for r in all_responses if r["success"]]
    error_runs = [r for r in all_responses if not r["success"]]
    timeout_runs = [r for r in all_responses if r["timeout"]]
    
    total_prompt_tokens = sum(r["prompt_tokens"] for r in successful_runs)
    total_completion_tokens = sum(r["completion_tokens"] for r in successful_runs)
    total_tokens = total_prompt_tokens + total_completion_tokens
    
    ttfts = [r["ttft_ms"] for r in successful_runs if r["ttft_ms"] is not None]
    latencies = [r["total_time_ms"] for r in successful_runs]
    
    avg_ttft = statistics.mean(ttfts) if ttfts else 0
    p95_ttft = statistics.quantiles(ttfts, n=20)[18] if len(ttfts) >= 2 else (ttfts[0] if ttfts else 0)
    
    avg_latency = statistics.mean(latencies) if latencies else 0
    p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 2 else (latencies[0] if latencies else 0)
    
    # Calculate tokens per second (average of successful runs)
    # Each run has its own tokens and time. 
    # TPS = sum(completion_tokens) / sum(total_time_s) is one way, 
    # but we want average of TPS per run for better distribution.
    tps_list = []
    for r in successful_runs:
        duration_s = r["total_time_ms"] / 1000
        if duration_s > 0:
            tps_list.append(r["completion_tokens"] / duration_s)
    
    avg_tps = statistics.mean(tps_list) if tps_list else 0
    
    error_rate = len(error_runs) / len(all_responses) if all_responses else 0
    timeout_rate = len(timeout_runs) / len(all_responses) if all_responses else 0
    
    model_resolved = successful_runs[0]["model_resolved"] if successful_runs else "unknown"
    backend = successful_runs[0]["backend"] if successful_runs else "unknown"
    backend_type = successful_runs[0]["backend_type"] if successful_runs else "unknown"
    fallback_used = any(r["fallback_used"] for r in successful_runs)
    avg_queue_wait = statistics.mean([r["queue_wait_ms"] for r in successful_runs]) if successful_runs else 0
    cache_hit_rate = len([r for r in successful_runs if r["cache_hit"]]) / len(successful_runs) if successful_runs else 0
    
    recommendation, reason = get_recommendation(avg_tps, p95_latency, error_rate)
    
    metrics = {
        "model_requested": args.model,
        "model_resolved": model_resolved,
        "backend": backend,
        "backend_type": backend_type,
        "fallback_used": fallback_used,
        "fallback_reason": "N/A" if not fallback_used else "Target backend failure or busy",
        "time_to_first_token_ms": avg_ttft,
        "time_to_first_token_p95_ms": p95_ttft,
        "total_latency_ms": avg_latency,
        "total_latency_p95_ms": p95_latency,
        "tokens_per_second": avg_tps,
        "prompt_tokens": total_prompt_tokens,
        "completion_tokens": total_completion_tokens,
        "total_tokens": total_tokens,
        "error_rate": error_rate,
        "timeout_rate": timeout_rate,
        "queue_wait_ms": avg_queue_wait,
        "cache_hit": cache_hit_rate > 0.5, # Boolean as requested, but we could use rate
        "cache_hit_rate": cache_hit_rate,
        "created_at": datetime.now().isoformat(),
        "git_commit": get_git_info(),
        "version": VERSION,
        "gpu_detected": gpu_info["gpu_detected"],
        "gpu_name": gpu_info["gpu_name"],
        "vram_total_mb": gpu_info["vram_total_mb"],
        "vram_used_before_mb": gpu_info["vram_used_before_mb"],
        "vram_used_after_mb": gpu_info["vram_used_after_mb"],
        "cpu_load": sys_after["cpu_load"],
        "memory_used_mb": sys_after["memory_used_mb"],
        "recommendation": recommendation,
        "recommendation_reason": reason
    }

    # Output Management
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_model = args.model.replace("/", "_").replace(":", "_")
    out_dir = Path(args.output_dir) / safe_model / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. JSON Report
    with open(out_dir / "benchmark.json", "w") as f:
        json.dump(metrics, f, indent=2)
        
    # 2. JSONL Raw Results
    with open(out_dir / "raw-results.jsonl", "w") as f:
        for r in all_responses:
            f.write(json.dumps(r) + "\n")
            
    # 3. Markdown Report
    runs_table = "| Run | Success | TTFT (ms) | Total (ms) | Tokens | TPS | Backend |\n"
    runs_table += "|---|---|---|---|---|---|---|\n"
    for i, r in enumerate(all_responses):
        tps = (r["completion_tokens"] / (r["total_time_ms"]/1000)) if r["success"] and r["total_time_ms"] > 0 else 0
        ttft_str = f"{r['ttft_ms']:.1f}" if r['ttft_ms'] is not None else "N/A"
        runs_table += f"| {i+1} | {r['success']} | {ttft_str} | {r['total_time_ms']:.1f} | {r['completion_tokens']} | {tps:.2f} | {r['backend']} |\n"

    md_content = f"""# Benchmark Report: {args.model}

## Metadata
- **Created At**: {metrics['created_at']}
- **Version**: {metrics['version']}
- **Git Commit**: `{metrics['git_commit']}`
- **Backend**: {metrics['backend']} ({metrics['backend_type']})

## Performance Summary
| Metric | Average | P95 |
|---|---|---|
| **Latency (ms)** | {metrics['total_latency_ms']:.2f} | {metrics['total_latency_p95_ms']:.2f} |
| **TTFT (ms)** | {metrics['time_to_first_token_ms']:.2f} | {metrics['time_to_first_token_p95_ms']:.2f} |
| **Tokens/sec** | {metrics['tokens_per_second']:.2f} | N/A |

- **Error Rate**: {metrics['error_rate']*100:.1f}%
- **Timeout Rate**: {metrics['timeout_rate']*100:.1f}%
- **Queue Wait**: {metrics['queue_wait_ms']:.1f} ms
- **Cache Hit**: {metrics['cache_hit']}

## System State
- **CPU Load**: {metrics['cpu_load']}%
- **Memory Used**: {metrics['memory_used_mb']:.1f} MB
- **GPU**: {metrics['gpu_name']}
- **VRAM**: {metrics['vram_used_after_mb']} / {metrics['vram_total_mb']} MB

## Detailed Runs
{runs_table}

## Recommendation
### **{metrics['recommendation'].upper().replace('_', ' ')}**
> {metrics['recommendation_reason']}

---
Generated by Gemini CLI LLM Stack Benchmark Tool.
"""
    with open(out_dir / "benchmark.md", "w") as f:
        f.write(md_content)
        
    print("\nBenchmark completed successfully.")
    print(f"Directory: {out_dir}")
    print(f"TPS: {metrics['tokens_per_second']:.2f}")
    print(f"P95 Latency: {metrics['total_latency_p95_ms']:.2f} ms")
    print(f"Recommendation: {metrics['recommendation']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Local Model Benchmark Runner")
    parser.add_argument("--model", required=True, help="Model or alias to benchmark")
    parser.add_argument("--backend", default="", help="Force specific backend (optional)")
    parser.add_argument("--prompt", default="", help="Prompt text")
    parser.add_argument("--prompt-file", default="", help="Path to prompt text file")
    parser.add_argument("--max-tokens", type=int, default=128, help="Max completion tokens")
    parser.add_argument("--concurrency", type=int, default=1, help="Number of concurrent requests")
    parser.add_argument("--runs", type=int, default=3, help="Number of runs (or batches of concurrency)")
    parser.add_argument("--streaming", choices=['true', 'false'], default='false', help="Use streaming")
    parser.add_argument("--client-api-key", default="", help="Client API key")
    parser.add_argument("--base-url", default="http://localhost:18080", help="Base API URL")
    parser.add_argument("--output-dir", default="artifacts/model-benchmarks", help="Output directory")
    
    # Modes
    parser.add_argument("--quick", action="store_true", help="Quick mode (1 run, low tokens)")
    parser.add_argument("--standard", action="store_true", help="Standard mode (3 runs)")
    parser.add_argument("--stress", action="store_true", help="Stress mode (Heavy load, high concurrency)")
    
    args = parser.parse_args()
    
    # Ensure artifacts directory exists
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    
    try:
        asyncio.run(run_benchmark(args))
    except KeyboardInterrupt:
        print("\nBenchmark interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nBenchmark failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
