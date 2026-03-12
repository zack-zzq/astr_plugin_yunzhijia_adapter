from astrbot.api.star import Context, Star, register
from astrbot.api import logger

# Import to trigger @register_platform_adapter side-effect
from .yunzhijia_adapter import YunzhijiaPlatformAdapter  # noqa: F401

@register("yunzhijia_adapter", "zack-zzq", "云之家平台适配器插件", "1.0.0")
class YunzhijiaAdapterPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        logger.info("Yunzhijia adapter plugin initialized.")

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        logger.info("Yunzhijia adapter plugin terminated.")
