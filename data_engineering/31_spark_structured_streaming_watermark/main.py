"""
課題31：PySpark 構造化ストリーミング with ウォーターマーク（遅延データ対応）

ここを実装しなさい。

注意:
  - ローカル検証には Part 2 の rate ソースを使うこと（ソケット接続不要）。
  - Part 1 はコード実装のみ（ウォーターマーク付きストリームのDFを定義）。
"""
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, TimestampType


def build_stream_with_watermark(spark: SparkSession):
    """
    Part 1: ウォーターマーク付き時間窓集計ストリームの定義。

    仮想のスキーマ（event_time, user_id, page）を持つストリームDFに対して:
    1. withWatermark("event_time", "10 minutes") を設定する。
    2. window("event_time", "5 minutes") のタンブリングウィンドウで集計する。
    3. page ごとのアクセス数（count）を集計する。

    Returns:
        ウォーターマーク付き集計済みのストリーミングDataFrame。
    """
    schema = StructType([
        StructField("event_time", TimestampType(), True),
        StructField("user_id", StringType(), True),
        StructField("page", StringType(), True),
    ])

    # ここを実装せよ: spark.readStream を使って上記スキーマの
    # ソケットor rateストリームを受け取り、ウォーターマーク集計を設定せよ
    raise NotImplementedError


def run_rate_source_verification(spark: SparkSession, timeout_secs: int = 15) -> None:
    """
    Part 2: rate ソースを使ったローカル動作確認。

    - spark.readStream.format("rate") で毎秒1レコードのストリームを生成する。
    - timestamp カラムを event_time として利用する。
    - 5秒のタンブリングウィンドウで行数を集計してコンソール出力する。
    - awaitTermination(timeout_secs) で指定秒後に自動停止する。
    """
    # ここを実装せよ
    raise NotImplementedError


if __name__ == "__main__":
    spark = SparkSession.builder.appName("Challenge31").master("local[*]").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    print("=== Part 2: rate ソース検証（15秒間実行） ===")
    run_rate_source_verification(spark, timeout_secs=15)

    spark.stop()
