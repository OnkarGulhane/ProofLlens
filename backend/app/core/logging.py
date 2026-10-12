"""Structured logging configuration for ProofLens AI."""

import logging
import sys
from app.core.config import settings


def setup_logging() -> logging.Logger:
    """Configures structured root logging for the application."""
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    # Suppress overly chatty third-party loggers in debug mode
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("watchfiles").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    logger = logging.getLogger("prooflens")
    logger.setLevel(log_level)
    return logger


logger = setup_logging()
