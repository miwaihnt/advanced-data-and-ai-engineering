"""
課題29：正解コード

設計判断メモ:
- ROW_NUMBER() は同値でも必ず一意な連番を振るため「完全な重複排除」に最適。
- RANK() は同値に同じ順位を振り、次の順位をスキップする（例: 1,1,3）。
- DENSE_RANK() は同値に同じ順位を振るが、スキップしない（例: 1,1,2）。
  → Top-Nランキング（"同率2位"も含めたい）には DENSE_RANK が適切。
"""
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window


def create_sample_data(spark: SparkSession) -> DataFrame:
    data = [
        ("ORD-001", "C-01", "P-A", "Electronics", 59800, "2024-01-05 10:00:00"),
        ("ORD-001", "C-01", "P-A", "Electronics", 59800, "2024-01-05 10:00:00"),
        ("ORD-002", "C-02", "P-B", "Books",         1500, "2024-01-06 11:00:00"),
        ("ORD-003", "C-01", "P-C", "Electronics",  12000, "2024-01-07 09:30:00"),
        ("ORD-004", "C-03", "P-D", "Books",         2800, "2024-01-08 14:00:00"),
        ("ORD-005", "C-02", "P-E", "Electronics",  98000, "2024-01-09 16:45:00"),
        ("ORD-005", "C-02", "P-E", "Electronics",  98000, "2024-01-09 16:45:00"),
        ("ORD-006", "C-03", "P-F", "Books",         5500, "2024-01-10 13:20:00"),
    ]
    schema = ["order_id", "customer_id", "product_id", "category", "amount", "ordered_at"]
    return spark.createDataFrame(data, schema=schema)


def dedup_with_dataframe_api(df: DataFrame) -> DataFrame:
    """Part 1a: DataFrame API"""
    window = Window.partitionBy("order_id").orderBy("ordered_at")
    return (
        df.withColumn("rn", F.row_number().over(window))
          .filter(F.col("rn") == 1)
          .drop("rn")
    )


def dedup_with_spark_sql(df: DataFrame, spark: SparkSession) -> DataFrame:
    """Part 1b: Spark SQL"""
    df.createOrReplaceTempView("orders")
    return spark.sql("""
        SELECT order_id, customer_id, product_id, category, amount, ordered_at
        FROM (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY ordered_at) AS rn
            FROM orders
        )
        WHERE rn = 1
    """)


def get_top_n_per_category(df: DataFrame, top_n: int = 2) -> DataFrame:
    """Part 2: カテゴリ別 Top-N (DENSE_RANK)"""
    window = Window.partitionBy("category").orderBy(F.col("amount").desc())
    return (
        df.withColumn("rank", F.dense_rank().over(window))
          .filter(F.col("rank") <= top_n)
          .select("category", "order_id", "amount", "rank")
          .orderBy("category", "rank")
    )


if __name__ == "__main__":
    spark = SparkSession.builder.appName("Challenge29_Answer").master("local[*]").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    df_raw = create_sample_data(spark)

    print("=== 生データ（重複あり） ===")
    df_raw.show(truncate=False)

    df_deduped = dedup_with_dataframe_api(df_raw)
    print("=== Part 1a: DataFrame API による重複排除後（6件） ===")
    df_deduped.show(truncate=False)

    df_deduped_sql = dedup_with_spark_sql(df_raw, spark)
    print("=== Part 1b: Spark SQL による重複排除後（6件） ===")
    df_deduped_sql.show(truncate=False)

    df_top_n = get_top_n_per_category(df_deduped, top_n=2)
    print("=== Part 2: カテゴリ別 Top-2（DENSE_RANK） ===")
    df_top_n.show(truncate=False)

    spark.stop()
