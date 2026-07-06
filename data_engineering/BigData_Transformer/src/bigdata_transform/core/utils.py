import psutil
import os
import asyncio

from bigdata_transform.core.logger import get_logger

class MemoryMonitor:

    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.is_running = False
        self.peak_memory = 0.0
        self.logger = get_logger(__name__)

    
    async def start(self) -> None:

        self.is_running = True
        self.logger.info("memory monitoring started")

        while self.is_running:
                now_rss = self.process.memory_info().rss / (1024 * 1024)
                self.peak_memory = max(self.peak_memory, now_rss)

                if now_rss > 500:
                     self.logger.warning(f"⚠️ DANGER! Memory usage is critical: {now_rss:.2f} MB")

                await asyncio.sleep(1)
    
    def stop(self):
        self.is_running = False
        self.logger.info(f"Memory Monitoring stopped. Peak memory: {self.peak_memory:.2f} MB")
            

    




