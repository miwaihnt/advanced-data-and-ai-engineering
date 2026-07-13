import re
import asyncio
import math
import time
import logging
from openai import AsyncOpenAI
from typing import List, Tuple

# =========
# logging設定
# =========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SemanticRAG")


# ==========================================
# Ollama Embedding API（nomic-embed-text）
#
# 【mock_embedding_api からの変更点】
# - モックの3次元決め打ちベクトル → Ollama の本物の768次元ベクトル
# - 課題21の qwen2.5:3b と同じく AsyncOpenAI で base_url を Ollama に向ける
# - /v1/embeddings（OpenAI互換エンドポイント）を使うため、書き方が統一できる
#
# 事前準備:
#   ollama pull nomic-embed-text
# ==========================================

# 課題21と同じパターン：base_url を Ollama に向けた AsyncOpenAI クライアント
client = AsyncOpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"  # Ollama 用のダミーキー
)


async def ollama_embedding_api(text: str) -> Tuple[List[float], int]:
    """
    Ollama の nomic-embed-text モデルを使ってテキストをベクトル化する。
    モックと同じシグネチャ（text -> (vector, token_count)）を維持しているため、
    呼び出し元のコードは一切変更不要。
    """
    response = await client.embeddings.create(
        model="nomic-embed-text",
        input=text
    )
    vector = response.data[0].embedding   # 768次元のfloatリスト

    # Ollama embedding API はトークン数を返さないため、モック同様の概算を使う
    token_count = max(5, math.ceil(len(text) / 4))
    return vector, token_count


# ==========================================
# ヘルパー関数: コサイン類似度計算
# （モックの3次元→本物の768次元でも zip ベースの計算は変更不要）
# ==========================================
def calculate_cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """
    2つのベクトルのコサイン類似度を計算する。
    """
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)


# ==========================================
# 非同期用トークンバケット・レートリミッター（変更なし）
# ==========================================
class AsyncTokenBucket:
    def __init__(self, rate: float, capacity: float):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self.lock = asyncio.Lock()

    async def consume(self, amount: float) -> None:
        async with self.lock:
            while True:
                now = time.time()
                elapsed = now - self.last_update
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
                self.last_update = now

                if self.tokens >= amount:
                    self.tokens -= amount
                    return

                needed = amount - self.tokens
                sleep_time = needed / self.rate
                logger.warning(
                    f"[Rate Limit] トークンが不足しています (保有: {self.tokens:.1f}, 要求: {amount}). "
                    f"{sleep_time:.2f}秒待機します..."
                )
                await asyncio.sleep(sleep_time)


# ==========================================
# セマンティックRAGインジェスト（Ollama版）
# mock_embedding_api → ollama_embedding_api に差し替えただけ
# ==========================================
class SemanticRAGPipeline:
    def __init__(self, max_tpm: int, similarity_threshold: float = 0.7):
        self.max_tpm = max_tpm
        self.similarity_threshold = similarity_threshold

    def split_into_sentences(self, text: str) -> List[str]:
        raw_sentences = re.split(r'[。.]', text)
        return [s.strip() for s in raw_sentences if s.strip()]

    async def get_semantic_chunks(self, text: str) -> List[str]:
        sentences = self.split_into_sentences(text)
        if not sentences:
            return []
        if len(sentences) == 1:
            return sentences

        # 各文のベクトルを並行取得（mock → ollama に差し替え）
        tasks = [ollama_embedding_api(s) for s in sentences]
        results = await asyncio.gather(*tasks)
        vectors = [vector for vector, _ in results]

        chunks = []
        current_chunk = [sentences[0]]

        for i in range(len(sentences) - 1):
            sim = calculate_cosine_similarity(vectors[i], vectors[i + 1])
            logger.info(f"文類似度比較: '{sentences[i][:20]}...' vs '{sentences[i+1][:20]}...' = {sim:.4f}")

            if sim < self.similarity_threshold:
                chunks.append(". ".join(current_chunk) + ".")
                current_chunk = [sentences[i + 1]]
            else:
                current_chunk.append(sentences[i + 1])

        if current_chunk:
            chunks.append(". ".join(current_chunk) + ".")

        return chunks

    async def generate_embeddings_with_rate_limit(self, chunks: List[str]) -> List[Tuple[str, List[float]]]:
        rate_per_sec = self.max_tpm / 60.0
        bucket = AsyncTokenBucket(rate=rate_per_sec, capacity=self.max_tpm)

        async def process_chunk(chunk: str) -> Tuple[str, List[float]]:
            estimated_tokens = max(5, math.ceil(len(chunk) / 4))
            await bucket.consume(estimated_tokens)
            # mock → ollama に差し替え
            vector, _ = await ollama_embedding_api(chunk)
            return chunk, vector

        tasks = [process_chunk(chunk) for chunk in chunks]
        return await asyncio.gather(*tasks)


# =========
# main
# =========
async def main():
    document = (
        "Alice has 3 apples. Bob has 2 times as many apples as Alice. "
        "Clara has 4 more apples than Bob and loves eating fresh fruit. "
        "A train leaves Station A travelling at 60 km/h. "
        "Another train leaves Station B travelling at 80 km/h. "
        "The relative speed of the trains is 140 km/h. "
        "Worst database service ever, it crashed my server immediately. "
        "I need to restore the PostgreSQL backups from the remote storage site."
    )

    logger.info("Semantic RAG Pipeline（Ollama版）を開始します...")
    logger.info("※ 事前に `ollama pull nomic-embed-text` が必要です")

    # TPM を大きめに設定（ローカルモデルなので課金制限がない）
    pipeline = SemanticRAGPipeline(max_tpm=10000, similarity_threshold=0.7)

    # 1. セマンティック・チャンキング
    logger.info("\n--- チャンキング開始 ---")
    chunks = await pipeline.get_semantic_chunks(document)
    print("\n--- ✂️ 生成されたセマンティック・チャンク ---")
    for i, chunk in enumerate(chunks, 1):
        print(f"Chunk {i}: {chunk}")

    # 2. レート制限付き並行埋め込み生成
    logger.info("\n--- 埋め込み生成開始 ---")
    start_time = time.time()
    embeddings = await pipeline.generate_embeddings_with_rate_limit(chunks)
    elapsed = time.time() - start_time

    print("\n--- 🔑 埋め込み生成結果 ---")
    for i, (chunk, vector) in enumerate(embeddings, 1):
        # 768次元なので最初の5次元だけ表示
        print(f"Embedding {i}: {chunk[:40]}... -> Vector[:5]: {[round(v, 4) for v in vector[:5]]}")

    print(f"\n総処理時間: {elapsed:.2f} 秒")


if __name__ == "__main__":
    asyncio.run(main())
