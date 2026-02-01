#!/usr/bin/env python3
import json
import urllib.request

req = urllib.request.Request('http://localhost:8000/api/query', method='POST')
req.add_header('Content-Type','application/json')
body = json.dumps({
  'question':'האם מתוכננת תחנה של מטרו בשכונת נחלת יהודה, האם יש תמונה של מיקום התחנה',
  'top_k':10,
  'search_mode':'hybrid',
  'semantic_ranker':True,
  'min_score':0,
  'content_type_filter':'all',
  'retrieval_strategy':'hybrid'
}).encode('utf-8')

with urllib.request.urlopen(req, data=body, timeout=60) as resp:
    data = json.loads(resp.read().decode('utf-8'))

print('Total sources:', len(data['sources']))
for i, src in enumerate(data['sources']):
    print(f"{i+1}. type={src['content_type']}, page={src['page_numbers']}, has_image={bool(src.get('image_sas_url'))}")
