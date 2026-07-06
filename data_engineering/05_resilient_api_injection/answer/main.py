import logging
import random
from pathlib import Path
import json
import time

# ========
# loggingの設定
# ========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========
# カスタムの例外クラス
# ========
class APIInfrastructureError(Exception):
    """回復不能な通信障害を表すカスタム例外"""
    pass


# ========
# mock用のAPI
# ========
def mock_api_call(page: int) -> dict[str, any]:
    rand = random.random()
    if rand < 0.2:
        raise ConnectionError(f"HTTP Error 429 Too Many Request")
    if rand <= 0.4:
        raise IOError(f"HTTP Error 500 Internal Server Error")
    
    if page == 1:
        return {
                "data": [{"tx_id": "tx_001", "amount": 5000}, {"tx_id": "tx_002", "amount": 1200}],
                "next_page": 2           
        }
        
    if page == 2:
        return {
            "data": [{"tx_id": "tx_003", "amount": 1000},{"tx_id": "tx_004", "amount": 2000}],
            "next_page": 3
        }

    if page == 3:
        return {
            "data": [{"tx_id": "tx_005", "amount": 1600},{"tx_id": "tx_006", "amount": 2500}],
            "next_page": 4
        }
    else:
        return{
            "data":[],
            "next_page":None
        }

# ========
# APIから取得したデータを保存
# ========
def save_jsonl(data: dict[str, any], save_path: Path) -> None:

    save_file = save_path/"001.jsonl"

    with open(save_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(data) + "\n")

# ========
# Orchestrator:APIリクエスト〜保存までの
# ========
def fetch_all_transactions(start_page: int):
    page = start_page 
    max_retries = 3
    while page is not None:
        # 多層防御 (Defense in Depth) および静的解析ツール (MyPy/Pyright) の警告防止のための初期化。
        # 万が一将来のリファクタリングで「例外発生時に警告ログのみで処理を続行する」バグが紛れ込んでも、
        # 前のページのデータ (Ghost Data) を参照して二重処理や無限ループを起こすのを防ぎ、
        # 下流の result["data"] にて確実に即時クラッシュ (Fail-Fast: TypeError) させるためのセーフティネット。
        result = None
        Success = False

        for attempt in range(1, max_retries + 1):
            try:
                result = mock_api_call(page)
                Success = True
                break
            except (ConnectionError, IOError) as e:
                logger.warning(f"pageの取得に失敗。{attempt}/ {max_retries}回目 {e}")
                if attempt < max_retries:
                    time.sleep(1)
            except Exception as e:
                logger.error(f"想定外のエラーが発生。{e}", exc_info=True)
                raise
        
        # 三回トライしてもダメだった場合
        if not Success or result is None:
            raise APIInfrastructureError(f"回復不能な通信障害：ページ{page}で {max_retries}回リトライしたが失敗しました")

        for i in result["data"]:
            yield i

        page = result["next_page"]

def main():
    # 保存先フォルダ
    save_path = Path.cwd() / "output"
    save_path.mkdir(parents=True, exist_ok=True)
    # API取得開始位置
    page = 1
    # APIリクエスト
    try:
        for data in fetch_all_transactions(page):
            save_jsonl(data, save_path)
    except APIInfrastructureError as e:
        logger.error(f"バッチ処理中に回復不能なインフラ例外を検知しました。処理を異常終了します: {e}")
        raise

if __name__ == '__main__':
    main()