import asyncio
from snowflake.snowpark import Session
from pathlib import Path

from bigdata_transform.core.config import SnowflakeConfig
from bigdata_transform.core.logger import get_logger

class SnowflakeClient:

    def __init__(self, account_parameter:SnowflakeConfig):
        self.logger = get_logger(__name__)
        self.parameters = account_parameter
        
        try:
            self.session = Session.builder.configs(self.parameters.model_dump()).create()
        except Exception as e:
            self.logger.error(f"snowflakeクライアントの初期化に失敗:{e}")

    def put_files(self, bronze_path: Path, silver_path: Path):

        # stageがなければ作成
        self.session.sql("CREATE STAGE IF NOT EXSITS DATA_LAKE.PUBLIC.BRONZE").collect()

        # bronze,silverのファイルアップロード
        bronze_file_upload = self.session.file.put(local_file_name=bronze_path/"*.parquet", stage_location="@BRONZE/bronze", parallel=4)
        silver_file_upload = self.session.file.put(local_file_name=silver_path/"*.parquet", stage_location="@BRONZE/silver", parallel=4)

        self.logge.info(f"file_upload_result bronze:{bronze_file_upload} silver: {silver_file_upload}")