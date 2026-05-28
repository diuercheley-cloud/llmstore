#!/usr/bin/env bash
# Owner: platform-ops
# Status: implementation

echo "=== Real Execution Readiness Gate ==="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"

if [[ -f "${ROOT_DIR}/.venv/bin/python3" ]]; then
  PYTHON_EXE="${ROOT_DIR}/.venv/bin/python3"
elif [[ -f "${ROOT_DIR}/venv/bin/python3" ]]; then
  PYTHON_EXE="${ROOT_DIR}/venv/bin/python3"
else
  PYTHON_EXE="python3"
fi

# 1. Run Automated Checks via Python Service
echo "Running readiness checks..."
cd "${ROOT_DIR}" && PYTHONPATH=control_plane ${PYTHON_EXE} -c "
import asyncio
import json
import sys
from app.db.session import SessionLocal
from app.services.runtime.real_execution_readiness import RealExecutionReadinessService

async def main():
    async with SessionLocal() as db:
        svc = RealExecutionReadinessService(db)
        results = await svc.check_readiness()
        
        # Save results to artifact
        import os
        os.makedirs('artifacts/runtime', exist_ok=True)
        with open('artifacts/runtime/real-execution-readiness.json', 'w') as f:
            json.dump(results, f, indent=2)
            
        # Generate Markdown Report
        with open('artifacts/runtime/real-execution-readiness.md', 'w') as f:
            f.write('# Real Execution Readiness Report\n\n')
            f.write(f'**Overall Status:** {results[\"status\"]}\n')
            f.write(f'**Timestamp:** {results[\"timestamp\"]}\n\n')
            
            f.write('## Checks\n\n')
            f.write('| Check | Status | Value |\n')
            f.write('|-------|--------|-------|\n')
            for check in results['checks']:
                status_emoji = '✅' if check['status'] == 'pass' else ('⚠️' if check['status'] == 'warn' else '❌')
                f.write(f'| {check[\"name\"]} | {status_emoji} {check[\"status\"]} | {check[\"value\"]} |\n')
            
            if results['blockers']:
                f.write('\n## ❌ Blockers\n\n')
                for b in results['blockers']:
                    f.write(f'- {b}\n')
            
            if results['warnings']:
                f.write('\n## ⚠️ Warnings\n\n')
                for w in results['warnings']:
                    f.write(f'- {w}\n')
        
        print(f'Readiness Status: {results[\"status\"]}')
        if results['status'] == 'production_blocked':
            print('ERROR: Production execution is blocked. See artifacts/runtime/real-execution-readiness.md')
            sys.exit(1)
        else:
            print('SUCCESS: Runtime is ready for its assigned deployment mode.')

asyncio.run(main())
"

if [ $? -eq 0 ]; then
    echo "✅ Readiness Gate Passed."
else
    echo "❌ Readiness Gate Failed."
    exit 1
fi
