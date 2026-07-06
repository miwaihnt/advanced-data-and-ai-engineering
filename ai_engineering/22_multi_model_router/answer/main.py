import time
import json
import logging
from typing import Any, Dict, Optional, Tuple
from pydantic import BaseModel, Field, ValidationError

# =========
# logging設定
# =========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MultiModelRouter")


# ==========================================
# Pydantic スキーマ定義
# ==========================================
class AnalysisResult(BaseModel):
    sentiment: str = Field(description="Must be 'positive', 'negative', or 'neutral'")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    reasoning: str = Field(min_length=10, description="Detailed explanation of at least 10 characters")


# ==========================================
# Mock LLM API (書き換えないでください)
# ==========================================
def mock_cheap_llm(user_input: str) -> Tuple[str, Dict[str, int]]:
    """
    安価なモデルを模倣するAPI。時折不正な構造や値を返す。
    コスト: Input $0.00015 / 1k tokens, Output $0.0006 / 1k tokens
    """
    # 応答時間シミュレーション
    time.sleep(0.1)

    metrics = {"input_tokens": 120, "output_tokens": 80}

    if "love" in user_input:
        # スキーマ違反：sentimentの値が不正、confidenceが範囲外、reasoningが短すぎる
        bad_json = '{"sentiment": "very positive", "confidence": 1.5, "reasoning": "Fast"}'
        return bad_json, metrics
    elif "crashed" in user_input:
        # JSONデコード違反：単なるテキスト（JSONになっていない）
        bad_text = "This is a negative review because the server crashed."
        return bad_text, metrics
    else:
        # 正常な回答
        good_json = '{"sentiment": "neutral", "confidence": 0.60, "reasoning": "The user description indicates it works but is nothing special."}'
        return good_json, metrics


def mock_expensive_llm(user_input: str) -> Tuple[str, Dict[str, int]]:
    """
    高価なモデルを模倣するAPI。常に正しい構造化データを返す。
    コスト: Input $0.003 / 1k tokens, Output $0.015 / 1k tokens
    """
    time.sleep(0.3) # 高価格モデルは推論時間がやや長い

    metrics = {"input_tokens": 250, "output_tokens": 120}

    if "love" in user_input:
        return '{"sentiment": "positive", "confidence": 0.98, "reasoning": "The user expresses high enthusiasm about the database\'s performance."}', metrics
    elif "crashed" in user_input:
        return '{"sentiment": "negative", "confidence": 0.99, "reasoning": "The customer reports server crashes and severe dissatisfaction."}', metrics
    else:
        return '{"sentiment": "neutral", "confidence": 0.55, "reasoning": "Decent sentiment but lacks excitement."}', metrics


# ==========================================
# 【模範解答】自動フォールバック付きルーターの実実装
# ==========================================
class MultiModelRouter:
    """
    LLMリクエストのコストと精度を最適化するインテリジェント・ルーター。
    """
    # 料金定義（1トークンあたりのドル単価）
    PRICE_CHEAP_INPUT = 0.00015 / 1000
    PRICE_CHEAP_OUTPUT = 0.0006 / 1000
    PRICE_EXPENSIVE_INPUT = 0.003 / 1000
    PRICE_EXPENSIVE_OUTPUT = 0.015 / 1000

    def __init__(self):
        pass

    def route_and_validate(self, user_input: str) -> Tuple[AnalysisResult, Dict[str, Any]]:
        """
        ユーザーの入力に対し、自動フォールバックと精度/コスト集計を行う。
        """
        start_time = time.time()
        
        # 1. CheapModelの呼び出し
        cheap_output, cheap_metrics = mock_cheap_llm(user_input)
        
        # CheapModelのコスト計算
        cost_cheap = (
            (cheap_metrics["input_tokens"] * self.PRICE_CHEAP_INPUT) +
            (cheap_metrics["output_tokens"] * self.PRICE_CHEAP_OUTPUT)
        )

        try:
            # 2. Pydanticスキーマ検証（CheapModelの出力）
            result = AnalysisResult.model_validate_json(cheap_output)
            latency = time.time() - start_time
            
            # 成功レポートの作成
            report = {
                "model": "CheapModel",
                "latency": latency,
                "tokens": {"CheapModel": cheap_metrics},
                "cost": cost_cheap
            }
            return result, report

        except (ValidationError, json.JSONDecodeError) as e:
            # 3. 検証失敗時の警告ログとフォールバックの実行
            logger.warning(
                f"[Validation Failed] CheapModel output validation failed with error: {e}. "
                f"Falling back to ExpensiveModel..."
            )
            
            # 4. ExpensiveModelの呼び出し
            expensive_output, exp_metrics = mock_expensive_llm(user_input)
            
            # ExpensiveModelのコスト計算
            cost_expensive = (
                (exp_metrics["input_tokens"] * self.PRICE_EXPENSIVE_INPUT) +
                (exp_metrics["output_tokens"] * self.PRICE_EXPENSIVE_OUTPUT)
            )

            # ExpensiveModelの出力を検証（もしこれで失敗したら呼び出し元へそのまま例外を投げる）
            result = AnalysisResult.model_validate_json(expensive_output)
            
            latency = time.time() - start_time
            
            # 二陣合計のコストとトークン集計レポート
            report = {
                "model": "ExpensiveModel",
                "latency": latency,
                "tokens": {
                    "CheapModel": cheap_metrics,
                    "ExpensiveModel": exp_metrics
                },
                "cost": cost_cheap + cost_expensive
            }
            return result, report


# =========
# main
# =========
def main():
    router = MultiModelRouter()
    
    test_inputs = [
        "I absolutely love this new database! It is incredibly fast.",   # Cheapモデルがスキーマ検証エラーを起こすケース
        "This is okay, nothing special but works.",                     # Cheapモデルが一撃で合格するケース
        "Worst service ever, it crashed my server immediately!"          # Cheapモデルが非JSONエラーを起こすケース
    ]

    for idx, text in enumerate(test_inputs, 1):
        print(f"\n--- 📝 テストケース {idx} ---")
        print(f"入力: {text}")
        
        try:
            result, report = router.route_and_validate(text)
            print("\n[✔] 成功レポート:")
            print(f"  使用モデル: {report['model']}")
            print(f"  総実行時間: {report['latency']:.3f} 秒")
            print(f"  消費トークン: {report['tokens']}")
            print(f"  総APIコスト: ${report['cost']:.6f}")
            print(f"  解析結果データ: {result}")
            
        except Exception as e:
            logger.error(f"致命的なエラーで処理が失敗しました: {e}", exc_info=True)


if __name__ == "__main__":
    main()
