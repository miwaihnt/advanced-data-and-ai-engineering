"""
課題28: 自律テスト・修復マルチエージェント
コンポーネント1: Pydanticスキーマ定義

ここを実装しなさい。
"""
from pydantic import BaseModel, Field


class CodeModification(BaseModel):
    """
    Coder Agentが生成するコード修正の構造
    """
    explanation: str = Field(..., description="どのような修正を行ったかの解説")
    fixed_code: str = Field(..., description="修正されたtarget_code.pyの全ソースコード。Markdownのコードブロックは含めず、純粋なPythonコードのみを出力すること。")


class ReviewResult(BaseModel):
    """
    Reviewer Agentが生成するレビュー結果の構造
    """
    approved: bool = Field(..., description="修正コードがレビュー基準をクリアしている場合はTrue、修正が必要な場合はFalse")
    feedback: str = Field(..., description="レビューのフィードバック詳細。不合格の場合は具体的な修正指示、合格の場合はその理由。")


class ScientistReport(BaseModel):
    """
    最終的な自律修復結果のレポート
    """
    success: bool = Field(..., description="テストがすべてパスした場合はTrue、最大リトライに達しても失敗した場合はFalse")
    total_iterations: int = Field(..., description="実行された修正・検証のループ回数")
    final_code: str = Field(..., description="最終的なソースコード")
    modification_history: list[str] = Field(..., description="各イテレーションでの試行履歴とエラー内容")
