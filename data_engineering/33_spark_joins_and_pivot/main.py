"""
課題33：SparkにおけるJoin最適化（Broadcast Join）とPivot（縦横変換）

ここを実装しなさい。
"""
from pyspark.sql import SparkSession
from pyspark.sql import functions as F


def create_sample_data(spark: SparkSession):
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


def execute_broadcast_join_and_pivot(sales_df, stores_df) -> "DataFrame":
    """
    1. sales_df と stores_df を Broadcast Join (Left Join) する
    2. region ごとに category ごとの売上合計 (amount) を Pivot 集計する
    3. 欠損値 (NULL) は 0 で補完する
    """
    # ここを実装せよ
    raise NotImplementedError


if __name__ == "__main__":
    spark = SparkSession.builder.appName("Challenge33").master("local[*]").getOrCreate()
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
