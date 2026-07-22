"""
課題33：正解コード

設計判断メモ:
- F.broadcast(stores_df) により、Driverから全Worker Executorに店舗マスタがブロードキャストされる。
- これにより、Shuffle Hash Join や Sort Merge Join のような全データ再配置（Shuffle）が回避され、局所的に高速化される。
- pivot() 前に可能であれば pivot 値のリストを明示すると、不要な追加スキャンを回避できる（例: pivot("category", ["Electronics", "Books", "Clothing"])）。
"""
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F


def create_sample_data(spark: SparkSession) -> tuple[DataFrame, DataFrame]:
    sales_data = [
        ("TX-001", "U-01", "ST-101", "Electronics", 50000),
        ("TX-002", "U-02", "ST-102", "Books",        2000),
        ("TX-003", "U-01", "ST-101", "Books",        1500),
        ("TX-004", "U-03", "ST-101", "Electronics", 120000),
        ("TX-005", "U-02", "ST-101", "Clothing",     8000),
    ]
    sales_schema = ["transaction_id", "user_id", "store_id", "category", "amount"]
    sales_df = spark.createDataFrame(sales_data, schema=sales_schema)

    stores_data = [
        ("ST-101", "Tokyo Flag", "Kanto"),
        ("ST-102", "Osaka Main", "Kansai"),
    ]
    stores_schema = ["store_id", "store_name", "region"]
    stores_df = spark.createDataFrame(stores_data, schema=stores_schema)

    return sales_df, stores_df


def execute_broadcast_join_and_pivot(sales_df: DataFrame, stores_df: DataFrame) -> DataFrame:
    # 1. Broadcast Join (マスタ側をブロードキャスト指定)
    df_joined = sales_df.join(
        F.broadcast(stores_df),
        on="store_id",
        how="left"
    )

    # 2. GroupBy + Pivot 集計
    df_pivot = (
        df_joined
        .groupBy("region")
        .pivot("category")
        .agg(F.sum("amount"))
        .fillna(0)
    )

    return df_pivot


if __name__ == "__main__":
    spark = SparkSession.builder.appName("Challenge33_Answer").master("local[*]").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    sales_df, stores_df = create_sample_data(spark)

    print("=== 取引データ ===")
    sales_df.show(truncate=False)

    print("=== 店舗マスタ ===")
    stores_df.show(truncate=False)

    df_pivot = execute_broadcast_join_and_pivot(sales_df, stores_df)
    print("=== Broadcast Join & Pivot 結果 ===")
    df_pivot.show(truncate=False)

    spark.stop()
