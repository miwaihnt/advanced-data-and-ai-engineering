import asyncio

from bigdata_transform.core.config import settings
from bigdata_transform.generator.producer import DataProducer
from bigdata_transform.generator.consumer import DataConsumer


async def data_engine():
    data_queue = asyncio.Queue(maxsize=settings.max_queue_size)
    producer = DataProducer(queue=data_queue)
    consumer = DataConsumer(queue=data_queue)

    await asyncio.gather(
        producer.run(total_cnt=settings.total_recods),
        consumer.run(settings)
    )

　