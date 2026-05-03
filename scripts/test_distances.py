from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import euclidean_distances

model = SentenceTransformer("all-MiniLM-L6-v2")

texts = [
    "always uses Kubernetes for orchestration",
    "always uses helm charts for deployment",
    "prefers building APIs with Python",
    "prefers FastAPI for backend",
    "never skip code reviews before merging",
    "always mandates PR reviews"
]

embs = model.encode(texts)
dist = euclidean_distances(embs)

for i in range(len(texts)):
    for j in range(i+1, len(texts)):
        print(f"Dist between '{texts[i]}' AND '{texts[j]}': {dist[i,j]:.2f}")
