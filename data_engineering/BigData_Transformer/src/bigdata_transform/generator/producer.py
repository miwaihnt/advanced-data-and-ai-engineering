from faker import Faker
from typing import Any
import asyncio
import random
import json

from bigdata_transform.core.config import settings
from bigdata_transform.core.logger import get_logger

class DataProducer:

    def __init__(self, queue: asyncio.Queue, chunk_size: int = settings.chunk_size):
        self.fake = Faker('ja_JP')
        self.queue = queue
        self.chunk_size = chunk_size
        self.status_options = ["success", "failed", "pending"]
        self.weight = [80, 15, 5]
        self.logger = get_logger(__name__)
    
    # データの生成
    async def run(self, total_cnt: int) -> None:

        self.logger.info("DataProducer started")
        current_cnt = 0

        while current_cnt < total_cnt:
            self.logger.info(f"Processing・・・{current_cnt}/{total_cnt}")
            result = []

            # チャンクサイズ分のループ
            for _ in range(self.chunk_size):
                tmp_result = {
                    "transaction_id": current_cnt,
                    "user_id": random.randint(1,1000000),
                    "product_id": random.randint(1, 500),
                    "amount": random.randint(1, 5000),
                    "timestamp": self.fake.date_time_this_year().isoformat(),
                    "status": random.choices(self.status_options, self.weight)[0]
                }

                result.append(tmp_result)
                current_cnt += 1

                if current_cnt > total_cnt:
                    break
            
            await self.queue.put(result)
            await asyncio.sleep(0)
        
        await self.queue.put(None)
        self.logger.info("DataProducer finished")


            


        
