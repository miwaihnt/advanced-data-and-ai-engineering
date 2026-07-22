import os
import time
import logging
from pathlib import Path
# ※ Polarsライブラリが必要です。動作テストの前にインポート可能か確認してください。
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
INPUT_CSV = Path(__file__).parent / "input/clickstream.csv"
OUTPUT_PARQUET = Path(__file__).parent / "output/user_rolling_mean.parquet"

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
# 【課題】Polars LazyFrame パイプラインの実装
# ==========================================
def run_polars_pipeline(input_path: Path, output_path: Path):
    """
    Polars LazyFrame を使用して以下の集計処理を行い、Parquet形式で保存しなさい。
    
    【要件】
    1. pl.scan_csv を使用して遅延読み込みを開始する。
    2. クレンジング: status が 'success'、かつ amount が正の実数である行のみを抽出。
    3. キャスト: timestamp列（Unix秒：int）を Datetime 型に変換。
    4. 並び替え: timestamp列で昇順にソートする（rolling集計の必須前提条件）。
    5. 移動窓集計: .rolling() を使用し、user_id ごとにグループ化し、
       過去5分間（'5m'）の amount 列の移動平均（mean）を算出しなさい。
       (出力される平均値のカラム名は 'rolling_mean_amount' とすること)
    6. 保存: メモリ展開を避け、sink_parquet() を使用して output_path にストリーミング書き出しを行う。
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # TODO: ここにPolarsのLazyパイプラインロジックを実装しなさい。
    pass


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
