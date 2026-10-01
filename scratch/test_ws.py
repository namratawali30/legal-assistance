import sys
sys.path.insert(0, r"D:\112\backend")

from app.rag.retriever import search_legal_chunks
from app.rag.confidence import evaluate_retrieval_confidence

query = "Where can a woman residing in a shared household file an application for residence orders under DV Act?"
results = search_legal_chunks(query=query, top_k=5, category="womens_safety")
print("RESULTS COUNT:", len(results))
for r in results:
    print(r.get("source_id"), r.get("provision_number"), r.get("score"))

conf = evaluate_retrieval_confidence(results)
print("CONFIDENCE:", conf)
