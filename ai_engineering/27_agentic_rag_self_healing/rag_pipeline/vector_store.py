"""
課題27: Agentic RAG with Self-Healing
コンポーネント1-B: インメモリ・ベクトルストア

ここを実装しなさい。
"""
import numpy as np
from openai import AsyncOpenAI
from .ingestion import Chunk


class InMemoryVectorStore:
    """
    NumPyを使ったシンプルなインメモリ・ベクトルストア。
    
    LangChainやChromaDBを使わず、スクラッチでコサイン類似度検索を実装することで、
    「ベクトル検索の本質（内積計算）」を理解し、
    どのベクトルDBを採用するかの技術選定根拠を語れるようにする。
    """

    def __init__(self, client: AsyncOpenAI, embed_model: str):
        self.client = client
        self.embed_model = embed_model
        self.chunks: list[Chunk] = []
        self.vectors: np.ndarray | None = None  # shape: (N, embedding_dim)

    async def add_chunks(self, chunks: list[Chunk]) -> None:
        """
        TODO: チャンクリストをベクトル化して内部ストアに格納しなさい。
        
        ヒント:
        - Embedding APIを呼び出して各チャンクのテキストをベクトル化すること
        - ベクトルをnp.arrayとしてself.vectorsに格納すること
        - API呼び出しは1回にまとめる（バッチ処理）と効率的
        """
        # TODO: ここを実装しなさい
        pass

    async def search(self, query: str, top_k: int = 3) -> list[tuple[Chunk, float]]:
        """
        TODO: クエリに対してコサイン類似度で上位K件のチャンクを返しなさい。
        
        Returns:
            (Chunk, similarity_score) のタプルリスト（スコア降順）
        
        設計上の問い:
        - なぜコサイン類似度なのか？ユークリッド距離との違いは？
        - このインメモリ実装はN件のドキュメントまでスケールするか？
          プロダクションではどのような代替手段（pgvector, Snowflake Cortex等）
          を採用するか？その選定根拠は？
        """
        # TODO: コサイン類似度を自分で実装しなさい（numpy.dotを使ってよい）
        # ヒント: cosine_similarity = dot(a, b) / (norm(a) * norm(b))
        pass

    def _cosine_similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """
        TODO: 2つのベクトル間のコサイン類似度を計算しなさい。
        """
        # TODO: ここを実装しなさい
        pass
