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
INPUT_FILE = Path(__file__).parent.parent / "input/large_input.jsonl"

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
    if not file_path.is_file():
        raise FileNotFoundError(f"Target file not found at: {file_path}")

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        chunk = []
        for line in f:
            chunk.append(line)
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk


# ==========================================
# 2. 各プロセスで動くローカル集計関数 (Mapフェーズ)
# ==========================================
def parse_chunk_local(lines: List[str]) -> Dict[str, int]:
    """
    1チャンク分のテキスト行リストを受け取り、JSONパースして status が "success" のもののみを集計する。
    結果を {user_id: total_amount} の部分集計辞書として返す。
    """
    local_agg = {}
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        
        # 🌟 遅延パース（Pre-filtering）：
        # まず生テキストの段階で "success" が含まれるかチェックし、重いJSONパースを回避する
        if "success" in stripped:
            try:
                data = json.loads(stripped)
                if data.get("status") == "success" and "user_id" in data and "amount" in data:
                    uid = data["user_id"]
                    amount = data["amount"]
                    local_agg[uid] = local_agg.get(uid, 0) + amount
            except json.JSONDecodeError:
                # ワーカープロセス内でのパースエラーは警告を出して無視
                pass
            except Exception:
                # その他想定外のエラーもスキップ
                pass
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

    # CPU数に応じたワーカー数の調整（明示的に指定された上限を利用）
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # read_chunksジェネレータからチャンクを順次取得し、プロセスプールへマッピング
        chunks = read_chunks(file_path, chunk_size)
        
        # executor.map はイテレータを引数に取り、結果をジェネレータとして返す
        results = executor.map(parse_chunk_local, chunks)

        # 各プロセスの結果をメインプロセス上のマスタ辞書に集約する（Reduce）
        for local_result in results:
            for uid, amount in local_result.items():
                master_agg[uid] = master_agg.get(uid, 0) + amount

    return master_agg


# =========
# main
# =========
def main():
    # 1. テストデータの生成
    generate_mock_data(INPUT_FILE, num_lines=50000)

    # 2. 並列パースの実行と時間計測
    logger.info(f"Starting parallel aggregation with 4 worker processes...")
    start_time = time.time()
    
    # ワーカプロセス数4、チャンクサイズ5000で実行
    result = parallel_parse_and_aggregate(INPUT_FILE, chunk_size=5000, max_workers=4)
    
    elapsed_time = time.time() - start_time
    logger.info(f"Aggregation finished in {elapsed_time:.4f} seconds.")

    # 3. 集計結果の確認
    logger.info("======= 集計結果 =======")
    print(json.dumps(result, indent=2))

    # テスト終了後にモックファイルを削除してクリーンアップ（実務のマナー）
    if INPUT_FILE.is_file():
        os.remove(INPUT_FILE)
        logger.info("Temporary mock file deleted.")

if __name__ == "__main__":
    main()
