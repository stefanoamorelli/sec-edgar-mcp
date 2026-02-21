"""
Rate limiter to ensure compliance with SEC EDGAR access restrictions.

SEC requires a maximum of 10 requests/second. This module provides
thread-safe rate limiting functionality.
"""

import time
import threading
import os
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Global rate limiter to ensure SEC EDGAR 10 req/s compliance.
    
    Uses a simple time interval control algorithm to ensure sufficient time
    between adjacent requests. Thread-safe for use in multi-threaded environments.
    
    Args:
        max_calls_per_second: Maximum requests per second, default 8 (conservative)
    """

    def __init__(self, max_calls_per_second: float = 8.0):
        if max_calls_per_second <= 0:
            raise ValueError("max_calls_per_second must be greater than 0")
        
        self.max_calls = max_calls_per_second
        # Calculate minimum interval (seconds)
        self.min_interval = 1.0 / max_calls_per_second
        self.last_call = 0.0
        self.lock = threading.Lock()
        
        logger.info(f"Rate limiter initialized: {max_calls_per_second} req/s (interval: {self.min_interval:.3f}s)")

    def wait_if_needed(self) -> float:
        """Wait if necessary to ensure rate limit is not exceeded.
        
        Returns:
            Actual wait time (seconds), returns 0 if no wait needed
        """
        with self.lock:
            current = time.time()
            elapsed = current - self.last_call
            
            if elapsed < self.min_interval:
                # Need to wait
                sleep_time = self.min_interval - elapsed
                logger.debug(f"Rate limit: waiting {sleep_time:.3f}s")
                time.sleep(sleep_time)
                self.last_call = time.time()
                return sleep_time
            else:
                # No wait needed
                self.last_call = current
                return 0.0


# Global singleton instance
_global_limiter = None
_limiter_lock = threading.Lock()


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter singleton.
    
    Reads configuration from SEC_EDGAR_RATE_LIMIT environment variable,
    defaults to 8 requests/second.
    
    Returns:
        Global RateLimiter instance
    """
    global _global_limiter
    
    if _global_limiter is None:
        with _limiter_lock:
            # Double-checked locking
            if _global_limiter is None:
                try:
                    rate = float(os.getenv("SEC_EDGAR_RATE_LIMIT", "8"))
                    if rate <= 0 or rate > 10:
                        logger.warning(
                            f"SEC_EDGAR_RATE_LIMIT={rate} out of valid range (0, 10], using default 8"
                        )
                        rate = 8.0
                except ValueError:
                    logger.warning(
                        f"SEC_EDGAR_RATE_LIMIT invalid, using default 8"
                    )
                    rate = 8.0
                
                _global_limiter = RateLimiter(rate)
    
    return _global_limiter


def reset_rate_limiter():
    """Reset global rate limiter (primarily for testing)."""
    global _global_limiter
    with _limiter_lock:
        _global_limiter = None
