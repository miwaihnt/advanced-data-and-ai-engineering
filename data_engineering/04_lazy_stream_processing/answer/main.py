import logging
import json
from pathlib import Path
from typing import Iterator, Any

# ========
# loggingの設定
# ========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========
# inputデータの設定
# スクリプトの位置を基準にし、かつ親ディレクトリ(課題4)のinputを参照するよう設定
# ========
INPUT_FILE = Path(__file__).parent.parent / "input/input.jsonl"
TARGET_KEY = "ERROR"

# ========
# inputデータをErrorに絞り込み、logフィールドの値を抽出する関数
# ========
def filter_errors(file_path: Path, key: str) -> Iterator[str]:
    if not file_path.is_file():
        raise FileNotFoundError(f"処理対象のファイルが見つかりません: {file_path}")

    # 巨大なファイルを想定し、文字化けで落ちないように errors='replace' を指定
    with open(file_path, "r", encoding='utf-8', errors='replace') as f:
        for line in f:
            if not line.strip():
                continue
            
            # 🌟 遅延パース（Pre-filtering）：
            # まず生テキストの段階で "ERROR" が含まれるかチェックし、重いJSONパースを回避する
            if key in line:
                try:
                    data = json.loads(line)
                    if "log" in data:
                        yield data["log"]
                except json.JSONDecodeError as e:
                    logger.warning(f"[Skip] JSON decode failed for line: {line.strip()}. Error: {e}")
                except Exception as e:
                    logger.error(f"[Skip] Unexpected error parsing line: {e}", exc_info=True)

# ========
# main
# ========
def main():
    logger.info("======= Process Started =======")
    try:
        for error_log in filter_errors(INPUT_FILE, TARGET_KEY):
            print(error_log)
        logger.info("======= Process Finished =======")
    except FileNotFoundError as e:
        logger.error(f"処理対象のファイルが見つかりません：{INPUT_FILE}")
    except PermissionError as e:
        logger.error(f"処理対象のファイルのアクセス権限がありません：{e}")
    except Exception as e:
        logger.error(f"想定外のエラーが発生しました。{e}", exc_info=True)

if __name__ == '__main__':
    main()