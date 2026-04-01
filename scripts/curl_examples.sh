#!/bin/bash
# Sample cURL client for Mock Interview AI API
# Start the API first: python main.py  OR  uvicorn main:app --reload

BASE="http://localhost:8000"

echo "=== 1. Get first question (Behavioral) ==="
curl -s -X POST "$BASE/ask_question" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"s1","user_id":"u1","mode":"behavioral"}' | jq .

echo ""
echo "=== 2. Get follow-up question ==="
curl -s -X POST "$BASE/ask_question" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id":"s1","user_id":"u1","mode":"behavioral",
    "last_question":"Tell me about a time you dealt with a difficult teammate.",
    "last_answer":"I had a teammate who missed deadlines. I scheduled a 1:1 to understand blockers and we agreed on daily standups."
  }' | jq .

echo ""
echo "=== 3. Evaluate response ==="
curl -s -X POST "$BASE/evaluate" \
  -H "Content-Type: application/json" \
  -d '{
    "question":"Tell me about a time you showed leadership.",
    "answer":"In my last project I led the backend team. I set up weekly syncs and we delivered on time.",
    "mode":"behavioral"
  }' | jq .

echo ""
echo "=== 4. Save event to memory ==="
curl -s -X POST "$BASE/memory/save" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id":"s1","user_id":"u1","event_type":"qa_pair",
    "content":{"question":"Q1","answer":"A1"}
  }' | jq .

echo ""
echo "=== 5. Recall context ==="
curl -s -X POST "$BASE/memory/recall" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"s1","user_id":"u1","limit":5}' | jq .
