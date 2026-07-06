import os
import json
import time
import logging
from pathlib import Path
from typing import Iterator, List, Dict, Any
from concurrent.futures import ProcessPoolExecutor

# =========
# logging
# =========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("GILBypassParser")

# =========
# config
# =========
INPUT_FILE = Path(__file__).parent / "input/large_input.jsonl"

# ==========================================
# テストデータ生成用ヘルパー（書き換えないでください）
# ==========================================
def generate_mock_data(file_path: Path, num_lines: int = 20000):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    users = ["u1", "u2", "u3", "u4", "u5"]
    statuses = ["success", "success", "success", "failed"]  # 75% success

    logger.info(f"Generating mock JSONL logs ({num_lines} lines) at: {file_path}")
    with open(file_path, "w", encoding="utf-8") as f:
        for i in range(num_lines):
            # 意図的にパースエラーになる壊れた行を時々混ぜる
            if i % 1000 == 0:
                f.write("{invalid_json_line\n")
                continue
            log_entry = {
                "user_id": users[i % len(users)],
                "amount": (i % 10) * 100 + 100,
                "status": statuses[i % len(statuses)]
            }
            f.write(json.dumps(log_entry) + "\n")


# ==========================================
# 1. チャンク読み込み用ジェネレータ
# ==========================================
def read_chunks(file_path: Path, chunk_size: int = 1000) -> Iterator[List[str]]:
    """
    ファイルを一度に全件ロードせず、指定された行数(chunk_size)ずつのリストを yield するジェネレータ。
    """
    # TODO: ここにチャンク読み込みのロジックを実装しなさい。
    # 空間計算量 O(chunk_size) を守ること。
    yield []


# ==========================================
# 2. 各プロセスで動くローカル集計関数 (Mapフェーズ)
# ==========================================
def parse_chunk_local(lines: List[str]) -> Dict[str, int]:
    """
    1チャンク分のテキスト行リストを受け取り、JSONパースして status が "success" のもののみを集計する。
    結果を {user_id: total_amount} の部分集計辞書として返す。
    
    ※ 各行の JSONDecodeError などの例外をキャッチしてスキップし、処理全体を止めないこと。
    """
    local_agg = {}
    # TODO: ここに各プロセスでのローカルパース・集計ロジックを実装しなさい。
    return local_agg


# ==========================================
# 3. マルチプロセスオーケストレータ (Reduceフェーズ)
# ==========================================
def parallel_parse_and_aggregate(
    file_path: Path, 
    chunk_size: int = 1000, 
    max_workers: int = 4
) -> Dict[str, int]:
    """
    ProcessPoolExecutor を使用して、チャンクごとのパースを並列実行する。
    返ってきた部分集計データをメインプロセス側の辞書に合流（Reduce）させて返す。
    """
    master_agg = {}

    # TODO: ここに ProcessPoolExecutor を用いた並列処理と、結果の集約ロジックを実装しなさい。
    # ヒープメモリを圧迫しないよう、Executorの futres の管理にも配慮すること。

    return master_agg


# =========
# main
# =========
def main():
    # 1. テストデータの生成
    generate_mock_data(INPUT_FILE, num_lines=50000)

    # 2. 並列パースの実行と時間計測
    logger.info("Starting parallel aggregation...")
    start_time = time.time()
    
    # ワーカプロセス数4、チャンクサイズ5000で実行
    result = parallel_parse_and_aggregate(INPUT_FILE, chunk_size=5000, max_workers=4)
    
    elapsed_time = time.time() - start_time
    logger.info(f"Aggregation finished in {elapsed_time:.4f} seconds.")

    # 3. 集計結果の確認
    logger.info("======= 集計結果 =======")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
