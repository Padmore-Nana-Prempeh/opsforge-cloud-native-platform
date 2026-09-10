#!/usr/bin/env bash

set -euo pipefail

GATEWAY_URL="${GATEWAY_URL:-http://127.0.0.1:8000}"

echo "A1 smoke test"
echo "-------------"

echo "Checking liveness..."
curl -fsS "${GATEWAY_URL}/health/live"
echo

echo "Checking readiness..."
curl -fsS "${GATEWAY_URL}/health/ready"
echo

echo "Creating order..."

response="$(
  curl -fsS \
    -X POST \
    "${GATEWAY_URL}/orders/smoke-item"
)"

echo "${response}"

order_id="$(
  python -c '
import json
import sys

data = json.load(sys.stdin)
print(data["order"]["id"])
' <<< "${response}"
)"

echo
echo "Created order: ${order_id}"
echo "Waiting for worker..."

for attempt in {1..10}; do

    order="$(
      curl -fsS \
        "${GATEWAY_URL}/orders/${order_id}"
    )"

    status="$(
      python -c '
import json
import sys

data = json.load(sys.stdin)
print(data["status"])
' <<< "${order}"
    )"

    echo "Attempt ${attempt}: ${status}"

    if [[ "${status}" == "completed" ]]; then
        echo
        echo "PASS: order completed asynchronously"
        exit 0
    fi

    sleep 1

done

echo
echo "FAIL: order did not complete in expected time"
exit 1
