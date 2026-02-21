"""
速率限制器，确保遵守 SEC EDGAR 的访问限制

SEC 要求最多 10 请求/秒，本模块提供线程安全的速率限制功能。
"""

import time
import threading
import os
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """全局速率限制器，确保遵守 SEC EDGAR 10 req/s 限制
    
    使用简单的时间间隔控制算法，确保相邻两次请求之间有足够的时间间隔。
    线程安全，可在多线程环境中使用。
    
    Args:
        max_calls_per_second: 每秒最大请求数，默认 8（保守策略）
    """

    def __init__(self, max_calls_per_second: float = 8.0):
        if max_calls_per_second <= 0:
            raise ValueError("max_calls_per_second 必须大于 0")
        
        self.max_calls = max_calls_per_second
        # 计算最小时间间隔（秒）
        self.min_interval = 1.0 / max_calls_per_second
        self.last_call = 0.0
        self.lock = threading.Lock()
        
        logger.info(f"速率限制器已初始化: {max_calls_per_second} 请求/秒 (间隔: {self.min_interval:.3f}秒)")

    def wait_if_needed(self) -> float:
        """如需要则等待，确保不超过速率限制
        
        Returns:
            实际等待的时间（秒），如果不需要等待则返回 0
        """
        with self.lock:
            current = time.time()
            elapsed = current - self.last_call
            
            if elapsed < self.min_interval:
                # 需要等待
                sleep_time = self.min_interval - elapsed
                logger.debug(f"速率限制：等待 {sleep_time:.3f}秒")
                time.sleep(sleep_time)
                self.last_call = time.time()
                return sleep_time
            else:
                # 不需要等待
                self.last_call = current
                return 0.0


# 全局单例实例
_global_limiter = None
_limiter_lock = threading.Lock()


def get_rate_limiter() -> RateLimiter:
    """获取全局速率限制器单例
    
    从环境变量 SEC_EDGAR_RATE_LIMIT 读取配置，默认 8 请求/秒。
    
    Returns:
        全局 RateLimiter 实例
    """
    global _global_limiter
    
    if _global_limiter is None:
        with _limiter_lock:
            # 双重检查锁定
            if _global_limiter is None:
                try:
                    rate = float(os.getenv("SEC_EDGAR_RATE_LIMIT", "8"))
                    if rate <= 0 or rate > 10:
                        logger.warning(
                            f"SEC_EDGAR_RATE_LIMIT={rate} 超出合理范围 (0, 10]，使用默认值 8"
                        )
                        rate = 8.0
                except ValueError:
                    logger.warning(
                        f"SEC_EDGAR_RATE_LIMIT 配置无效，使用默认值 8"
                    )
                    rate = 8.0
                
                _global_limiter = RateLimiter(rate)
    
    return _global_limiter


def reset_rate_limiter():
    """重置全局速率限制器（主要用于测试）"""
    global _global_limiter
    with _limiter_lock:
        _global_limiter = None
