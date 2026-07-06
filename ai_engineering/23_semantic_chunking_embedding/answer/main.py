import re
import asyncio
import math
import time
import logging
from typing import Any, Dict, List, Tuple

# =========
# logging設定
# =========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SemanticRAG")


# ==========================================
# Mock Embedding API (書き換えないでください)
# ==========================================
async def mock_embedding_api(text: str) -> Tuple[List[float], int]:
    """
    疑似ベクトルと消費トークン数を返す模擬Embedding API。
    I/O遅延として 50ms 待機する。
    """
    await asyncio.sleep(0.05)
    
    # 簡易トークンカウント（文字数に基づく概算）
    token_count = max(5, math.ceil(len(text) / 4))

    # テキストの意味に応じた3次元の疑似ベクトルを生成
    text_lower = text.lower()
    if "apple" in text_lower or "fruit" in text_lower or "clara" in text_lower:
        # 果物系
        vector = [0.95, 0.10, 0.05]
    elif "train" in text_lower or "speed" in text_lower or "station" in text_lower:
        # 移動・交通系
        vector = [0.05, 0.90, 0.15]
    elif "database" in text_lower or "crashed" in text_lower or "server" in text_lower:
        # IT・インフラ系
        vector = [0.10, 0.20, 0.85]
    else:
        # 一般
        vector = [0.50, 0.50, 0.50]

    return vector, token_count


# ==========================================
# ヘルパー関数: コサイン類似度計算
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
# 非同期用トークンバケット・レートリミッター
# ==========================================
class AsyncTokenBucket:
    def __init__(self, rate: float, capacity: float):
        """
        Args:
            rate (float): 1秒間に補充されるトークン数。
            capacity (float): バケットの最大容量。
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self.lock = asyncio.Lock()

    async def consume(self, amount: float) -> None:
        """
        指定されたトークン量を消費する。足りない場合は充足するまで非同期スリープする。
        複数の並行タスクが同時に判定してもバグらないよう、asyncio.Lock を用いる。
        """
        async with self.lock:
            while True:
                now = time.time()
                elapsed = now - self.last_update
                
                # トークンの補充（Lazy Replenishment）
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
                self.last_update = now

                if self.tokens >= amount:
                    self.tokens -= amount
                    return

                # 足りないトークン数から必要なスリープ時間を逆算する
                needed = amount - self.tokens
                sleep_time = needed / self.rate
                logger.warning(
                    f"[Rate Limit] トークンが不足しています (保有: {self.tokens:.1f}, 要求: {amount}). "
                    f"{sleep_time:.2f}秒待機します..."
                )
                await asyncio.sleep(sleep_time)


# ==========================================
# 【模範解答】セマンティックRAGインジェストの実装
# ==========================================
class SemanticRAGPipeline:
    def __init__(self, max_tpm: int, similarity_threshold: float = 0.7):
        """
        Args:
            max_tpm (int): 1分間(60秒)に送信できる最大トークン数(Tokens Per Minute)。
            similarity_threshold (float): これを下回った場合にチャンクを分割するしきい値。
        """
        self.max_tpm = max_tpm
        self.similarity_threshold = similarity_threshold

    def split_into_sentences(self, text: str) -> List[str]:
        """
        入力テキストを「。」または「.」で文章（文）に分解する。
        """
        # 正規表現で句点とピリオドで分割
        raw_sentences = re.split(r'[。.]', text)
        # 空白・空文字を除外し、前後の余白をトリム
        return [s.strip() for s in raw_sentences if s.strip()]

    async def get_semantic_chunks(self, text: str) -> List[str]:
        """
        入力テキストを類似度に基づき結合し、セマンティックチャンクを生成する。
        """
        sentences = self.split_into_sentences(text)
        if not sentences:
            return []
        if len(sentences) == 1:
            return sentences

        # 各文のベクトルを並行して取得（ここでは一時的なAPI制限は考慮せず並行取得して良いとする）
        tasks = [mock_embedding_api(s) for s in sentences]
        results = await asyncio.gather(*tasks)
        vectors = [vector for vector, _ in results]

        chunks = []
        current_chunk = [sentences[0]]

        # 隣り合う文章間のコサイン類似度を算出
        for i in range(len(sentences) - 1):
            sim = calculate_cosine_similarity(vectors[i], vectors[i + 1])
            logger.info(f"文類似度比較: '{sentences[i][:15]}...' vs '{sentences[i+1][:15]}...' = {sim:.3f}")
            
            if sim < self.similarity_threshold:
                # 類似度がしきい値未満なら、現在のチャンクを結合してリストへ追加し、新チャンクを開始
                chunks.append(". ".join(current_chunk) + ".")
                current_chunk = [sentences[i + 1]]
            else:
                current_chunk.append(sentences[i + 1])

        if current_chunk:
            chunks.append(". ".join(current_chunk) + ".")

        return chunks

    async def generate_embeddings_with_rate_limit(self, chunks: List[str]) -> List[Tuple[str, List[float]]]:
        """
        チャンクのリストを受け取り、TPM制限を遵守しながら並行処理で埋め込みを生成する。
        """
        # TPMを1秒あたりの補充レートに換算
        rate_per_sec = self.max_tpm / 60.0
        bucket = AsyncTokenBucket(rate=rate_per_sec, capacity=self.max_tpm)

        async def process_chunk(chunk: str) -> Tuple[str, List[float]]:
            # トークン数の見積もり
            estimated_tokens = max(5, math.ceil(len(chunk) / 4))
            
            # トークンバケットから必要トークン量を消費（足りなければ自動スリープ）
            await bucket.consume(estimated_tokens)
            
            # 実際のAPIリクエストの送信
            vector, _ = await mock_embedding_api(chunk)
            return chunk, vector

        # asyncio.gatherで全チャンクを並行して実行予約する（バケットがスリープで適切に流量制御する）
        tasks = [process_chunk(chunk) for chunk in chunks]
        return await asyncio.gather(*tasks)


# =========
# main
# =========
async def main():
    # 途中でトピックが「果物」から「列車（交通）」、「ITサーバー」へ劇的に遷移する長文テキスト
    document = (
        "Alice has 3 apples. Bob has 2 times as many apples as Alice. "
        "Clara has 4 more apples than Bob and loves eating fresh fruit. "
        "A train leaves Station A travelling at 60 km/h. "
        "Another train leaves Station B travelling at 80 km/h. "
        "The relative speed of the trains is 140 km/h. "
        "Worst database service ever, it crashed my server immediately. "
        "I need to restore the PostgreSQL backups from the remote storage site."
    )

    logger.info("Semantic RAG Pipelineを開始します...")
    
    # テスト用に非常に小さな TPM（50トークン/分）を設定し、レート制限がかかり待機が発生することを確認する
    pipeline = SemanticRAGPipeline(max_tpm=50, similarity_threshold=0.7)

    # 1. セマンティック・チャンキングの実行
    chunks = await pipeline.get_semantic_chunks(document)
    print("\n--- ✂️ 生成されたセマンティック・チャンク ---")
    for i, chunk in enumerate(chunks, 1):
        print(f"Chunk {i}: {chunk}")

    # 2. レート制限付き並行埋め込み生成
    start_time = time.time()
    embeddings = await pipeline.generate_embeddings_with_rate_limit(chunks)
    elapsed = time.time() - start_time

    print("\n--- 🔑 埋め込み生成結果 ---")
    for i, (chunk, vector) in enumerate(embeddings, 1):
        print(f"Embedding {i}: {chunk[:30]}... -> Vector: {vector}")

    print(f"\n総処理時間: {elapsed:.2f} 秒 (TPM制限によるスリープを含む)")


if __name__ == "__main__":
    asyncio.run(main())
