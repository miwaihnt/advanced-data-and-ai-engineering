import asyncio
import httpx
from techtrendwatcher.core.config import get_settings
from techtrendwatcher.core.logger import get_logger, setup_logging
from techtrendwatcher.github.client import GithubClient
from techtrendwatcher.reddit.client import RedditClient
from techtrendwatcher.github.processor import (
    convert_to_dataframe,
    get_trend_dataframe,
    save_as_parquet,
)
from techtrendwatcher.notion.client import NotionClient
from techtrendwatcher.snowflake.client import SnowflakeClient
from techtrendwatcher.core.base import BaseTrendSource

async def process_query(
    source: BaseTrendSource,
    query: str,
    notion_client: NotionClient,
    settings: Any
) -> None:
    logger = get_logger(__name__)
    source_name = source.__class__.__name__.lower().replace("client", "")
    
    try:
        # 1. Extraction (Normalized TrendItem)
        items = await source.fetch_trends(query)
        if not items:
            return

        # 2. Transformation
        df = convert_to_dataframe(items)
        
        # 3. Save & Diff
        save_as_parquet(df, query, source=source_name)
        trend_df = get_trend_dataframe(df, query, source=source_name)

        # 4. Loading (Notion & Snowflake)
        # ※ NotionClient/SnowflakeClient側の修正が必要な場合があるけど、
        # ここではオーケストレーションの形を示すわよ。
        snowflake_client = SnowflakeClient(settings.snowflake)
        
        # 本来はここでSemaphoreを使った並列実行をするけど、簡略化して示すわ
        tasks = []
        for row in trend_df.to_dicts():
            # Notion用のマッピング（sourceに応じて変える等の工夫が必要ね）
            tasks.append(notion_client.upsert_repo(row))
        
        await asyncio.gather(
            asyncio.gather(*tasks),
            snowflake_client.upload_to_snowflake(df)
        )
        logger.info("pipeline_success", source=source_name, query=query)

    except Exception as e:
        logger.error("pipeline_failed", source=source_name, query=query, error=str(e))

async def main() -> None:
    setup_logging()
    logger = get_logger(__name__)
    logger.info("multi_source_pipeline_startup")

    try:
        settings = get_settings()
    except Exception as e:
        logger.error("config_load_failed", error=str(e))
        return

    async with httpx.AsyncClient() as shared_client:
        sources: list[BaseTrendSource] = [
            GithubClient(shared_client),
            RedditClient(shared_client)
        ]
        notion_client = NotionClient(shared_client)

        # 全てのソース × 全てのクエリを並列実行！
        all_tasks = [
            process_query(source, query, notion_client, settings)
            for source in sources
            for query in settings.search_query
        ]
        
        await asyncio.gather(*all_tasks)

def run() -> None:
    asyncio.run(main())

if __name__ == "__main__":
    run()
