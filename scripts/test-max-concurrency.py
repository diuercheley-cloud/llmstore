#!/usr/bin/env python3
import argparse
import asyncio
import os
import sys
import time
from typing import Dict

import httpx


async def send_request(client: httpx.AsyncClient, url: str, api_key: str, model: str, request_id: int) -> Dict:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": f"Request {request_id}: Tell me a very short joke."}],
        "max_tokens": 20,
        "stream": False
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    start_time = time.perf_counter()
    try:
        response = await client.post(f"{url}/v1/chat/completions", json=payload, headers=headers, timeout=60.0)
        end_time = time.perf_counter()
        
        if response.status_code == 200:
            return {
                "success": True,
                "latency": end_time - start_time,
                "status_code": response.status_code
            }
        else:
            return {
                "success": False,
                "latency": end_time - start_time,
                "status_code": response.status_code,
                "error": response.text
            }
    except Exception as e:
        end_time = time.perf_counter()
        return {
            "success": False,
            "latency": end_time - start_time,
            "status_code": 0,
            "error": str(e)
        }

async def run_concurrency_test(url: str, api_key: str, model: str, concurrency: int):
    print(f"Testing concurrency: {concurrency}...")
    async with httpx.AsyncClient() as client:
        tasks = [send_request(client, url, api_key, model, i) for i in range(concurrency)]
        results = await asyncio.gather(*tasks)
        
    successes = [r for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]
    
    if successes:
        avg_latency = sum(r["latency"] for r in successes) / len(successes)
        max_latency = max(r["latency"] for r in successes)
    else:
        avg_latency = 0
        max_latency = 0
        
    print(f"  Success: {len(successes)}/{concurrency}")
    print(f"  Avg Latency: {avg_latency:.2f}s")
    print(f"  Max Latency: {max_latency:.2f}s")
    
    if failures:
        print(f"  Failures: {len(failures)}")
        sample_error = failures[0]['error']
        print(f"  Sample Error: {sample_error[:100]}")
        if "exceeded" in sample_error and "requests per minute" in sample_error:
            print("  HINT: You hit a rate limit. Consider using a client with a higher quota or a different billing plan.")
        
    return {
        "concurrency": concurrency,
        "success_rate": len(successes) / concurrency,
        "avg_latency": avg_latency,
        "max_latency": max_latency,
        "failed": len(failures) > 0
    }

async def main():
    parser = argparse.ArgumentParser(description="Test maximum concurrency for Gemma")
    parser.add_argument("--url", default=os.getenv("BASE_URL", "http://localhost:18080"), help="Base URL of the API")
    parser.add_argument("--api-key", default=os.getenv("API_KEY"), help="API Key")
    parser.add_argument("--model", default="gemma", help="Model ID")
    parser.add_argument("--start", type=int, default=1, help="Starting concurrency")
    parser.add_argument("--step", type=int, default=2, help="Concurrency step")
    parser.add_argument("--max", type=int, default=20, help="Maximum concurrency to test")
    parser.add_argument("--max-latency", type=float, default=30.0, help="Stop if avg latency exceeds this (seconds)")
    
    args = parser.parse_args()
    
    if not args.api_key:
        print("Error: API_KEY must be set via environment variable or --api-key")
        sys.exit(1)
        
    url = args.url.rstrip("/")
    
    results = []
    for c in range(args.start, args.max + 1, args.step):
        res = await run_concurrency_test(url, args.api_key, args.model, c)
        results.append(res)
        
        if res["success_rate"] < 0.8:
            print(f"\nStopping: Success rate dropped below 80% at concurrency {c}")
            break
        
        if res["avg_latency"] > args.max_latency:
            print(f"\nStopping: Average latency exceeded {args.max_latency}s at concurrency {c}")
            break
            
        # Give the system a bit of breathing room between tests
        await asyncio.sleep(1)

    print("\n--- Summary ---")
    print(f"{'Concurrency':<12} {'Success %':<12} {'Avg Latency':<12} {'Max Latency':<12}")
    for res in results:
        print(f"{res['concurrency']:<12} {res['success_rate']*100:<11.1f}% {res['avg_latency']:<11.2f}s {res['max_latency']:<11.2f}s")

if __name__ == "__main__":
    asyncio.run(main())
