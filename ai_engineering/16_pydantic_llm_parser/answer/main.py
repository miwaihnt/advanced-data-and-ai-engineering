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
    
    # 5. 通貨が小文字、金額が文字列型（自動変換・キャストで救済可能）
    '{"transaction_id": "tx_105", "user_id": "usr_555", "amount": "99.9", "currency": "eur", "timestamp": "2026-06-25T15:04:00Z"}',
    
    # 6. 金額がマイナス（バリデーションエラー -> DLQ）
    '{"transaction_id": "tx_106", "user_id": "usr_444", "amount": -10.0, "currency": "JPY", "timestamp": "2026-06-25T15:05:00Z"}',
    
    # 7. user_idが命名規則違反（バリデーションエラー -> DLQ）
    '{"transaction_id": "tx_107", "user_id": "guest_user", "amount": 450.0, "currency": "USD", "timestamp": "2026-06-25T15:06:00Z"}',
    
    # 8. 完全に壊れたテキスト（修復不能 -> DLQ）
    'I apologize, but I could not find any transaction details in the provided document.'
]


# ==========================================
# 【模範解答】Pydantic v2モデルの定義
# ==========================================
class TransactionModel(BaseModel):
    """
    取引データのPydantic v2モデル。
    """
    transaction_id: str
    user_id: str
    amount: float = Field(gt=0)
    currency: str
    timestamp: datetime

    @field_validator("transaction_id")
    @classmethod
    def validate_transaction_id(cls, v: str) -> str:
        if not v.startswith("tx_"):
            raise ValueError("transaction_id must start with 'tx_'")
        return v

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        if not re.match(r"^usr_\d+$", v):
            raise ValueError("user_id must match pattern 'usr_\\d+'")
        return v

    @field_validator("currency")
    @classmethod
    def validate_and_normalize_currency(cls, v: str) -> str:
        v_upper = v.upper()
        if v_upper not in {"JPY", "USD", "EUR", "GBP"}:
            raise ValueError(f"Unsupported currency: {v}. Must be JPY, USD, EUR, or GBP")
        return v_upper


# ==========================================
# 【模範解答】JSON文字列の自動修復（Auto-Healing）
# ==========================================
def heal_json_string(raw: str) -> str:
    """
    不完全または崩れたJSON文字列を正規表現や文字列操作で可能な限り修復し、
    json.loads可能な文字列にして返す。
    """
    # 1. 前後の空白・改行を除去
    cleaned = raw.strip()
    
    # 2. マークダウンのコードブロック除去 (```json または ```)
    cleaned = re.sub(r"^```(?:json)?\n", "", cleaned)
    cleaned = re.sub(r"\n```$", "", cleaned)
    cleaned = cleaned.strip()

    # 3. 最初の '{' から 最後の '}' を抽出する
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    
    if first_brace != -1:
        if last_brace != -1 and last_brace > first_brace:
            cleaned = cleaned[first_brace:last_brace + 1]
        else:
            # '{' はあるが '}' が無い、または '{' より前にある場合（末尾閉じ括弧欠損）
            # その場合、'{' から文字列の最後までを取り出して、末尾に '}' を付加する
            cleaned = cleaned[first_brace:] + "}"
            
    return cleaned


# ==========================================
# 【模範解答】インジェクションおよびDLQ処理
# ==========================================
def ingest_raw_llm_outputs(
    outputs: List[str]
) -> Tuple[List[TransactionModel], List[Dict[str, Any]]]:
    """
    生のLLM出力リストを1つずつループ処理し、修復と検証を行う。
    """
    success_records: List[TransactionModel] = []
    dlq_records: List[Dict[str, Any]] = []

    for index, raw in enumerate(outputs):
        try:
            # 1. 自動修復
            healed = heal_json_string(raw)
            # 2. JSONパース
            parsed = json.loads(healed)
            # 3. Pydanticモデルによるバリデーションとインスタンス化
            model = TransactionModel(**parsed)
            success_records.append(model)
        except json.JSONDecodeError as e:
            dlq_records.append({
                "index": index,
                "raw_data": raw,
                "error_reason": f"JSON Decode Error: {str(e)}"
            })
        except ValidationError as e:
            # Pydantic v2 の検証エラーメッセージを綺麗にフォーマット
            error_msgs = []
            for err in e.errors():
                loc = ".".join(str(x) for x in err["loc"])
                msg = err["msg"]
                error_msgs.append(f"{loc}: {msg}")
            reason = "Validation Error: " + ", ".join(error_msgs)
            
            dlq_records.append({
                "index": index,
                "raw_data": raw,
                "error_reason": reason
            })
        except Exception as e:
            dlq_records.append({
                "index": index,
                "raw_data": raw,
                "error_reason": f"Unexpected Error: {str(e)}"
            })
    
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
