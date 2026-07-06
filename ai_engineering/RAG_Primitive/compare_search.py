import asyncio
import pyarrow as pa
from rag_primitive.storage.lancedb_client import LanceDBClient
from rag_primitive.embedding.model import SpeechEmbedder, SpeechReranker

async def main():
    client = LanceDBClient()
    embedder = SpeechEmbedder()
    query_text = "予算について教えて"
    query_vector = embedder.encode_single(query_text, is_query=True).cpu().numpy().tolist()[0]
    
    print("### 1. Vector Search (ANN/HNSW) ###")
    ann_results = client.search(query_vector, limit=3)
    for i, res in enumerate(ann_results):
        print(f"#{i+1}: {res['speaker']} ({res['date']}) - Dist: {res['_distance']:.4f}")
        print(f"   Content: {res['content'][:100]}...")

    print("\n### 2. Vector Search (Flat) ###")
    # インデックスを一時的に削除して全件スキャンを強制するわ
    client.drop_index()
    flat_results = client.search(query_vector, limit=3)
    for i, res in enumerate(flat_results):
        print(f"#{i+1}: {res['speaker']} ({res['date']}) - Dist: {res['_distance']:.4f}")
        print(f"   Content: {res['content'][:100]}...")
    
    print("\n### 3. Hybrid Search (RRF + Rerank) ###")
    # インデックスを戻さないと FTS が動かないわね
    client.create_fts_index()
    client.create_index("HNSW")
    hybrid_results = client.search_hybrid_manual(query_text, query_vector, limit=3)
    for i, res in enumerate(hybrid_results):
        print(f"#{i+1}: {res['speaker']} ({res['date']}) - Rerank: {res['_rerank_score']:.4f} (RRF: {res['_rrf_score']:.4f})")
        print(f"   Content: {res['content'][:100]}...")

if __name__ == "__main__":
    asyncio.run(main())
