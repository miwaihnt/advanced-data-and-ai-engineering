import asyncio

import polars as pl
from snowflake.snowpark import Session
from snowflake.connector import errors

from techtrendwatcher.core.config import SnowflakeConfig
from techtrendwatcher.core.exceptions import SnowflakeAPIError, SnowflakeAuthError
from techtrendwatcher.core.logger import get_logger


class SnowflakeClient:
    def __init__(self, account_parameter: SnowflakeConfig):
        self.logger = get_logger(__name__)
        self.settings = account_parameter
        self.table_name = self.settings.table

        try:
            self.session = Session.builder.configs(
                account_parameter.model_dump(by_alias=True)
            ).create()
        except Exception as e:
            raise SnowflakeAuthError(
                f"Snowflakeへの接続に失敗:{e}", original_error=e
            ) from e

    async def upload_to_snowflake(self, df: pl.DataFrame) -> None:

        # すべてのカラム名を大文字に変換する（Snowflake のお作法）
        df = df.rename({col: col.upper() for col in df.columns})

        # DataFrameをdictに変換
        pandas_df = df.to_pandas()

        try:
            # 書き込み
            await asyncio.to_thread(
                self.session.write_pandas,
                pandas_df,
                table_name=self.table_name,
                auto_create_table=True,
            )

        except errors.ProgrammingError as e:

            code = e.errno
            reasons = {
                2003: "object_not_found",                                                                                                                            
                390101: "warehouse_suspended",                                                                                                                                               
                904: "invalid_identifier",                                                                                                                                          
            }

            reason = reasons.get(code, "snowflake_programming_error")
            raise SnowflakeAPIError(
                f"Snowflakeの書き込みエラー",
                error_code = code,
                reason = reason,
                original_error=e
            ) from e

        except Exception as e:
            raise SnowflakeAPIError(
                f"Snowflakeへの書き込みに失敗:{e}", 
                reason="Unknown Snowflake Error",                
                original_error=e
            ) from e
