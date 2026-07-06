import re
import json
import logging
from datetime import datetime
from typing import Any, Optional, Tuple, List, Dict
from pydantic import BaseModel, Field, field_validator, ValidationError

# =========
# logging
# =========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LLMIngestionPipeline")

# ==========================================
# テストデータ（LLMから返ってきた不完全なログのモック）
# ==========================================
RAW_LLM_OUTPUTS = [
    # 1. 完全なJSON
    '{"transaction_id": "tx_101", "user_id": "usr_999", "amount": 1500.0, "currency": "JPY", "timestamp": "2026-06-25T15:00:00Z"}',
    
    # 2. マークダウンで囲まれている
    '```json\n{"transaction_id": "tx_102", "user_id": "usr_888", "amount": 2500.5, "currency": "USD", "timestamp": "2026-06-25T15:01:00Z"}\n```',
    
    # 3. 前後に不要な解説テキストがある
    'Here is the extracted transaction: {"transaction_id": "tx_103", "user_id": "usr_777", "amount": 300, "currency": "EUR", "timestamp": "2026-06-25T15:02:00Z"} hope this helps!',
    
    # 4. 末尾の閉じ括弧が欠けている
    '{"transaction_id": "tx_104", "user_id": "usr_666", "amount": 120.0, "currency": "gbp", "timestamp": "2026-06-25T15:03:00Z"',
    
    # 5. 通学小文字、金額が文字列型（自動変換・キャストで救済可能）
    '{"transaction_id": "tx_105", "user_id": "usr_555", "amount": "99.9", "currency": "eur", "timestamp": "2026-06-25T15:04:00Z"}',
    
    # 6. 金額がマイナス（バリデーションエラー -> DLQ）
    '{"transaction_id": "tx_106", "user_id": "usr_444", "amount": -10.0, "currency": "JPY", "timestamp": "2026-06-25T15:05:00Z"}',
    
    # 7. user_idが命名規則違反（バリデーションエラー -> DLQ）
    '{"transaction_id": "tx_107", "user_id": "guest_user", "amount": 450.0, "currency": "USD", "timestamp": "2026-06-25T15:06:00Z"}',
    
    # 8. 完全に壊れたテキスト（修復不能 -> DLQ）
    'I apologize, but I could not find any transaction details in the provided document.'
]


# ==========================================
# 【課題】Pydantic v2モデルの定義
# ==========================================
class TransactionModel(BaseModel):
    """
    取引データのPydantic v2モデル。
    
    【要件】
    1. transaction_id: str型。 "tx_" から始まること（カスタムバリデータで検証）。
    2. user_id: str型。 "^usr_\d+$" の正規表現パターンにマッチすること（カスタムバリデータで検証）。
    3. amount: float型。正の実数（> 0）であること。
    4. currency: str型。 "JPY", "USD", "EUR", "GBP" のいずれかであること。
       ※ 小文字が送られてきた場合は、自動的に大文字に正規化するカスタムバリデータ（Before/Afterは問いません）を実装すること。
    5. timestamp: datetime型（Pydanticが自動でISO文字列をdatetimeオブジェクトにキャストします）。
    """
    # TODO: フィールド定義とPydanticアノテーションを記述しなさい。
    pass

    # TODO: field_validator を実装し、上記のカスタムバリデーションを適用しなさい。


# ==========================================
# 【課題】JSON文字列の自動修復（Auto-Healing）
# ==========================================
def heal_json_string(raw: str) -> str:
    """
    不完全または崩れたJSON文字列を正規表現や文字列操作で可能な限り修復し、
    json.loads可能な文字列にして返しなさい。
    
    【ヒント】
    1. 前後の空白や改行を strip() する。
    2. マークダウンのコードブロック '```json' や '```' を除去する。
    3. 最初の '{' から 最後の '}' を抽出する。
    4. 末尾の '}' が欠損している場合（例えば '{' はあるが末尾が '}' で終わらない場合）に、
       簡易的に '}' を末尾に追加して閉じる。
    """
    # TODO: ここに修復ロジックを実装しなさい。
    return raw


# ==========================================
# 【課題】インジェクションおよびDLQ処理
# ==========================================
def ingest_raw_llm_outputs(
    outputs: List[str]
) -> Tuple[List[TransactionModel], List[Dict[str, Any]]]:
    """
    生のLLM出力リストを1つずつループ処理し、修復と検証を行いなさい。
    正常なレコードは TransactionModel のインスタンスとして Success リストに、
    修復不能または検証エラーになったレコードは DLQ (Dead Letter Queue) リストに格納しなさい。
    
    DLQリストの各要素の辞書形式例:
    {
        "index": インデックス(int),
        "raw_data": 元の生の文字列(str),
        "error_reason": エラーの原因を表す文字列/サマリー(str)
    }
    """
    success_records: List[TransactionModel] = []
    dlq_records: List[Dict[str, Any]] = []

    # TODO: ループ処理、heal_json_string呼び出し、json.loads、Pydanticパース、エラーキャッチを実装しなさい。
    
    return success_records, dlq_records


# =========
# main
# =========
def main():
    logger.info("Starting LLM ingestion pipeline...")
    
    success_records, dlq_records = ingest_raw_llm_outputs(RAW_LLM_OUTPUTS)
    
    logger.info(f"Processed {len(RAW_LLM_OUTPUTS)} records.")
    
    logger.info(f"--- Successfully Ingested ({len(success_records)} records) ---")
    for rec in success_records:
        logger.info(f"- TX: {rec.transaction_id}, User: {rec.user_id}, Amount: {rec.amount} {rec.currency}, Time: {rec.timestamp}")
        
    logger.info(f"--- Dead Letter Queue ({len(dlq_records)} records) ---")
    for dlq in dlq_records:
        logger.info(f"- Record {dlq['index']} Failed: {dlq['error_reason']}")

if __name__ == "__main__":
    main()
