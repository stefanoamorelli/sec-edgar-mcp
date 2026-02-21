"""
SEC EDGAR MCP 配置模块

管理所有配置项，包括：
- User-Agent 配置
- 速率限制配置
- 超时配置
- 本地缓存配置
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# 自动加载 .env 文件（如果存在）
try:
    from dotenv import load_dotenv
    
    # 尝试从多个位置加载 .env
    env_locations = [
        Path.cwd() / ".env",                    # 当前目录
        Path(__file__).parent.parent / ".env", # 项目根目录
    ]
    
    for env_file in env_locations:
        if env_file.exists():
            load_dotenv(env_file)
            logger.debug(f"已加载环境变量文件: {env_file}")
            break
except ImportError:
    logger.debug("python-dotenv 未安装，跳过 .env 文件加载")
except Exception as e:
    logger.warning(f"加载 .env 文件失败: {e}")


def initialize_config():
    """初始化 SEC EDGAR 基础配置，返回 User-Agent
    
    SEC 要求 User-Agent 必须包含真实姓名和邮箱地址，格式如：
    "Your Name (your@email.com)"
    
    Returns:
        User-Agent 字符串
        
    Raises:
        ValueError: 如果 SEC_EDGAR_USER_AGENT 未设置或格式不正确（缺少邮箱）
    """
    sec_edgar_user_agent = os.getenv("SEC_EDGAR_USER_AGENT")
    if not sec_edgar_user_agent:
        raise ValueError("SEC_EDGAR_USER_AGENT environment variable is not set.")
    
    # 验证格式：必须包含邮箱地址（简单检查是否包含 @ 符号）
    if "@" not in sec_edgar_user_agent:
        raise ValueError(
            "SEC_EDGAR_USER_AGENT 必须包含真实邮箱地址。\n"
            "格式示例: 'Your Name (your@email.com)'\n"
            f"当前值: {sec_edgar_user_agent}"
        )

    logger.info(f"SEC EDGAR 配置已初始化，User-Agent: {sec_edgar_user_agent[:50]}...")
    return sec_edgar_user_agent


def initialize_edgar_cache():
    """初始化 edgartools 本地存储缓存
    
    读取 SEC_EDGAR_CACHE_DIR 环境变量，配置 edgartools 的本地存储功能。
    启用后可实现：
    - 数据持久化缓存
    - 离线访问能力
    - 79x 性能提升（后续查询）
    
    Returns:
        缓存目录的完整路径
    """
    cache_dir = os.getenv("SEC_EDGAR_CACHE_DIR", "~/.cache/sec-edgar")
    
    # 展开 ~ 为用户主目录，并转换为绝对路径
    cache_path = os.path.abspath(os.path.expanduser(cache_dir))
    
    # 创建缓存目录
    try:
        os.makedirs(cache_path, exist_ok=True)
        logger.info(f"缓存目录已创建/确认: {cache_path}")
    except OSError as e:
        logger.warning(f"无法创建缓存目录 {cache_path}: {e}")
        # 继续执行，让 edgartools 使用默认位置
    
    # 必须在导入 edgar 模块之前设置环境变量
    # edgartools 会在导入时读取此环境变量
    os.environ["EDGAR_LOCAL_DATA_DIR"] = cache_path
    
    # 启用 edgartools 本地存储
    try:
        # 注意：必须在导入其他 edgar 模块之前调用
        import edgar
        edgar.use_local_storage(cache_path)
        logger.info(f"✅ edgartools 本地存储已启用: {cache_path}")
        logger.info("📊 后续查询将获得最多 79x 性能提升")
        
        # 验证路径是否生效
        if hasattr(edgar, 'get_local_data_path'):
            actual_path = edgar.get_local_data_path()
            if actual_path != cache_path:
                logger.warning(f"⚠️  实际缓存路径与配置不符: {actual_path}")
    except ImportError:
        logger.warning("无法导入 edgar，可能是 edgartools 版本不支持")
    except Exception as e:
        logger.warning(f"无法启用 edgartools 本地存储: {e}")
    
    return cache_path


def get_rate_limit():
    """获取速率限制配置（请求/秒）
    
    从环境变量 SEC_EDGAR_RATE_LIMIT 读取，默认 8 请求/秒。
    SEC 官方限制为 10 请求/秒，默认值提供了安全余量。
    
    Returns:
        每秒最大请求数
    """
    try:
        rate = float(os.getenv("SEC_EDGAR_RATE_LIMIT", "8"))
        if rate <= 0 or rate > 10:
            logger.warning(
                f"SEC_EDGAR_RATE_LIMIT={rate} 超出合理范围 (0, 10]，使用默认值 8"
            )
            return 8.0
        return rate
    except ValueError:
        logger.warning("SEC_EDGAR_RATE_LIMIT 配置无效，使用默认值 8")
        return 8.0


def get_timeout():
    """获取请求超时配置（秒）
    
    从环境变量 SEC_EDGAR_TIMEOUT 读取，默认 30 秒。
    对于大文件下载，可以设置更长的超时时间（如 60-120 秒）。
    
    Returns:
        超时时间（秒）
    """
    try:
        timeout = int(os.getenv("SEC_EDGAR_TIMEOUT", "30"))
        if timeout <= 0:
            logger.warning(f"SEC_EDGAR_TIMEOUT={timeout} 必须大于 0，使用默认值 30")
            return 30
        return timeout
    except ValueError:
        logger.warning("SEC_EDGAR_TIMEOUT 配置无效，使用默认值 30")
        return 30
