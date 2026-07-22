"""
課題30：正解コード（Delta Lake MERGE INTO SCD Type 2）

設計判断メモ:
- SCD Type 2 を1フェーズのMERGEで完全実装するには、Delta 2.0以降の
  「WHEN NOT MATCHED BY SOURCE」節が必要。
- ここでは汎用性の高い「2フェーズ方式」を採用:
    Phase 1: 変更があった既存レコードを MERGE で無効化（is_current=false）
    Phase 2: 変更ありレコード + 新規レコードをまとめて INSERT
"""
import os
import shutil
from datetime import datetime
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from delta import configure_spark_with_delta_pip
from delta.tables import DeltaTable


def create_spark() -> SparkSession:
    builder = (
        SparkSession.builder
        .appName("Challenge30_Answer")
        .master("local[*]")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog"
        )
    )
    return configure_spark_with_delta_pip(builder).getOrCreate()


def setup_initial_table(spark: SparkSession, table_path: str) -> None:
    existing_data = [
        ("C-01", "Alice", "alice@old.com",     True,  "2024-01-01", "9999-12-31"),
        ("C-02", "Bob",   "bob@example.com",   True,  "2024-01-01", "9999-12-31"),
    ]
    schema = ["customer_id", "name", "email", "is_current", "valid_from", "valid_to"]
    df = spark.createDataFrame(existing_data, schema=schema)
    df.write.format("delta").mode("overwrite").save(table_path)
    print("✅ 初期Deltaテーブルを作成しました")


def run_scd2_merge(spark: SparkSession, table_path: str, update_date: str) -> None:
    incoming_data = [
        ("C-01", "Alice", "alice@new.com"),
        ("C-03", "Charlie", "charlie@example.com"),
    ]
    incoming_schema = ["customer_id", "name", "email"]
    df_incoming = spark.createDataFrame(incoming_data, schema=incoming_schema)

    delta_table = DeltaTable.forPath(spark, table_path)

    # Phase 1: 変更があった is_current=true のレコードを無効化する
    # - emailが変わった場合のみUPDATE対象とする
    (
        delta_table.alias("target")
        .merge(
            df_incoming.alias("source"),
            "target.customer_id = source.customer_id AND target.is_current = true"
        )
        .whenMatchedUpdate(
            condition="target.email != source.email",
            set={
                "is_current": F.lit(False),
                "valid_to": F.lit(update_date),
            }
        )
        .execute()
    )

    # Phase 2: 変更ありレコードの「新バージョン」と「完全新規」の両方をINSERT
    # - 変更ありの customer_id は既にis_current=falseになっているため、
    #   NOT MATCHEDで再度インサートされる
    (
        delta_table.alias("target")
        .merge(
            df_incoming.alias("source"),
            # is_current=trueで一致するレコードがなければINSERT
            "target.customer_id = source.customer_id AND target.is_current = true"
        )
        .whenNotMatchedInsert(
            values={
                "customer_id": "source.customer_id",
                "name":        "source.name",
                "email":       "source.email",
                "is_current":  F.lit(True),
                "valid_from":  F.lit(update_date),
                "valid_to":    F.lit("9999-12-31"),
            }
        )
        .execute()
    )

    print(f"✅ SCD Type 2 MERGE 完了（update_date: {update_date}）")


if __name__ == "__main__":
    spark = create_spark()
    spark.sparkContext.setLogLevel("WARN")

    # 実験用にローカルの固定フォルダを指定する（既存のテストデータがあれば一旦削除）
    table_path = "./output_delta_table_scd2"
    if os.path.exists(table_path):
        shutil.rmtree(table_path)

    setup_initial_table(spark, table_path)

    print("\n=== MERGE 前のテーブル（Version 0） ===")
    spark.read.format("delta").load(table_path).show(truncate=False)

    run_scd2_merge(spark, table_path, update_date="2024-02-01")

    print("\n=== MERGE 後のテーブル（最新状態 / 4レコード期待） ===")
    result = spark.read.format("delta").load(table_path)
    result.orderBy("customer_id", "valid_from").show(truncate=False)

    # コミット履歴の確認
    print("\n=== Delta テーブルのコミット履歴（History） ===")
    delta_table = DeltaTable.forPath(spark, table_path)
    delta_table.history().select("version", "timestamp", "operation", "operationMetrics").show(truncate=False)

    # Time Travel の確認（バージョン0が初期状態）
    print("\n=== Time Travel: Version 0（MERGE前の初期状態） ===")
    spark.read.format("delta").option("versionAsOf", 0).load(table_path).show(truncate=False)

    print(f"\n📁 物理データは '{table_path}' に残してあるわよ！")
    print(f"   `ls -la {table_path}` や `ls -la {table_path}/_delta_log` で中身を確認しなさい！")

    spark.stop()
