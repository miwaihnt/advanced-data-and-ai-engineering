"""
課題32：正解コード

設計判断メモ:
- coalesce(col1, col2, lit(default)) で優先度順のフォールバック値を決定。
- from_json で構造化スキーマを適用。
- explode_outer は NULL や空配列を消さずに残すが、今回は explode でタグ展開を行う。
- fillna / coalesce でネスト内フィールドの補完を行う。
"""
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, ArrayType


def create_sample_data(spark: SparkSession) -> DataFrame:
    data = [
        ("L-101", "U-01", "alice@main.com", "alice@bk.com", '{"tags": ["tech", "ai"], "device": "mobile"}'),
        ("L-102", "U-02", None,             "bob@bk.com",   '{"tags": ["news"], "device": "desktop"}'),
        ("L-103", "U-03", None,             None,           '{"tags": ["tech", "sports"], "device": null}'),
        ("L-104", "U-04", "dave@main.com",  None,           None),
    ]
    schema = ["log_id", "user_id", "preferred_email", "backup_email", "raw_payload"]
    return spark.createDataFrame(data, schema=schema)


def process_nulls_and_complex_types(df: DataFrame) -> DataFrame:
    # 1. 優先度付きメール決定 & 無効行除外
    df_email = (
        df.withColumn(
            "contact_email",
            F.coalesce(F.col("preferred_email"), F.col("backup_email"), F.lit("unknown@example.com"))
        )
        .filter(F.col("contact_email") != "unknown@example.com")
    )

    # 2. JSON スキーマの定義
    json_schema = StructType([
        StructField("tags", ArrayType(StringType()), True),
        StructField("device", StringType(), True),
    ])

    # 3. パース & 展開
    df_parsed = (
        df_email.withColumn("parsed_payload", F.from_json(F.col("raw_payload"), json_schema))
        .select(
            "log_id",
            "user_id",
            "contact_email",
            F.coalesce(F.col("parsed_payload.device"), F.lit("unknown")).alias("device"),
            F.explode_outer(F.col("parsed_payload.tags")).alias("tag")
        )
    )

    return df_parsed


if __name__ == "__main__":
    spark = SparkSession.builder.appName("Challenge32_Answer").master("local[*]").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    df_raw = create_sample_data(spark)
    print("=== 生データ ===")
    df_raw.show(truncate=False)

    df_result = process_nulls_and_complex_types(df_raw)
    print("=== クレンジング・展開後のデータ ===")
    df_result.show(truncate=False)

    spark.stop()
