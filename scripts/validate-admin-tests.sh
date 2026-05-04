#!/usr/bin/env bash
set -e

# Load environment variables
if [ -f .env.local ]; then
  source .env.local
else
  echo "Error: .env.local not found."
  exit 1
fi

echo "--- Testing /admin-tests ---"
status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:18080/admin-tests)
if [ "$status" -eq 200 ]; then
  echo "PASS: /admin-tests returns 200"
else
  echo "FAIL: /admin-tests returns $status"
fi

echo -e "\n--- Testing /admin/tests/auth/whoami without token ---"
status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:18080/admin/tests/auth/whoami)
if [ "$status" -eq 401 ]; then
  echo "PASS: /admin/tests/auth/whoami without token returns 401"
else
  echo "FAIL: /admin/tests/auth/whoami without token returns $status"
fi

echo -e "\n--- Testing /admin/tests/auth/whoami with token ---"
status=$(curl -s -o /dev/null -w "%{http_code}" -H "X-Admin-Token: ${ADMIN_TOKEN}" http://localhost:18080/admin/tests/auth/whoami)
if [ "$status" -eq 200 ]; then
  echo "PASS: /admin/tests/auth/whoami with token returns 200"
else
  echo "FAIL: /admin/tests/auth/whoami with token returns $status"
fi

echo -e "\n--- Testing /admin/tests/system/resources with token ---"
status=$(curl -s -o /dev/null -w "%{http_code}" -H "X-Admin-Token: ${ADMIN_TOKEN}" http://localhost:18080/admin/tests/system/resources)
if [ "$status" -eq 200 ]; then
  echo "PASS: /admin/tests/system/resources with token returns 200"
else
  echo "FAIL: /admin/tests/system/resources with token returns $status"
fi

echo -e "\n--- Testing /admin/tests/audit with token ---"
status=$(curl -s -o /dev/null -w "%{http_code}" -H "X-Admin-Token: ${ADMIN_TOKEN}" http://localhost:18080/admin/tests/audit)
if [ "$status" -eq 200 ]; then
  echo "PASS: /admin/tests/audit with token returns 200"
else
  echo "FAIL: /admin/tests/audit with token returns $status"
fi

echo -e "\nAll validation checks completed."
