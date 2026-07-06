from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel, Field
from functools import lru_cache

class SnowflakeConfig(BaseModel):
  account: str
  user: str
  password: str
  role: str
  warehouse: str
  database: str
  snowflake_schema: str = Field(alias="schema")


class Settings(BaseSettings):

    """envの読み込みと設定"""
    model_config = SettingsConfigDict(
       env_file=".env", env_nested_delimiter="_", extra="ignore"
    )

    # dataディレクトリの設定
    root: Path = Path(__file__).parent.parent.parent.parent
    data_dir: Path = root / "data"
    raw_dir: Path = data_dir / "root"
    bronze_dir: Path =data_dir / "bronze"  #raw_dataをそのままParquetに変換したもの
    silver_dir: Path =data_dir / "silver" #raw_dataを集計しParquetに変換したもの
    
    # Producerの設定
    total_recods: int = 1000 #生成するrow数
    chunk_size: int = 100 #ファイル書き出しサイズ 
    max_queue_size: int = 3 #queueのサイズ 

    # snowflakeの設定
    snowflake: SnowflakeConfig

@lru_cache
def get_settings():
   return Settings()

settings = get_settings()

def setup_directories():
    settings.root.mkdir(parents=True, exist_ok=True)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.raw_dir.mkdir(parents=True, exist_ok=True)
    settings.bronze_dir.mkdir(parents=True, exist_ok=True)
    settings.silver_dir.mkdir(parents=True, exist_ok=True)

