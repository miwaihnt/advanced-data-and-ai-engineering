import polars as pl
import datetime
from pydantic import ValidationError

from bigdata_transform.core.config import settings
from bigdata_transform.core.logger import get_logger
from bigdata_transform.schema.ecommerce import Transaction, pydantic_to_polars

class DataTransformer:

    def __init__(self):
       self.logger = get_logger(__name__)
       self.input_dir = settings.raw_dir
       self.bronze_dir = settings.bronze_dir 
       self.silver_dir = settings.silver_dir


    def process(self):
        self.logger.info("DataTransforme process started")
        time = datetime.datetime.now(datetime.timezone.utc)
        run_id = time.strftime("%Y%m%d_%H%M%S")
        valid_status = ["success", "failed", "pending"]

        # pydanticの型定義を読み込む
        schema = pydantic_to_polars(Transaction)


        # 全ファイルを読み込む
        lf = pl.scan_ndjson(self.input_dir / "*.jsonl", schema=schema)

        # 型変換
        lf = lf.with_columns([
            pl.col("timestamp").str.to_datetime()
        ])

        # 不正なレコードを排除する
        invalid_df = lf.filter(
            (pl.col("amount") < 0) |
            (~pl.col("status").is_in(valid_status))
        ).collect()

        for row in invalid_df.to_dicts():
            try:
                Transaction(**row)
            except ValidationError as e:
                self.logger.error(f"invalid record found: {row}", error=e)

        valid_df = lf.filter(
            (pl.col("amount") >= 0),
            (pl.col("status").is_in(valid_status))
        )

        # Bronze Dataを生成する
        valid_df.sink_parquet(self.bronze_dir / f"{run_id}_bronze.parquet")

        # Silver Dataを生成する
        product_summary = valid_df.group_by("product_id").agg([
            pl.sum("amount").alias("total_sales"),
            pl.count("transaction_id").alias("transaction_count"),
            pl.mean("amount").alias("avg_amount")            
        ])

        product_summary.collect(streaming=True).write_parquet(self.silver_dir / f"{run_id}_silver.parquet")
        self.logger.info("DataTransforme process finished")

    

