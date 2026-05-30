#!/bin/bash
# Validate that agent eval suites are populated and compliant with production requirements.
set -euo pipefail

TEMPLATES=(
  "support-triage"
  "github-issue-triage"
  "compliance-evidence"
  "rag-research"
  "incident-response"
  "billing-review"
  "devops-runbook"
  "salesforce-account-summary"
)

echo "Validating Agent Evaluation Datasets..."
exit_code=0

for template in "${TEMPLATES[@]}"; do
  file="examples/agents/${template}/eval_suite.json"
  if [ ! -f "$file" ]; then
    echo "ERROR: Missing eval_suite.json for template '${template}' at ${file}"
    exit_code=1
    continue
  fi

  # Run Python script inline to check schema and count
  python3 -c "
import json, sys
try:
    with open('$file') as f:
        data = json.load(f)
except Exception as e:
    print('ERROR: Invalid JSON in $file:', e)
    sys.exit(1)

if 'test_cases' not in data:
    print('ERROR: Missing \"test_cases\" key in $file')
    sys.exit(1)

cases = data['test_cases']
if len(cases) < 10:
    print(f'ERROR: Template \"$template\" has only {len(cases)} test cases, minimum is 10.')
    sys.exit(1)

required_keys = ['input', 'expected_behavior', 'prohibited_behavior', 'allowed_tools', 'expected_tools', 'max_steps', 'max_cost', 'assertions']
required_tags = ['happy path', 'edge case', 'tool failure', 'policy denial', 'memory retrieval', 'unsafe request', 'tenant isolation', 'approval required', 'cost limit', 'final answer quality']

found_tags = set()
for idx, case in enumerate(cases):
    for key in required_keys:
        if key not in case:
            print(f'ERROR: Case {idx} (\"' + case.get('name', 'unnamed') + '\") in $file is missing required key: \"{key}\"')
            sys.exit(1)
    tags = case.get('tags', [])
    for tag in tags:
        found_tags.add(tag.lower())

missing_tags = [tag for tag in required_tags if tag not in found_tags]
if missing_tags:
    print(f'WARNING: Template \"$template\" is missing test types: {missing_tags}')
" && echo "SUCCESS: $template is fully compliant with 10+ test cases." || exit_code=1
done

if [ "$exit_code" -eq 0 ]; then
  echo "All Agent Evaluation Datasets are valid and populated!"
else
  echo "Some evaluation datasets failed validation."
fi

exit "$exit_code"
