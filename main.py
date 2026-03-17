from astrbot.api.star import Context, Star

class YunzhijiaAdapterPlugin(Star):
    def __init__(self, context: Context):
        from .yunzhijia_adapter import YunzhijiaPlatformAdapter
