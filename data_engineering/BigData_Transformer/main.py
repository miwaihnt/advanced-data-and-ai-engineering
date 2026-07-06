import asyncio

from bigdata_transform.core.config import settings
from bigdata_transform.generator.engine import data_engine
from bigdata_transform.core.config import setup_directories
from bigdata_transform.core.utils import MemoryMonitor
from bigdata_transform.transformer.engine import DataTransformer
from bigdata_transform.load.load import SnowflakeClient

async def main():
    setup_directories()
    client = DataTransformer()
    base_setting = settings

    # モニターの準備
    monitor = MemoryMonitor()

    # 監視をバックグラウンドプロセスで開始
    monitor_task = asyncio.create_task(monitor.start())

    # snowflake関連のクラスを初期化
    snowflake_client = SnowflakeClient(base_setting.snowflake)

    try:
        # メインのデータ生成・保存処理を開始
        await data_engine()
        client.process()
        # snowflake_client.put_files(base_setting.bronze_dir, base_setting.silver_dir)

    finally:
        # モニターの停止
        monitor.stop()
        await monitor_task

if __name__ == "__main__":
    asyncio.run(main())
