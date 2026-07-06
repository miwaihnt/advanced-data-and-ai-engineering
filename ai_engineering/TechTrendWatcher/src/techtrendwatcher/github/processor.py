from datetime import datetime
from pathlib import Path
import polars as pl
from techtrendwatcher.core.logger import get_logger
from techtrendwatcher.models.base import TrendItem

def convert_to_dataframe(items: list[TrendItem]) -> pl.DataFrame:
    """共通モデルのリストをDataFrameに変換するわ。"""
    data = [item.model_dump() for item in items]
    df = pl.DataFrame(data)
    df = df.with_columns(captured_at=pl.lit(datetime.now()))
    return df

def save_as_parquet(df: pl.DataFrame, query: str, source: str) -> None:
    """ソースごとにディレクトリを分けて保存するわよ。"""
    logger = get_logger(__name__)
    project_path = Path(__file__).parent.parent
    safe_query = query.replace(" ", "_").lower()

    # data/raw/{source}/{query}/ 形式で保存
    save_dir = project_path / "data" / "raw" / source / safe_query
    save_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_path = save_dir / f"trend_{timestamp}.parquet"

    df.write_parquet(save_path)
    logger.info("save_dataframe_to_file", source=source, path=str(save_path))

def get_trend_dataframe(current_df: pl.DataFrame, query: str, source: str) -> pl.DataFrame:
    """前回データとの比較。ソース名を考慮するのを忘れないで。"""
    logger = get_logger(__name__)
    project_path = Path(__file__).parent.parent
    safe_query = query.replace(" ", "_").lower()
    file_dir = project_path / "data" / "raw" / source / safe_query

    sorted_files = sorted(file_dir.glob("*.parquet"))
    # 自分自身の保存直後だから、2つ以上あれば比較可能
    if len(sorted_files) >= 2:
        prev_file = sorted_files[-2]
        logger.info("comparing_with_prev_file", prev_file=prev_file.name)
        prev_df = pl.read_parquet(prev_file)

        # 外部IDで結合
        join_df = current_df.join(prev_df, on="external_id", how="left", suffix="_prev")

        trend_df = join_df.with_columns(
            score_delta=(
                pl.col("score") - pl.col("score_prev").fill_null(0)
            )
        ).filter(pl.col("score_delta") > 0)

        return trend_df
    else:
        return current_df.with_columns(score_delta=pl.col("score"))

