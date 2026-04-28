import requests
import json

url = "http://localhost:8000/research"
payload = {
  "query": "Fake profile detection",
  "search_top_n": 1,
  "reranker_top_k": 1,
  "retriever_top_k": 1,
  "refinement_iterations": 3
}

try:
    response = requests.post(url, json=payload, timeout=180)
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")
