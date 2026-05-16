import time
import hashlib
import json

def generate_performance_baseline():
    print("Generating performance baseline metrics...")
    
    # Simple hashing benchmark
    data = b"performance_test_payload" * 100
    start = time.time()
    for _ in range(1000):
        hashlib.sha256(data).hexdigest()
    end = time.time()
    hashing_latency = (end - start) / 1000
    
    print(f"Hashing Latency: {hashing_latency*1000:.4f}ms")
    
    # Register in a JSON file for future regression checks
    baseline = {
        "timestamp": time.time(),
        "hashing_latency_ms": hashing_latency * 1000,
        "startup_sim_ms": 1200 # Simulated
    }
    
    with open("docs/performance/performance_baseline.json", "w") as f:
        json.dump(baseline, f, indent=2)
        
    print("Performance baseline saved to docs/performance/performance_baseline.json")

if __name__ == "__main__":
    generate_performance_baseline()
