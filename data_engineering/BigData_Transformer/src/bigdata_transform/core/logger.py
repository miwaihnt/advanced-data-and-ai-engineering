import logging
import structlog

from typing import Any

def setup_logging(level: str = "INFO") -> None:

    # 共通プロセッサの定義
    processors: list[Any] = [
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer
    ]

    # structlogの設定
    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%x]"
    )



def get_logger(name: str) -> Any:
    return structlog.get_logger(name)