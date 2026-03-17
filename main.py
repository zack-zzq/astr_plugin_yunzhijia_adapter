from astrbot.api.star import Context, Star, register
from astrbot.api import logger

# Import to trigger @register_platform_adapter side-effect
from .yunzhijia_adapter import YunzhijiaPlatformAdapter  # noqa: F401
