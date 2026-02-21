"""
Unified HTTP client with retry mechanism and rate limiting.

Provides unified configuration and error handling for all SEC EDGAR HTTP requests.
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
from typing import Optional
from .rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)


def get_session(user_agent: str, timeout: int = 30) -> requests.Session:
    """Create a configured requests Session with retry strategy.
    
    Configuration includes:
    - Automatic retry mechanism (up to 3 attempts)
    - Exponential backoff strategy (1s, 2s, 4s)
    - Standardized headers (mimics real browser)
    - Timeout settings
    
    Args:
        user_agent: User-Agent string (must include real name and email)
        timeout: Default timeout in seconds
    
    Returns:
        Configured requests.Session object
    """
    session = requests.Session()
    
    # Configure retry strategy
    # total: Maximum 3 retries
    # backoff_factor: Exponential backoff, wait time = {backoff factor} * (2 ** (retry_count - 1))
    #                 i.e., 1s, 2s, 4s
    # status_forcelist: Retry on these HTTP status codes
    # allowed_methods: Only retry these HTTP methods
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
        raise_on_status=False,  # Don't auto-raise exceptions, let caller handle
    )
    
    # Create HTTP adapter and mount to session
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    # Set standardized headers (mimics real browser)
    session.headers.update({
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "DNT": "1",
        "Connection": "keep-alive",
    })
    
    logger.debug(f"HTTP Session created, User-Agent: {user_agent[:50]}...")
    
    return session


def rate_limited_get(
    url: str,
    session: requests.Session,
    timeout: Optional[int] = None,
    **kwargs
) -> requests.Response:
    """Execute rate-limited GET request with logging.
    
    Automatically applies rate limiting before sending request to ensure
    compliance with SEC EDGAR access restrictions. Logs request details
    and results for monitoring and debugging.
    
    Args:
        url: Request URL
        session: requests.Session object
        timeout: Timeout in seconds, uses session default if not specified
        **kwargs: Additional parameters passed to requests.get
    
    Returns:
        requests.Response object
        
    Raises:
        requests.RequestException: Network request failed
    """
    limiter = get_rate_limiter()
    
    # Log pre-request state
    logger.debug(f"Preparing request: {url}")
    
    # Apply rate limiting
    wait_time = limiter.wait_if_needed()
    if wait_time > 0:
        logger.debug(f"Rate limit: waited {wait_time:.3f}s")
    
    # Execute request
    try:
        response = session.get(url, timeout=timeout, **kwargs)
        
        # Log successful request
        content_length = len(response.content)
        logger.info(
            f"Request successful: {url} "
            f"(status: {response.status_code}, "
            f"size: {content_length:,} bytes)"
        )
        
        # Check HTTP status
        response.raise_for_status()
        
        return response
        
    except requests.exceptions.Timeout as e:
        logger.error(f"Request timeout: {url} - {e}")
        raise
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else "unknown"
        logger.error(f"HTTP error: {url} (status: {status_code}) - {e}")
        raise
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error: {url} - {e}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {url} - {e}")
        raise


def rate_limited_head(
    url: str,
    session: requests.Session,
    timeout: Optional[int] = None,
    **kwargs
) -> requests.Response:
    """Execute rate-limited HEAD request.
    
    Used to check if a resource exists without downloading full content.
    
    Args:
        url: Request URL
        session: requests.Session object
        timeout: Timeout in seconds
        **kwargs: Additional parameters passed to requests.head
    
    Returns:
        requests.Response object
    """
    limiter = get_rate_limiter()
    
    logger.debug(f"Preparing HEAD request: {url}")
    
    # Apply rate limiting
    wait_time = limiter.wait_if_needed()
    if wait_time > 0:
        logger.debug(f"Rate limit: waited {wait_time:.3f}s")
    
    # Execute request
    try:
        response = session.head(url, timeout=timeout, **kwargs)
        logger.info(f"HEAD request successful: {url} (status: {response.status_code})")
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        logger.error(f"HEAD request failed: {url} - {e}")
        raise
