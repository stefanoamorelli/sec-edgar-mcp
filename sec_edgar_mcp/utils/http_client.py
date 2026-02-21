"""
统一的 HTTP 客户端，带重试机制和速率限制

为所有 SEC EDGAR HTTP 请求提供统一的配置和错误处理。
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
from typing import Optional
from .rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)


def get_session(user_agent: str, timeout: int = 30) -> requests.Session:
    """创建配置好的 requests Session，带重试策略
    
    配置包括：
    - 自动重试机制（最多 3 次）
    - 指数退避策略（1s, 2s, 4s）
    - 标准化的请求头（模拟真实浏览器）
    - 超时设置
    
    Args:
        user_agent: User-Agent 字符串（必须包含真实姓名和邮箱）
        timeout: 默认超时时间（秒）
    
    Returns:
        配置好的 requests.Session 对象
    """
    session = requests.Session()
    
    # 配置重试策略
    # total: 最多重试 3 次
    # backoff_factor: 指数退避，等待时间为 {backoff factor} * (2 ** (重试次数 - 1))
    #                 即: 1s, 2s, 4s
    # status_forcelist: 遇到这些 HTTP 状态码时重试
    # allowed_methods: 只对这些 HTTP 方法重试
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
        raise_on_status=False,  # 不自动抛出异常，让调用方处理
    )
    
    # 创建 HTTP 适配器并挂载到 session
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    # 设置标准化的请求头（模拟真实浏览器）
    session.headers.update({
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "DNT": "1",
        "Connection": "keep-alive",
    })
    
    logger.debug(f"HTTP Session 已创建，User-Agent: {user_agent[:50]}...")
    
    return session


def rate_limited_get(
    url: str,
    session: requests.Session,
    timeout: Optional[int] = None,
    **kwargs
) -> requests.Response:
    """执行速率限制的 GET 请求，带日志记录
    
    在发送请求前自动应用速率限制，确保不超过 SEC EDGAR 的访问限制。
    记录请求详情和结果，便于监控和调试。
    
    Args:
        url: 请求的 URL
        session: requests.Session 对象
        timeout: 超时时间（秒），如不指定则使用 session 默认值
        **kwargs: 传递给 requests.get 的其他参数
    
    Returns:
        requests.Response 对象
        
    Raises:
        requests.RequestException: 网络请求失败
    """
    limiter = get_rate_limiter()
    
    # 记录请求前状态
    logger.debug(f"准备请求: {url}")
    
    # 应用速率限制
    wait_time = limiter.wait_if_needed()
    if wait_time > 0:
        logger.debug(f"速率限制：已等待 {wait_time:.3f}秒")
    
    # 执行请求
    try:
        response = session.get(url, timeout=timeout, **kwargs)
        
        # 记录请求成功
        content_length = len(response.content)
        logger.info(
            f"请求成功: {url} "
            f"(状态: {response.status_code}, "
            f"大小: {content_length:,} bytes)"
        )
        
        # 检查 HTTP 状态
        response.raise_for_status()
        
        return response
        
    except requests.exceptions.Timeout as e:
        logger.error(f"请求超时: {url} - {e}")
        raise
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else "未知"
        logger.error(f"HTTP 错误: {url} (状态码: {status_code}) - {e}")
        raise
    except requests.exceptions.ConnectionError as e:
        logger.error(f"连接错误: {url} - {e}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"请求失败: {url} - {e}")
        raise


def rate_limited_head(
    url: str,
    session: requests.Session,
    timeout: Optional[int] = None,
    **kwargs
) -> requests.Response:
    """执行速率限制的 HEAD 请求
    
    用于检查资源是否存在而不下载完整内容。
    
    Args:
        url: 请求的 URL
        session: requests.Session 对象
        timeout: 超时时间（秒）
        **kwargs: 传递给 requests.head 的其他参数
    
    Returns:
        requests.Response 对象
    """
    limiter = get_rate_limiter()
    
    logger.debug(f"准备 HEAD 请求: {url}")
    
    # 应用速率限制
    wait_time = limiter.wait_if_needed()
    if wait_time > 0:
        logger.debug(f"速率限制：已等待 {wait_time:.3f}秒")
    
    # 执行请求
    try:
        response = session.head(url, timeout=timeout, **kwargs)
        logger.info(f"HEAD 请求成功: {url} (状态: {response.status_code})")
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        logger.error(f"HEAD 请求失败: {url} - {e}")
        raise
