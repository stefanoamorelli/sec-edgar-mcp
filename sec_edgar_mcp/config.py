"""
SEC EDGAR MCP configuration module.

Manages all configuration items including:
- User-Agent configuration
- Rate limiting configuration
- Timeout configuration
- Local cache configuration
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Auto-load .env file if it exists
try:
    from dotenv import load_dotenv
    
    # Try loading .env from multiple locations
    env_locations = [
        Path.cwd() / ".env",                    # Current directory
        Path(__file__).parent.parent / ".env", # Project root
    ]
    
    for env_file in env_locations:
        if env_file.exists():
            load_dotenv(env_file)
            logger.debug(f"Loaded environment file: {env_file}")
            break
except ImportError:
    logger.debug("python-dotenv not installed, skipping .env file loading")
except Exception as e:
    logger.warning(f"Failed to load .env file: {e}")


def initialize_config():
    """Initialize SEC EDGAR base configuration, return User-Agent.
    
    SEC requires User-Agent to include real name and email address in format:
    "Your Name (your@email.com)"
    
    Returns:
        User-Agent string
        
    Raises:
        ValueError: If SEC_EDGAR_USER_AGENT is not set or format is incorrect (missing email)
    """
    sec_edgar_user_agent = os.getenv("SEC_EDGAR_USER_AGENT")
    if not sec_edgar_user_agent:
        raise ValueError("SEC_EDGAR_USER_AGENT environment variable is not set.")
    
    # Validate format: must contain email address (simple check for @ symbol)
    if "@" not in sec_edgar_user_agent:
        raise ValueError(
            "SEC_EDGAR_USER_AGENT must contain a valid email address.\n"
            "Format example: 'Your Name (your@email.com)'\n"
            f"Current value: {sec_edgar_user_agent}"
        )

    logger.info(f"SEC EDGAR configuration initialized, User-Agent: {sec_edgar_user_agent[:50]}...")
    return sec_edgar_user_agent


def initialize_edgar_cache():
    """Initialize edgartools local storage cache.
    
    Reads SEC_EDGAR_CACHE_DIR environment variable to configure edgartools
    local storage functionality. When enabled, provides:
    - Persistent data caching
    - Offline access capability
    - 79x performance improvement (for subsequent queries)
    
    Returns:
        Full path to cache directory
    """
    cache_dir = os.getenv("SEC_EDGAR_CACHE_DIR", "~/.cache/sec-edgar")
    
    # Expand ~ to user home directory and convert to absolute path
    cache_path = os.path.abspath(os.path.expanduser(cache_dir))
    
    # Create cache directory
    try:
        os.makedirs(cache_path, exist_ok=True)
        logger.info(f"Cache directory created/verified: {cache_path}")
    except OSError as e:
        logger.warning(f"Cannot create cache directory {cache_path}: {e}")
        # Continue execution, let edgartools use default location
    
    # Must set environment variable before importing edgar module
    # edgartools reads this environment variable during import
    os.environ["EDGAR_LOCAL_DATA_DIR"] = cache_path
    
    # Enable edgartools local storage
    try:
        # Note: Must be called before importing other edgar modules
        import edgar
        edgar.use_local_storage(cache_path)
        logger.info(f"✅ edgartools local storage enabled: {cache_path}")
        logger.info("📊 Subsequent queries will achieve up to 79x performance boost")
        
        # Verify path is effective
        if hasattr(edgar, 'get_local_data_path'):
            actual_path = edgar.get_local_data_path()
            if actual_path != cache_path:
                logger.warning(f"⚠️  Actual cache path differs from config: {actual_path}")
    except ImportError:
        logger.warning("Cannot import edgar, edgartools version may not support this")
    except Exception as e:
        logger.warning(f"Cannot enable edgartools local storage: {e}")
    
    return cache_path


def get_rate_limit():
    """Get rate limit configuration (requests/second).
    
    Reads from SEC_EDGAR_RATE_LIMIT environment variable, defaults to 8 req/s.
    SEC official limit is 10 req/s, default provides safety margin.
    
    Returns:
        Maximum requests per second
    """
    try:
        rate = float(os.getenv("SEC_EDGAR_RATE_LIMIT", "8"))
        if rate <= 0 or rate > 10:
            logger.warning(
                f"SEC_EDGAR_RATE_LIMIT={rate} out of valid range (0, 10], using default 8"
            )
            return 8.0
        return rate
    except ValueError:
        logger.warning("SEC_EDGAR_RATE_LIMIT invalid, using default 8")
        return 8.0


def get_timeout():
    """Get request timeout configuration (seconds).
    
    Reads from SEC_EDGAR_TIMEOUT environment variable, defaults to 30 seconds.
    For large file downloads, can set longer timeout (e.g., 60-120 seconds).
    
    Returns:
        Timeout in seconds
    """
    try:
        timeout = int(os.getenv("SEC_EDGAR_TIMEOUT", "30"))
        if timeout <= 0:
            logger.warning(f"SEC_EDGAR_TIMEOUT={timeout} must be greater than 0, using default 30")
            return 30
        return timeout
    except ValueError:
        logger.warning("SEC_EDGAR_TIMEOUT invalid, using default 30")
        return 30
