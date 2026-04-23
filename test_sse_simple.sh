#!/bin/bash
# Simple SSE test using curl with background WS sender

SESSION_ID="ws_test_$(date +%s)"
WALLET="test_user"

echo "=== SSE Debug Test ==="
echo "Session: $SESSION_ID"
echo ""

# Start SSE in background
curl -N -s "http://localhost:8000/api/meta-agent/sse/chat/${WALLET}?session_id=${SESSION_ID}" \
  --max-time 5 \
  -H "Accept: text/event-stream" \
  -D /tmp/sse_headers.txt \
  2>&1 &
CURL_PID=$!

echo "Curl PID: $CURL_PID"
sleep 2

# Check SSE headers
echo "=== SSE Headers ==="
cat /tmp/sse_headers.txt
echo ""

# Check if curl is still running
if kill -0 $CURL_PID 2>/dev/null; then
    echo "✅ SSE connection established (curl still running)"
else
    echo "❌ SSE connection closed immediately"
fi

# Kill curl
kill $CURL_PID 2>/dev/null

echo ""
echo "=== Test Complete ==="
