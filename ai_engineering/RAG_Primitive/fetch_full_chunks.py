import asyncio
from rag_primitive.storage.lancedb_client import LanceDBClient
from rag_primitive.embedding.model import SpeechEmbedder

async def main():
    client = LanceDBClient()
    embedder = SpeechEmbedder()
    query_text = "日本の少子化を止めるための具体的な対策"
    query_vector = embedder.encode_single(query_text, is_query=True).cpu().numpy().tolist()[0]
    
    # 全手法の結果を統合してユニークなIDを抽出
    results = []
    results.extend(client.search(query_vector, limit=3))
    results.extend(client.search_fts(query_text, limit=3))
    results.extend(client.search_hybrid_manual(query_text, query_vector, limit=3))
    
    unique_chunks = {}
    for res in results:
        cid = res['chunk_id']
        if cid not in unique_chunks:
            unique_chunks[cid] = res

    for cid, res in unique_chunks.items():
        print(f"--- CHUNK_START: {res['speaker']} ({res['date']}) ---")
        print(res['content'])
        print(f"--- CHUNK_END ---")

if __name__ == "__main__":
    asyncio.run(main())
