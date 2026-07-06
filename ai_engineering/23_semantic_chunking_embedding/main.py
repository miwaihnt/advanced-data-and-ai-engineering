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
# 【課題】セマンティックRAGインジェストの実装
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
        （末尾の空文字や空白はトリムして除外すること）。
        """
        # TODO: 文境界の分割処理を実装しなさい。
        pass

    async def get_semantic_chunks(self, text: str) -> List[str]:
        """
        入力テキストを文に分解し、隣り合う文どうしのコサイン類似度を計算して
        しきい値未満となった境界でテキストを結合した「チャンクのリスト」を生成する。
        
        【重要】文ごとのベクトル取得も、並行して mock_embedding_api を叩くのが望ましい。
        """
        # TODO: コサイン類似度を用いたセマンティック分割ロジックを実装しなさい。
        pass

    async def generate_embeddings_with_rate_limit(self, chunks: List[str]) -> List[Tuple[str, List[float]]]:
        """
        チャンクのリストを受け取り、非同期・並行で `mock_embedding_api` を叩いて
        (チャンクテキスト, ベクトル) のタプルのリストを返す。
        
        【レートリミット制約】
        - 1分間（60秒）の累積トークン数が `self.max_tpm` を超えないよう、
          送信前に累積トークンを監視し、トークン枠が空くまで非同期で待機（sleep）させなさい。
          （ヒント: トークン補充の計算は前回のアクセス時間からの経過秒数を用いてLazyに行うのが効率的です。）
        """
        # TODO: TPM制御付きの並行埋め込み生成ロジックを実装しなさい。
        pass


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
