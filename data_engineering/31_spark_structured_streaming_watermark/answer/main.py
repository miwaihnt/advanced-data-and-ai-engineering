"""
課題31：正解コード（Structured Streaming with Watermark）

設計判断メモ:
- ウォーターマークは「State Store（中間集計状態）のメモリ管理」のための仕組み。
  event_time の最大値 - watermarkDelay よりも古いデータは棄却し、
  対応するウィンドウのStateも解放する → メモリのOOMを防ぐ。
- outputMode:
    "append"  : ウォーターマークを超えた（確定した）ウィンドウのみ出力。
                遅延対応が必要な集計では最もメモリ効率が高い。
    "update"  : 更新のたびに出力。StateをUI的に確認したい場合。
    "complete": 全ウィンドウの状態を毎バッチ出力。State爆発のリスクあり。
"""
import tempfile
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, TimestampType


def build_stream_with_watermark(spark: SparkSession):
    """
    Part 1: ウォーターマーク付き時間窓集計ストリームの定義
    （ソースをソケットに変更して使う想定のコード骨格）
    """
    schema = StructType([
        StructField("event_time", TimestampType(), True),
        StructField("user_id", StringType(), True),
        StructField("page", StringType(), True),
    ])

    # ソケットソースの例（本番のKafka等に差し替え可能な疎結合設計）
    df_stream = (
        spark.readStream
        .format("socket")
        .option("host", "localhost")
        .option("port", 9999)
        .load()
    )

    # JSON文字列をパースしてスキーマを適用
    df_parsed = (
        df_stream
        .select(F.from_json(F.col("value"), schema).alias("data"))
        .select("data.*")
    )

    # ウォーターマーク + タンブリングウィンドウ集計
    df_aggregated = (
        df_parsed
        .withWatermark("event_time", "10 minutes")
        .groupBy(
            F.window("event_time", "5 minutes"),
            F.col("page")
        )
        .count()
    )

    return df_aggregated


def run_rate_source_verification(spark: SparkSession, timeout_secs: int = 15) -> None:
    """
    Part 2: rate ソースを使ったローカル動作確認
    rate形式は {timestamp: Timestamp, value: Long} を自動生成する。
    """
    with tempfile.TemporaryDirectory() as checkpoint_dir:
        df_rate = spark.readStream.format("rate").option("rowsPerSecond", 1).load()

        df_windowed = (
            df_rate
            # タンブリングウィンドウ（5秒間隔）でカウント集計
            .withWatermark("timestamp", "5 seconds")
            .groupBy(F.window("timestamp", "5 seconds"))
            .count()
        )

        query = (
            df_windowed.writeStream
            .outputMode("append")
            .format("console")
            .option("truncate", False)
            .option("checkpointLocation", checkpoint_dir)
            .start()
        )

        query.awaitTermination(timeout_secs)
        query.stop()
        print(f"✅ {timeout_secs}秒のストリーム検証完了")


if __name__ == "__main__":
    spark = SparkSession.builder.appName("Challenge31_Answer").master("local[*]").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    print("=== Part 2: rate ソース検証（15秒間実行） ===")
    run_rate_source_verification(spark, timeout_secs=15)

    spark.stop()
