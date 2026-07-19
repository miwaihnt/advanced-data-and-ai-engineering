import asyncio
import json
import logging
from typing import AsyncGenerator, List
from openai import AsyncOpenAI
from pydantic import BaseModel, Field, ValidationError

# ==========================================
# ロギング設定
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logger = logging.getLogger("BackpressureStream")

# ==========================================
# Pydantic スキーマ定義
# ==========================================
class TransactionModel(BaseModel):
    transaction_id: str = Field(..., description="tx_から始まるID")
    user_id: str = Field(..., description="usr_から始まるID")
    amount: float = Field(..., gt=0, description="正の取引金額")
    currency: str = Field(..., description="JPY, USD, EUR などの通貨コード")

# ==========================================
# LLMストリームの解析ジェネレータ
# ==========================================
async def parse_llm_stream(stream) -> AsyncGenerator[TransactionModel, None]:
    """
    LLMからストリーミングされるトークンをバッファリングし、
    改行(\n)ごとに切り出してPydanticでバリデーションし、逐次yieldするわ。
    """
    buffer = ""
    async for chunk in stream:
        content = chunk.choices[0].delta.content
        if not content:
            continue
        
        buffer += content
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            line = line.strip()
            
            if not line or line.startswith("```"):
                continue
            
            first_brace = line.find("{")
            last_brace = line.rfind("}")
            if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                line = line[first_brace:last_brace + 1]
            
            try:
                data = json.loads(line)
                model = TransactionModel(**data)
                yield model
            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning(f"⚠️ [DLQ] Failed to parse line: {line[:50]}... Error: {e}")

# ==========================================
# パイプライン管理（バックプレッシャーとマイクロバッチ）
# ==========================================
class IngestionPipeline:
    def __init__(self, queue_size: int = 3, batch_size: int = 3, batch_timeout: float = 0.5):
        self.queue = asyncio.Queue(maxsize=queue_size)
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout

    async def producer(self, stream):
        """LLMの出力をパースしてQueueに詰めるプロデューサー"""
        logger.info("🎬 [Producer] Starting stream parse...")
        
        async for model in parse_llm_stream(stream):
            if self.queue.full():
                logger.info(f"⏳ [Producer] Queue FULL (size: {self.queue.qsize()})! Waiting for space to free up...")
            
            await self.queue.put(model)
            logger.info(f"📥 [Producer] Queued: {model.transaction_id} (Queue size: {self.queue.qsize()})")
        
        await self.queue.put(None)
        logger.info("🏁 [Producer] Completed pushing all data to queue.")

    async def consumer(self):
        """Queueからデータを取り出し、マイクロバッチ（バルクインサート）を行うコンシューマー"""
        batch: List[TransactionModel] = []
        logger.info("🚀 [Consumer] Starting DB Ingestion consumer...")

        while True:
            try:
                try:
                    item = await asyncio.wait_for(self.queue.get(), timeout=self.batch_timeout)
                except asyncio.TimeoutError:
                    if batch:
                        logger.info("⏱️ [Consumer] Timeout reached. Flushing remaining items...")
                        await self.bulk_insert(batch)
                        batch = []
                    continue

                if item is None:
                    if batch:
                        await self.bulk_insert(batch)
                    self.queue.task_done()
                    logger.info("🏁 [Consumer] Completed processing all items from queue.")
                    break

                batch.append(item)
                self.queue.task_done()

                # DB書き込みの「遅さ」をシミュレートしてバックプレッシャーを際立たせるわよ！
                # 1アイテムあたり2.0秒のウェイトをかけるわ
                logger.info(f"⚙️ [Consumer] Processing {item.transaction_id}... (Simulating DB latency)")
                await asyncio.sleep(2.0)

                if len(batch) >= self.batch_size:
                    await self.bulk_insert(batch)
                    batch = []

            except Exception as e:
                logger.error(f"❌ [Consumer Error]: {e}")

    async def bulk_insert(self, batch: List[TransactionModel]):
        """モック用のバルクインサート処理"""
        logger.info(f"💾 [DB Ingestion] >>> Bulk inserting {len(batch)} records to Database <<<")
        for m in batch:
            logger.info(f"  └─> Ingested: {m.transaction_id} ({m.amount} {m.currency})")
        logger.info("[DB Ingestion] >>> Ingestion Done <<<")

# ==========================================
# メイン実行関数
# ==========================================
async def main():
    client = AsyncOpenAI(
        base_url="http://localhost:11434/v1",
        api_key="ollama",
    )

    logger.info("🤖 Requesting NDJSON generation to Ollama...")
    
    try:
        response = await client.chat.completions.create(
            model="qwen2.5:3b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict JSON Lines (NDJSON) generator.\n"
                        "Each line you output must be a single, valid JSON object.\n"
                        "Do not wrap your output in markdown code blocks like ```json.\n"
                        "Do not include any explanation or extra text. Only JSON Lines.\n"
                        "Example line format:\n"
                        '{"transaction_id": "tx_101", "user_id": "usr_1001", "amount": 1500.0, "currency": "JPY"}'
                    )
                },
                {
                    "role": "user",
                    "content": "Please generate 15 transaction records."
                }
            ],
            stream=True,
            temperature=0.0
        )
    except Exception as e:
        logger.error(f"❌ Failed to connect to Ollama: {e}")
        logger.error("Make sure 'ollama serve' is running and 'qwen2.5:3b' model is installed.")
        return

    pipeline = IngestionPipeline(queue_size=3, batch_size=3)

    await asyncio.gather(
        pipeline.producer(response),
        pipeline.consumer()
    )

if __name__ == "__main__":
    asyncio.run(main())
