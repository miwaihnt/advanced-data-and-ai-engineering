import json
import logging
from dataclasses import dataclass
from pathlib import Path
from collections import defaultdict
from typing import Any, Iterable, Dict

# ===========
# configの設定 
# ===========
# デフォルトパス（検証・実行用）
transaction_file = Path.cwd() / "input/transaction.jsonl"
user_file = Path.cwd() / "input/users.jsonl"

# ===========
# loggerの設定 
# ===========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ===========
# userのdata class
# ===========
@dataclass(frozen=True)
class User:
    user_id: str
    country: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "User":
        # 必須キーのチェック
        for key in ("user_id", "country"):
            if key not in data:
                raise ValueError(f"必須キー '{key}' がありません")
        
        # 型チェック
        uid = data["user_id"]
        country = data["country"]
        if not isinstance(uid, str):
            raise TypeError(f"user_id は str である必要があります（入力: {type(uid).__name__}）")
        if not isinstance(country, str):
            raise TypeError(f"country は str である必要があります（入力: {type(country).__name__}）")
        
        return cls(user_id=uid, country=country)


# ===========
# transactionのdata class
# ===========
@dataclass(frozen=True)
class Transaction:
    user_id: str
    amount: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Transaction":
        # 必須キーのチェック
        for key in ("user_id", "amount"):
            if key not in data:
                raise ValueError(f"必須キー '{key}' がありません")
        
        # 型チェック
        uid = data["user_id"]
        amount = data["amount"]
        if not isinstance(uid, str):
            raise TypeError(f"user_id は str である必要があります（入力: {type(uid).__name__}）")
        if not isinstance(amount, int):
            raise TypeError(f"amount は int である必要があります（入力: {type(amount).__name__}）")
        
        return cls(user_id=uid, amount=amount)


# ==========================================
# イテレータを受け取り、結合と集計を行うビジネスロジック
# ==========================================
def aggregate_by_country(
    transactions: Iterable[dict[str, Any]], 
    users: Iterable[dict[str, Any]]
) -> dict[str, int]:
    """
    ユーザーマスターとトランザクションデータを結合し、国別の合計金額を算出する。
    時間計算量: O(N + M)  (N: transactionsの要素数, M: usersの要素数)
    空間計算量: O(M)      (user_map のサイズ)
    """
    user_map: dict[str, str] = {}

    # 1. ユーザーマスターをハッシュマップ化 (O(M))
    for user_data in users:
        try:
            user = User.from_dict(user_data)
            user_map[user.user_id] = user.country
        # ユーザーデータのバリデーションエラーのハンドリング
        except (ValueError, TypeError) as e:
            logger.warning(f"[Skip] ユーザーマスタのバリデーションに失敗しました: {e}")

    # 2. トランザクションを集計 (O(N))
    agg_transaction = defaultdict(int)
    for tx_data in transactions:
        try:
            tx = Transaction.from_dict(tx_data)
            # user_mapからuidを検索する。なければ、Unknownにする 
            country = user_map.get(tx.user_id, "Unknown")
            agg_transaction[country] += tx.amount
        except (ValueError, TypeError) as e:
            logger.warning(f"[Skip] トランザクションのバリデーションに失敗しました: {e}")

    return dict(agg_transaction)


# ==========================================
# 発展版：Polarsを用いたOut-of-core（メモリ外）処理
# ==========================================
def aggregate_by_country_polars(transaction_path: Path, user_path: Path) -> dict[str, int]:
    """
    データ規模がメモリに乗らない数億件スケールの場合を想定したPolars版の実装。
    Lazy APIとストリーミング実行を使い、メモリ消費を抑えて高速に処理する。
    """
    try:
        import polars as pl
    except ImportError:
        logger.error("Polars がインストールされていません。`pip install polars` を実行してください。")
        raise

    if not transaction_path.is_file():
        raise FileNotFoundError(f"トランザクションファイルが存在しません: {transaction_path}")
    if not user_path.is_file():
        raise FileNotFoundError(f"ユーザーマスタファイルが存在しません: {user_path}")

    # Scanでクエリグラフを作成 (遅延評価: メモリにはロードしない)
    users_lf = pl.scan_ndjson(str(user_path))
    tx_lf = pl.scan_ndjson(str(transaction_path))

    # 結合と集計のパイプラインを定義
    result_df = (
        tx_lf.join(users_lf, on="user_id", how="left")
        # 国名が欠損(null)の場合は "Unknown" に置換
        .with_columns(pl.col("country").fill_null(pl.lit("Unknown")))
        # 国ごとに金額を集計
        .group_by("country")
        .agg(pl.col("amount").sum().alias("total_amount"))
    )

    # streaming=Trueでメモリ外（Out-of-core）並列ストリーミング処理を実行
    collected = result_df.collect(streaming=True)
    
    # 辞書形式 {"country": total_amount} に変換して返却
    return {row["country"]: row["total_amount"] for row in collected.iter_rows(named=True)}


# ==========================================
# ファイルI/Oをジェネレータで処理するヘルパー
# ==========================================
def stream_jsonl(file_path: Path) -> Iterable[dict[str, Any]]:
    """
    ファイルを1行ずつ読み込み、JSONオブジェクトをyieldする。
    行単位でのエラーハンドリングを行い、壊れた行があってもスキップして継続する。
    """
    if not file_path.is_file():
        raise FileNotFoundError(f"処理対象のファイルが存在しません: {file_path}")
        
    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            # =================================================================
            # ① そもそもJSONとして壊れている場合
            # 例: {"user_id": u1} (ダブルクォーテーションがない)
            # =================================================================
            except json.JSONDecodeError as e:
                logger.warning(f"[Skip] {file_path.name} L{line_num}: JSONのパースに失敗しました: {e} | line: {line.strip()}")
            # =================================================================
            # ② その他の予期せぬエラー (OSErrorなど)
            # =================================================================
            except Exception as e:
                logger.error(f"[Error] {file_path.name} L{line_num}: 予期せぬエラーが発生しました: {e}", exc_info=True)


def main():
    print("=== 標準ライブラリ (ジェネレータ) 版の実行 ===")
    try:
        result = aggregate_by_country(
            transactions=stream_jsonl(transaction_file),
            users=stream_jsonl(user_file)
        )
        print("集計結果:", result)
    except Exception as e:
        logger.error(f"標準ライブラリ版の実行でエラーが発生しました: {e}")

    print("\n=== Polars (発展版) の実行 ===")
    try:
        polars_result = aggregate_by_country_polars(transaction_file, user_file)
        print("Polars集計結果:", polars_result)
    except ImportError:
        print("Polars が未インストールの為、Polars版の実行をスキップします。")
    except Exception as e:
        logger.error(f"Polars版の実行でエラーが発生しました: {e}")


if __name__ == '__main__':
    main()
