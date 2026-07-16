import logging
import json
import time
from typing import Optional, Any
from shadow.core.config import get_config
from shadow.core.database import get_db_connection

class DatabaseLogHandler(logging.Handler):
    def emit(self, record):
        try:
            # We construct structured log details if they were passed via extra
            reasoning = getattr(record, 'reasoning', None)
            action = getattr(record, 'action', record.getMessage())
            duration = getattr(record, 'duration', None)
            result_payload = getattr(record, 'result', None)
            error_payload = getattr(record, 'error', None)
            provider = getattr(record, 'provider', None)
            tokens = getattr(record, 'tokens', 0)
            cost = getattr(record, 'cost', 0.0)

            # If standard exception info is present and no custom error is provided, format it
            if record.exc_info and not error_payload:
                error_payload = logging.Formatter().formatException(record.exc_info)

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO system_logs (level, reasoning, action, duration, result, error, provider, tokens, cost)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.levelname,
                reasoning,
                action,
                duration,
                str(result_payload) if result_payload is not None else None,
                str(error_payload) if error_payload is not None else None,
                provider,
                tokens,
                cost
            ))
            conn.commit()
            conn.close()
        except Exception:
            # Prevent logging errors from crashing the main application loop
            pass

def setup_logging():
    config = get_config()
    level = getattr(logging, config.log_level.upper(), logging.INFO)

    # Configure root logger
    logger = logging.getLogger("shadow")
    logger.setLevel(level)

    # Clear handlers to avoid duplicate logs in live environments
    if logger.handlers:
        logger.handlers.clear()

    # Console Handler with a clean format
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(name)s - %(message)s', '%Y-%m-%d %H:%M:%S')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # DB Handler
    db_handler = DatabaseLogHandler()
    db_handler.setLevel(level)
    logger.addHandler(db_handler)

    return logger

# Global logger
logger = setup_logging()

def log_decision(
    level: str,
    action: str,
    reasoning: Optional[str] = None,
    duration: Optional[float] = None,
    result: Optional[Any] = None,
    error: Optional[Any] = None,
    provider: Optional[str] = None,
    tokens: int = 0,
    cost: float = 0.0
):
    """
    Convenience helper to write highly-structured agent/system actions to the logs.
    """
    extra = {
        'reasoning': reasoning,
        'action': action,
        'duration': duration,
        'result': result,
        'error': error,
        'provider': provider,
        'tokens': tokens,
        'cost': cost
    }
    lvl = getattr(logging, level.upper(), logging.INFO)
    logger.log(lvl, action, extra=extra)
