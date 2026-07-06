import time
import random
import logging
from typing import Any, Dict, Iterator, List, Optional

# =========
# loggingの設定
# =========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CursorPagination")


# =========
# カスタム例外クラス
# =========
class APIConnectionError(Exception):
    """API接続の通信障害を表すカスタム例外"""
    pass


# ==========================================
# Mock API（書き換えないでください）
# ==========================================
def mock_cursor_api(cursor: Optional[str] = None) -> Dict[str, Any]:
    """
    Cursorベースのページネーションを提供する模擬API。
    15%の確率で一時的な通信障害 (APIConnectionError) を発生させる。
    """
    # 意図的な通信エラーのシミュレーション
    if random.random() < 0.15:
        raise APIConnectionError("Temporary network disconnect (503 Service Unavailable)")
        
    # カーソル状態の遷移: None -> "cur_page_2" -> "cur_page_3" -> "cur_page_4" -> None
    if cursor is None:
        return {
            "records": [
                {"id": 1, "name": "Alice", "score": 95},
                {"id": 2, "name": "Bob", "score": 88}
            ],
            "next_cursor": "cur_page_2"
        }
    elif cursor == "cur_page_2":
        return {
            "records": [
                {"id": 3, "name": "Charlie", "score": 92},
                {"id": 4, "name": "David", "score": 79}
            ],
            "next_cursor": "cur_page_3"
        }
    elif cursor == "cur_page_3":
        # イジワル：一部データ欠損やキーの不足
        return {
            "records": [
                {"id": 5, "name": "Eve", "score": 85},
                {"id": 6, "name": "Frank"}  # scoreキーが欠損
            ],
            "next_cursor": "cur_page_4"
        }
    elif cursor == "cur_page_4":
        return {
            "records": [
                {"id": 7, "name": "Grace", "score": 99}
            ],
            "next_cursor": None  # 最終ページ
        }
    else:
        raise ValueError(f"Invalid cursor token: {cursor}")


# ==========================================
# 【模範解答】Cursor型APIのストリーミングラッパーの実装
# ==========================================
def stream_records_from_api(
    max_retries: int = 3, 
    retry_delay: float = 0.5
) -> Iterator[Dict[str, Any]]:
    """
    Cursor型APIから全レコードを省メモリで取得し、1件ずつ yield するジェネレータ。
    """
    cursor: Optional[str] = None
    has_more = True

    while has_more:
        # 多層防御：リクエスト結果と成否フラグを初期化
        response_data: Optional[Dict[str, Any]] = None
        success = False

        # API接続のリトライループ
        for attempt in range(1, max_retries + 1):
            try:
                # APIリクエスト送信
                response_data = mock_cursor_api(cursor)
                success = True
                break
            except APIConnectionError as e:
                logger.warning(
                    f"APIへの接続に失敗しました (試行 {attempt}/{max_retries}): {e}"
                )
                if attempt < max_retries:
                    time.sleep(retry_delay)
            except Exception as e:
                # ネットワーク障害以外の予期せぬ例外は、リトライせずに即時再送（Fail-Fast）
                logger.error(f"予期せぬ例外が発生しました: {e}", exc_info=True)
                raise

        # リトライ上限を超えても成功しなかった場合、例外を投げてプロセスを止める
        if not success or response_data is None:
            raise APIConnectionError(
                f"API接続がリトライ上限 ({max_retries}回) に達したため、処理を中断します。"
            )

        # ⭕️ yield from を用いた、各ページ内レコードの省メモリ順次出力
        # 防御的設計：'records'キーがない場合やNoneの場合に備えて .get() とフォールバック [] を使用
        records = response_data.get("records")
        if isinstance(records, list):
            yield from records
        elif records is not None:
            # recordsキーが存在するがリストではない異常構造の場合の警告
            logger.warning(f"レスポンスの 'records' がリストではありません: {type(records)}")

        # カーソルの更新と継続条件の判定
        cursor = response_data.get("next_cursor")
        
        # カーソルがNoneまたは空文字になった場合は、次のループに入らず終了する
        if cursor is None or cursor == "":
            has_more = False


# =========
# main
# =========
def main():
    logger.info("Starting Cursor Pagination Wrapper...")
    
    try:
        # APIストリームの開始
        record_stream = stream_records_from_api(max_retries=3, retry_delay=0.5)
        
        print("--- 🚀 受信したレコード ---")
        for record in record_stream:
            # 安全にデータを表示
            print(f"ID: {record.get('id')}, Name: {record.get('name')}, Score: {record.get('score', 'N/A')}")
        print("--- 処理完了 ---")

    except Exception as e:
        logger.error(f"プログラム実行中に致命的なエラーが発生しました: {e}", exc_info=True)


if __name__ == '__main__':
    main()
