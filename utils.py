import time
import logging
from functools import wraps
from typing import Callable, Any

logger = logging.getLogger(__name__)

def retry(retries: int = 3, delay: float = 1.0, exceptions: tuple = (Exception,)):
    """
    Simple retry decorator for transient API failures.
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    logger.warning(
                        f"Attempt {attempt + 1}/{retries} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
            logger.error(f"All {retries} attempts failed for {func.__name__}")
            raise last_exc
        return wrapper
    return decorator
