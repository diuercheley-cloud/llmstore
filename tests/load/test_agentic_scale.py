import asyncio
import uuid
import time
import httpx
import sys
from typing import List

BASE_URL = "http://localhost:8000"
TENANT_ID = "load-test-tenant"

async def run_agent(client: httpx.AsyncClient, agent_id: str, run_num: int):
    start = time.time()
    try:
        response = await client.post(
            f"/v1/agents/{agent_id}/runs",
            json={"input_text": f"Load test message {run_num}"},
            headers={"X-Tenant-ID": TENANT_ID}
        )
        response.raise_for_status()
        run_id = response.json()["id"]
        
        # Poll for completion
        for _ in range(30):
            await asyncio.sleep(2)
            res = await client.get(f"/v1/agents/runs/{run_id}", headers={"X-Tenant-ID": TENANT_ID})
            status = res.json()["status"]
            if status in ["completed", "failed"]:
                latency = time.time() - start
                return {"run_num": run_num, "status": status, "latency": latency}
                
        return {"run_num": run_num, "status": "timeout", "latency": time.time() - start}
    except Exception as e:
        return {"run_num": run_num, "status": "error", "error": str(e), "latency": time.time() - start}

async def scale_test(agent_id: str, count: int, concurrency: int = 50):
    async with httpx.AsyncClient(timeout=30) as client:
        tasks = []
        semaphore = asyncio.Semaphore(concurrency)

        async def sem_run(i):
            async with semaphore:
                return await run_agent(client, agent_id, i)

        print(f"Starting load test: {count} runs, {concurrency} concurrency...")
        start_all = time.time()
        
        results = await asyncio.gather(*[sem_run(i) for i in range(count)])
        
        total_time = time.time() - start_all
        
        # Stats
        completed = [r for r in results if r["status"] == "completed"]
        failed = [r for r in results if r["status"] == "failed"]
        errors = [r for r in results if r["status"] == "error"]
        latencies = [r["latency"] for r in completed]
        
        print("\n--- Load Test Results ---")
        print(f"Total Runs: {count}")
        print(f"Total Time: {total_time:.2f}s")
        print(f"Throughput: {count / total_time:.2f} runs/s")
        print(f"Success Rate: {len(completed) / count * 100:.1f}%")
        print(f"Failures/Errors: {len(failed) + len(errors)}")
        if latencies:
            print(f"Avg Latency: {sum(latencies) / len(latencies):.2f}s")
            print(f"P95 Latency: {sorted(latencies)[int(len(latencies)*0.95)]:.2f}s")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_agentic_scale.py <agent_id> <count>")
        sys.exit(1)
    
    a_id = sys.argv[1]
    c = int(sys.argv[2])
    asyncio.run(scale_test(a_id, c))
