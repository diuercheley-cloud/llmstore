import json
from pathlib import Path

from app.core.config import get_settings
from app.services.auth import require_admin
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(prefix="/admin", tags=["admin-benchmarks"], dependencies=[Depends(require_admin)])


@router.get("/benchmarks")
async def list_benchmarks():
    """
    List the latest benchmark for each model found in artifacts.
    """
    benchmarks_dir = Path("artifacts/model-benchmarks")
    if not benchmarks_dir.exists():
        return []

    results = []
    try:
        for model_dir in benchmarks_dir.iterdir():
            if not model_dir.is_dir():
                continue

            # Get the latest timestamp directory
            runs = [d for d in model_dir.iterdir() if d.is_dir()]
            if not runs:
                continue

            latest_run = max(runs, key=lambda d: d.name)
            bench_file = latest_run / "benchmark.json"

            if bench_file.exists():
                try:
                    with open(bench_file, "r") as f:
                        data = json.load(f)
                        results.append(data)
                except Exception:
                    pass
    except Exception:
        pass

    return results


@router.get("/benchmarks/{model}")
async def get_model_benchmark(model: str):
    """
    Get the latest benchmark for a specific model.
    """
    settings = get_settings()
    # Handle model names with slashes or colons by replacing them as done in the runner
    safe_model = model.replace("/", "_").replace(":", "_")
    bench_dir = Path("artifacts/model-benchmarks") / safe_model

    if not bench_dir.exists():
        raise HTTPException(status_code=404, detail=f"No benchmarks found for model {model}")

    runs = [d for d in bench_dir.iterdir() if d.is_dir()]
    if not runs:
        raise HTTPException(status_code=404, detail=f"No runs found for model {model}")

    latest_run = max(runs, key=lambda d: d.name)
    bench_file = latest_run / "benchmark.json"

    if not bench_file.exists():
        raise HTTPException(status_code=404, detail=f"Benchmark file not found for latest run of {model}")

    try:
        with open(bench_file, "r") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading benchmark: {str(e)}")
