import asyncio
from rag_primitive.storage.lancedb_client import LanceDBClient
from rag_primitive.embedding.model import SpeechEmbedder

async def main():
    client = LanceDBClient()
    embedder = SpeechEmbedder()
    query_text = "日本の少子化を止めるための具体的な対策"
    query_vector = embedder.encode_single(query_text, is_query=True).cpu().numpy().tolist()[0]
    
    print("### 1. Vector Search (ANN/HNSW) ###")
    ann_results = client.search(query_vector, limit=3)
    for i, res in enumerate(ann_results):
        print(f"#{i+1}: {res['speaker']} ({res['date']}) - Dist: {res['_distance']:.4f}")
        print(f"   Content: {res['content'][:100]}...")

    print("\n### 2. Full-Text Search (FTS) ###")
    fts_results = client.search_fts(query_text, limit=3)
    for i, res in enumerate(fts_results):
        print(f"#{i+1}: {res['speaker']} ({res['date']}) - Score: {res['_score']:.4f}")
        print(f"   Content: {res['content'][:100]}...")
    
    print("\n### 3. Hybrid Search (RRF + Rerank) ###")
    hybrid_results = client.search_hybrid_manual(query_text, query_vector, limit=3)
    for i, res in enumerate(hybrid_results):
        print(f"#{i+1}: {res['speaker']} ({res['date']}) - Rerank: {res['_rerank_score']:.4f}")
        print(f"   Content: {res['content'][:100]}...")

if __name__ == "__main__":
    asyncio.run(main())
