from typing import Any, Generator, Optional
import json
import logging
from pathlib import Path
# ロガーはモジュールレベルで適切に設定
logger = logging.getLogger(__name__)

def flatten_json_recursive(
    data: Any, 
    parent_key: str = "", 
    sep: str = ".", 
    res: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """
    再帰的にJSONをフラット化する。
    items.update() を繰り返すのではなく、1つの辞書を参照渡しして効率化する。
    """
    if res is None:
        res = {}
    if isinstance(data, dict):
        for k, v in data.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            flatten_json_recursive(v, new_key, sep, res)
    elif isinstance(data, list):
        for i, v in enumerate(data):
            new_key = f"{parent_key}{sep}{i}" if parent_key else str(i)
            flatten_json_recursive(v, new_key, sep, res)
    else:
        # 末端の要素に到達したときだけ辞書に格納
        res[parent_key] = data
    return res
def process_jsonl_stream(input_path: Path) -> Generator[dict[str, Any], None, None]:
    """
    JSONLファイルを1行ずつ読み込み、Generatorとして返す（メモリ節約）。
    """
    with input_path.open("r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield flatten_json_recursive(json.loads(line))
            except json.JSONDecodeError as e:
                logger.warning(f"Line {line_num}: Skip invalid JSON: {e}")
def main():
    # 実際には引数パース(argparse)とかを使うともっと「プロ」っぽいけど、
    # 今は基本をしっかりさせなさい！
    input_path = Path("input/input.jsonl")
    output_path = Path("output/output.jsonl")
    # 書き出しもストリーミングで行う
    with output_path.open("w", encoding="utf-8") as f:
        for flattened_data in process_jsonl_stream(input_path):
            f.write(json.dumps(flattened_data, ensure_ascii=False) + "\n")
    
    logger.info("Processing completed successfully.")
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()