#!/usr/bin/env python3
"""Quick test script for the combined query API."""
import json
import sys
import urllib.request

question = (
    'התבסס על מפת קו M1, דוח תחנה 36 וקובץ הנתונים הטבלאי: '
    '1. האם ניתן להגיע מתחנה 36 "שדרות הציונות" לתחנה "הראשונים" מבלי לעבור בתחנה שנמצאת על שלוחה? '
    '2. מהו המסלול המדויק (רשימת תחנות לפי סדר)? '
    '3. האם קיימות תכניות מקודמות ברדיוס 800 מ\' לאורך כל המסלול הזה? '
    '4. איזו תחנה במסלול כוללת מעבר הולכי רגל תת-קרקעי שאינו מחייב כניסה למטרו?'
)

payload = json.dumps({"question": question, "strategy": "combined"}).encode("utf-8")
req = urllib.request.Request(
    "http://localhost:8000/api/query",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=180) as resp:
    data = json.loads(resp.read().decode("utf-8"))

print("=== ANSWER ===")
print(data.get("answer", ""))
print()

# Show individual strategy results if available
combined = data.get("combined_results", {})
if combined:
    if combined.get("search_answer"):
        print("\n=== DRAFT A (AI Search) ===")
        print(combined["search_answer"])
    if combined.get("graphrag_answer"):
        print("\n=== DRAFT B (GraphRAG) ===")
        print(combined["graphrag_answer"])

print("\n=== SOURCES ===")
for s in data.get("sources", []):
    print(f"  - {s.get('source_document', '')} ({s.get('content_type', '')})")
