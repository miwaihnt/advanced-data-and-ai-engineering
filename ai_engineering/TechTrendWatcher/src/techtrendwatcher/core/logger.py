import logging
from typing import Anyp

import structlog
n

def setup_logging() -> None:
    # 1. 共通プロセッサの定義
    processors: list[Any] = [
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer(),
    ]

    # structlogの設定
    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # 標準loggingの設定
    logging.basicConfig(
        format="%(message)s",
        level=logging.INFO,
    )


def get_logger(name: str) -> Any:
    return structlog.get_logger(name)
