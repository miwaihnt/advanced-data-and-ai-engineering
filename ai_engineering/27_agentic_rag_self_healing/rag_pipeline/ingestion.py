"""
課題27: Agentic RAG with Self-Healing
コンポーネント1-A: ドキュメント分割・チャンキング

ここを実装しなさい。
"""
from dataclasses import dataclass


@dataclass
class Chunk:
    """分割されたドキュメントの単位"""
    chunk_id: str    # 例: "chunk_001"
    text: str        # チャンクのテキスト本文
    source: str      # 元ドキュメントのソース名


def split_document(
    text: str,
    source: str,
    chunk_size: int = 200,
    chunk_overlap: int = 20,
) -> list[Chunk]:
    """
    TODO: テキストを固定長チャンクに分割する関数を実装しなさい。
    
    Args:
        text: 分割対象のテキスト
        source: ソース文書の名前（メタデータとしてChunkに付与）
        chunk_size: 各チャンクの最大文字数
        chunk_overlap: 連続するチャンク間の重複文字数（文脈の連続性を保つため）
    
    Returns:
        Chunkオブジェクトのリスト
    
    設計上の問い:
        - なぜ chunk_overlap が必要なのか？
        - 固定長チャンキングの代替手法（セマンティックチャンキング等）と
          のトレードオフは何か？
    """
    # TODO: ここを実装しなさい
    pass
