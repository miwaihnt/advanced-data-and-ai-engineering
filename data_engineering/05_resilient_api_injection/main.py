import logging
import random
import json
from typing import Any, Iterator
from pathlib import Path

# ========
# config
# ========
start_page = 1
output_dir = Path(__file__).parent / "input"

# ========
# logging
# ========
logging.basicConfig(
    level = logging.INFO,
    format = '%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ========
# カスタム例外
# ========
class ApiInfrastractureError(Exception):
    """三回試行した結果、失敗となった場合の例外クラス"""
    pass


# ========
# mock用のAPI
# ========

def _fetch_page(start_page:int) -> dict[str, Any]:

    # 乱数の発生
    rnd = random.random()

    if rnd < 0.2:
        raise ConnectionError(f"サーバへの接続に失敗しました")
    elif rnd < 0.3:
        raise IOError(f"サーバとの疎通が切断されました")

    page = start_page

    if page == 1:
        return { "data": [{"tx_id": "tx_001", "amount": 5000}, {"tx_id": "tx_002", "amount": 1200}],
                "next_page":2        
        }
    elif page == 2:
        return { "data": [{"tx_id": "tx_001", "amount": 5000}, {"tx_id": "tx_002", "amount": 1200}],
                "next_page":3        
        }
    elif page == 3:
        return { "data": [{"tx_id": "tx_001", "amount": 5000}, {"tx_id": "tx_002", "amount": 1200}],
                "next_page": None        
        }
        
    else:
        return {"data":{}, "next_page": None}
    


# ========
# mock_apiを叩いてデータを取得する
# api側からのエラーは三回までretryする。三回のトライでダメな場合、独自例外が発生
# ========
def mock_api_call(start_page:int) -> Iterator[dict[str,Any]]:

    page = start_page
    max_retries = 3

    while page is not None:
        success = False
        result = None



        for attempt in range(1, max_retries + 1):
            try:
                result = _fetch_page(page)
                print(result)
                success = True
                page = result["next_page"]
                break
            except (IOError, ConnectionError) as e:
                logging.warning(f"apiコールの失敗。試行回数:{attempt}/ {max_retries}")
                if attempt < max_retries - 1:
                    continue
        
        if success == False:
            raise ApiInfrastractureError(f"試行回数を超過。処理を中止します")

        # データを1つずつ返すGenerator
        for d in result["data"]:
            yield d


# ========
# 取得結果jsonlに保存する
# ========
def save_as_jsonl(stream_data:dict[str, Any], output_dir: Path) -> None:
    # 保存先のディレクトリがなければ作成
    output_dir.mkdir(parents=True,  exist_ok=True)
    # 保残先ファイルの作成
    output_file = output_dir /"output.jsonl"
    # 保存処理の実行
    with open(output_file, "a", encoding="utf-8") as f:
        try:
            f.write(json.dumps(stream_data))
        except TypeError as e:
            logger.warning(f"[Skip]:Jsonのデコードに失敗しました。対象データ:{stream_data}, 原因:{e}")


def main():
    print("====処理開始====")
    try:
        for i in mock_api_call(1):
            save_as_jsonl(i, output_dir)
    except ApiInfrastractureError as e:
            logger.error(f"api callに失敗しました。処理を終了します")
            raise

if __name__ == '__main__':
    main()