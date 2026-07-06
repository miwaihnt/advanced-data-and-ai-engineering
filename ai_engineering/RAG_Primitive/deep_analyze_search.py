import asyncio
from rag_primitive.storage.lancedb_client import LanceDBClient
from rag_primitive.embedding.model import SpeechEmbedder

async def main():
    client = LanceDBClient()
    embedder = SpeechEmbedder()
    query_text = "日本の少子化を止めるための具体的な対策"
    query_vector = embedder.encode_single(query_text, is_query=True).cpu().numpy().tolist()[0]
    
    # 1. 真理 (Flat Vector Search) を取得
    print("Fetching Ground Truth (Flat Vector Search)...")
    client.drop_index() # インデックスを削除して全件スキャンを強制
    flat_results = client.search(query_vector, limit=500) # 広めに取る
    flat_map = {res['chunk_id']: (i+1, res['_distance']) for i, res in enumerate(flat_results)}

    # 2. ハイブリッド検索 (RRF + Rerank) を実行
    print("Executing Hybrid + Rerank Search...")
    client.create_fts_index() # FTSのためにインデックス再構築
    client.create_index("HNSW")
    hybrid_results = client.search_hybrid_manual(query_text, query_vector, limit=3)

    print("\n" + "="*80)
    print(f"QUERY: {query_text}")
    print("="*80)
    print(f"{'Rank':<10} | {'Speaker':<15} | {'Rerank Score':<12} | {'Flat Vector Rank':<18} | {'Flat Dist':<10}")
    print("-" * 80)
    
    for i, res in enumerate(hybrid_results):
        cid = res['chunk_id']
        # Flat検索の順位と距離をマップから引く（500位以下は >500）
        v_rank, v_dist = flat_map.get(cid, (">500", 1.0))
        
        print(f"Hybrid #{i+1:<2} | {res['speaker']:<15} | {res['_rerank_score']:<12.4f} | {v_rank:<18} | {v_dist:<10.4f}")

    print("="*80)
    print("\n### Note: Flat Vector Search #1 (The one Hybrid 'rejected') ###")
    top_flat = flat_results[0]
    print(f"Flat #1: {top_flat['speaker']} (Dist: {top_flat['_distance']:.4f})")
    print(f"Content: {top_flat['content'][:100]}...")

if __name__ == "__main__":
    asyncio.run(main())
