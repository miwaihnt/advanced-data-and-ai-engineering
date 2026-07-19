"""
課題27: Agentic RAG with Self-Healing
コンポーネント2: Pydanticスキーマ定義

ここを実装しなさい。
"""
from pydantic import BaseModel, Field


class RAGResponse(BaseModel):
    """
    TODO: LLMから返ってくる回答を型安全に受け取るためのスキーマを定義しなさい。
    
    フィールド:
    - answer: ユーザーへの最終回答
    - sources: 回答の根拠となったchunk_idのリスト（必ず1件以上）
    - confidence: 根拠の確かさへの自己評価スコア（0.0〜1.0）
    - needs_retry: 品質が不十分で再検索が必要な場合はTrue
    """
    pass  # TODO: ここを実装しなさい


class FallbackResponse(BaseModel):
    """最大リトライ回数に達した際のフォールバックレスポンス"""
    message: str
    total_retries: int
    last_confidence: float | None = None
