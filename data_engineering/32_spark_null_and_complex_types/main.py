"""
課題32：PySparkにおけるNULL処理と複合データ型（JSON・Array）の展開

ここを実装しなさい。
"""
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, ArrayType


def create_sample_data(spark: SparkSession):
    data = [
        ("L-101", "U-01", "alice@main.com", "alice@bk.com", '{"tags": ["tech", "ai"], "device": "mobile"}'),
        ("L-102", "U-02", None,             "bob@bk.com",   '{"tags": ["news"], "device": "desktop"}'),
        ("L-103", "U-03", None,             None,           '{"tags": ["tech", "sports"], "device": null}'),
        ("L-104", "U-04", "dave@main.com",  None,           None),
    ]
    schema = ["log_id", "user_id", "preferred_email", "backup_email", "raw_payload"]
    return spark.createDataFrame(data, schema=schema)


def process_nulls_and_complex_types(df) -> "DataFrame":
    """
    1. preferred_email -> backup_email -> "unknown@example.com" の順で優先評価する contact_email を作成
    2. contact_email == "unknown@example.com" の行をフィルタアウト
    3. raw_payload (JSON) をパース (schema: tags=Array[String], device=String)
    4. tags を explode し、device が NULL の場合は "unknown" で補完
    """
    # ここを実装せよ
    raise NotImplementedError


if __name__ == "__main__":
    spark = SparkSession.builder.appName("Challenge32").master("local[*]").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    df_raw = create_sample_data(spark)
    print("=== 生データ ===")
    df_raw.show(truncate=False)

    df_result = process_nulls_and_complex_types(df_raw)
    print("=== クレンジング・展開後のデータ ===")
    df_result.show(truncate=False)

    spark.stop()
