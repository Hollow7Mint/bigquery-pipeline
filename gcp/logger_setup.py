import logging
import sys
from typing import Optional


def setup(
    name: str = "gcp-tool",
    level: str = "INFO",
    log_file: Optional[str] = None,
    fmt: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()

    formatter = logging.Formatter(fmt, datefmt="%Y-%m-%dT%H:%M:%S")

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.propagate = False
    return logger


class StructuredLogger:
    def __init__(self, name: str) -> None:
        self._log = logging.getLogger(name)

    def _fmt(self, msg: str, **kw) -> str:
        if not kw:
            return msg
        pairs = " ".join(f"{k}={v!r}" for k, v in kw.items())
        return f"{msg} {pairs}"

    def info(self, msg: str, **kw) -> None:
        self._log.info(self._fmt(msg, **kw))

    def warning(self, msg: str, **kw) -> None:
        self._log.warning(self._fmt(msg, **kw))

    def error(self, msg: str, **kw) -> None:
        self._log.error(self._fmt(msg, **kw))

    def debug(self, msg: str, **kw) -> None:
        self._log.debug(self._fmt(msg, **kw))
