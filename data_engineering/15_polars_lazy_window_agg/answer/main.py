import os
import time
import logging
from pathlib import Path
import polars as pl

# =========
# logging
# =========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("PolarsRollingPipeline")

# =========
# config
# =========
INPUT_CSV = Path(__file__).parent.parent / "input/clickstream.csv"
OUTPUT_PARQUET = Path(__file__).parent.parent / "output/user_rolling_mean.parquet"

# ==========================================
# テストデータ生成用ヘルパー（書き換えないでください）
# ==========================================
def generate_mock_csv(file_path: Path, num_lines: int = 50000):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 基点となるUnixタイムスタンプ (2026-06-25T15:00:00Z)
    start_ts = 1782399600 
    users = ["u1", "u2", "u3", "u4", "u5"]
    statuses = ["success", "success", "success", "failed"]

    logger.info(f"Generating mock clickstream CSV ({num_lines} lines) at: {file_path}")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("timestamp,user_id,amount,status\n")
        for i in range(num_lines):
            # 時系列が単調増加するようにタイムスタンプを増加させる
            ts = start_ts + (i // len(users)) * 10
            # 意図的に amount を NULL (空) にした行や不正値を混ぜる
            amount = "" if i % 1000 == 0 else str(float((i % 5) * 50 + 50))
            if i % 2000 == 0:
                amount = "-100.0" # 不正値
            
            user = users[i % len(users)]
            status = statuses[i % len(statuses)]
            f.write(f"{ts},{user},{amount},{status}\n")


# ==========================================
# 【模範解答】Polars LazyFrame パイプラインの実装
# ==========================================
def run_polars_pipeline(input_path: Path, output_path: Path):
    """
    Polars LazyFrame を使用して以下の集計処理を行い、Parquet形式で保存しなさい。
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Scan CSV (遅延読み込みの定義。この時点ではI/Oは発生しない)
    lazy_plan = (
        pl.scan_csv(str(input_path))
        
        # 2. クレンジング: status が 'success' かつ amount が正の数値であるレコードのみを対象とする
        .filter(
            (pl.col("status") == "success") &
            (pl.col("amount").is_not_null()) &
            (pl.col("amount") > 0)
        )
        
        # 3. キャスト: Unix秒 (整数) を Datetime 型に変換
        .with_columns(
            pl.from_epoch(pl.col("timestamp"), time_unit="s").alias("timestamp")
        )
        
        # 4. ソート: 移動窓集計のために timestamp 昇順でソート（group_by_rolling の必須要件）
        .sort("timestamp")
        
        # 5. 移動窓集計: 各ユーザー(user_id)ごとに、過去5分(5m)の移動平均を算出する
        .rolling(
            index_column="timestamp",
            period="5m",
            group_by="user_id"
        )
        .agg(
            # 現在のトランザクション額を残しつつ、5分移動平均を算出
            pl.col("amount").last().alias("amount"),
            pl.col("amount").mean().alias("rolling_mean_amount")
        )
    )

    # 6. 保存: ストリーミング（OutOfCore）実行を明示して Parquet に直接書き込む
    # メモリ上にDataFrameオブジェクトを構築しないため、メモリ効率が極めて高い
    lazy_plan.sink_parquet(str(output_path))


# =========
# main
# =========
def main():
    # 1. テストデータの生成
    generate_mock_csv(INPUT_CSV, num_lines=10000)

    # 2. パイプラインの実行
    logger.info("Starting Polars pipeline...")
    start_time = time.time()
    
    run_polars_pipeline(INPUT_CSV, OUTPUT_PARQUET)
    
    elapsed_time = time.time() - start_time
    logger.info(f"Polars pipeline finished in {elapsed_time:.4f} seconds.")

    # 3. 集計結果の確認（一部を読み込んでコンソールに表示）
    if OUTPUT_PARQUET.exists():
        logger.info("======= 集計結果サンプル (Parquetから読み込み) =======")
        df_sample = pl.read_parquet(OUTPUT_PARQUET).head(10)
        print(df_sample)
    else:
        logger.error("Output Parquet file was not created!")

    # テスト終了後にモックファイルをクリーンアップ
    if INPUT_CSV.is_file():
        os.remove(INPUT_CSV)
    if OUTPUT_PARQUET.is_file():
        os.remove(OUTPUT_PARQUET)
    logger.info("Temporary test files cleaned up.")

if __name__ == "__main__":
    main()
