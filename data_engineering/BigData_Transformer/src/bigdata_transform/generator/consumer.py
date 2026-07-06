import asyncio
import datetime
import json
from pydantic_settings import BaseSettings

from bigdata_transform.core.logger import get_logger


class DataConsumer:

    def __init__(self, queue: asyncio.Queue):
        self.queue = queue
        self.logger = get_logger(__name__)
    
    async def run(self, settings: BaseSettings) -> None:
        self.logger.info("data save process started")
        now = datetime.datetime.now(datetime.timezone.utc)
        run_id = now.strftime("%Y%m%d_%H%M%S")
        part_id = 1
        cnt_byte = 0
        target_byte = 100000

        output_file = settings.raw_dir / f"{run_id}_{part_id:03d}.jsonl"

        f = open(output_file, "a", encoding="utf-8")

        try:
            while True:
                chunk = await self.queue.get()
                if chunk is None:
                    break
                
                for record in chunk:
                    line = json.dumps(record, separators=(',', ':')) + "\n"
                    line_byte = len(line.encode('utf-8'))
                    self.logger.info(f"data_byte:{line_byte}")
                
                    if cnt_byte + line_byte > target_byte:
                        self.logger.info(f"{output_file}が{target_byte}を超えました。新しいファイルに書き込みます")
                        f.close()

                        part_id += 1
                        output_file = settings.raw_dir / f"{run_id}_{part_id:03d}.jsonl"
                        cnt_byte = 0
                        f = open(output_file, "a", encoding="utf-8")
                    
                    f.write(line)
                    cnt_byte += line_byte
            
        finally:
            f.close()        
            self.logger.info("data save process finished")


