import asyncio
import json
import hmac
import hashlib
import time
from aiohttp import web

from astrbot.api.platform import Platform, AstrBotMessage, MessageMember, PlatformMetadata, MessageType
from astrbot.api.event import MessageChain
from astrbot.api.message_components import Plain, At
from astrbot.core.platform.astr_message_event import MessageSesion
from astrbot.api.platform import register_platform_adapter
from astrbot import logger

try:
    from .yunzhijia_event import YunzhijiaPlatformEvent
except ImportError:
    from yunzhijia_event import YunzhijiaPlatformEvent

@register_platform_adapter(
    "yunzhijia", 
    "云之家平台适配器", 
    default_config_tmpl={
        "host": "0.0.0.0",
        "port": 8090,
        "path": "/yzj/webhook",
        "send_msg_url": "",
        "secret": ""
    },
    adapter_display_name="云之家",
    logo_path="logo.png",
    config_metadata={
        "host": {
            "description": "监听 Host (默认 0.0.0.0)",
            "type": "string",
            "default": "0.0.0.0"
        },
        "port": {
            "description": "监听端口 (默认 8090)",
            "type": "int",
            "default": 8090
        },
        "path": {
            "description": "Webhook 路径 (默认 /yzj/webhook)",
            "type": "string",
            "default": "/yzj/webhook"
        },
        "send_msg_url": {
            "description": "发消息接口地址",
            "type": "string",
            "hint": "填入云之家后台的 Webhook URL"
        },
        "secret": {
            "description": "请求鉴权 Secret (可选)",
            "type": "string",
            "hint": "云之家推送消息时的 HMAC-SHA1 签名密钥。如果不填则不强制校验"
        },
        "logo_token": {
            "type": "string",
            "invisible": True
        }
    }
)
class YunzhijiaPlatformAdapter(Platform):

    def __init__(self, platform_config: dict, platform_settings: dict, event_queue: asyncio.Queue) -> None:
        super().__init__(platform_config, event_queue)
        self.config = platform_config
        self.settings = platform_settings
        self.app = web.Application()
        self.runner = None
        self.site = None
    
    async def send_by_session(self, session: MessageSesion, message_chain: MessageChain):
        # We need to construct an event and call its send method
        ev = YunzhijiaPlatformEvent(
            message_str="", 
            message_obj=AstrBotMessage(), 
            platform_meta=self.meta(), 
            session_id=session.session_id, 
            send_msg_url=self.config.get("send_msg_url")
        )
        await ev.send(message_chain)
        await super().send_by_session(session, message_chain)
    
    def meta(self) -> PlatformMetadata:
        return PlatformMetadata(
            "yunzhijia",
            "云之家适配器",
            "yunzhijia"
        )

    async def run(self):
        host = self.config.get("host", "0.0.0.0")
        port = self.config.get("port", 8090)
        path = self.config.get("path", "/yzj/webhook")

        self.app.router.add_post(path, self.handle_webhook)
        self.app.router.add_get(path, self.handle_health_check)

        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, host, port)
        await self.site.start()
        
        logger.info(f"Yunzhijia Adapter webhook listening on http://{host}:{port}{path}")

    async def terminate(self) -> None:
        if self.site:
            await self.site.stop()
            self.site = None
        if self.runner:
            await self.runner.cleanup()
            self.runner = None
        await super().terminate()
        logger.info("Yunzhijia Adapter webhook stopped.")

    async def handle_health_check(self, request: web.Request) -> web.Response:
        return web.Response(text="OK")

    def _verify_signature(self, request: web.Request, data: dict) -> bool:
        secret = self.config.get("secret")
        # Bypass validation if no secret is configured, or if it is a Yunzhijia test ping
        if not secret or data.get("robotId") == "test-robotId":
            return True 
            
        sign = request.headers.get("sign") or request.headers.get("Sign") or request.headers.get("SIGN")
        if not sign:
            logger.warning("Yunzhijia Webhook missing 'sign' header.")
            return False
            
        try:
            # Build signature string according to Yunzhijia specs:
            # robotId,robotName,operatorOpenid,operatorName,time,msgId,content
            time_str = str(data.get("time", ""))
            
            sig_parts = [
                data.get("robotId", ""),
                data.get("robotName", ""),
                data.get("operatorOpenid", ""),
                data.get("operatorName", ""),
                time_str,
                data.get("msgId", ""),
                data.get("content", "")
            ]
            signature_string = ",".join(sig_parts)
            
            # Compute HmacSHA1
            import base64
            hmac_obj = hmac.new(
                secret.encode('utf-8'),
                signature_string.encode('utf-8'),
                hashlib.sha1
            )
            expected_signature = base64.b64encode(hmac_obj.digest()).decode('utf-8')
            
            if sign == expected_signature:
                return True
            else:
                logger.warning(f"Yunzhijia signature mismatch. Expected: {expected_signature}, Got: {sign}")
                return False
        except Exception as e:
            logger.error(f"Error validating Yunzhijia signature: {e}")
            return False

    async def handle_webhook(self, request: web.Request) -> web.Response:
        raw_body = await request.text()
        
        try:
            data = json.loads(raw_body)
            if not isinstance(data, dict):
                return web.Response(status=400, text="invalid json payload, expected object")
        except json.JSONDecodeError:
            return web.Response(status=400, text="invalid json")

        if not self._verify_signature(request, data):
            return web.Response(status=401, text="invalid signature")

        # Typical YZJ Webhook format from openclaw reference:
        # { "type": 2, "robotId": "...", "operatorOpenid": "...", "operatorName": "...", "msgId": "...", "content": "..." }
        
        if "content" not in data:
            return web.Response(status=400, text="missing required fields")

        # Convert and commit to queue asynchronously so we can return response immediately
        abm = await self.convert_message(data)
        await self.handle_msg(abm)

        # ACK to Yunzhijia
        return web.json_response({
            "success": True,
            "data": {
                "type": 2,
                "content": ""
            }
        })

    async def convert_message(self, data: dict) -> AstrBotMessage:
        abm = AstrBotMessage()
        abm.type = MessageType.GROUP_MESSAGE # Yunzhijia bot usually works in group context
        abm.group_id = data.get("robotId", "")
        abm.self_id = data.get("robotId", "")
        
        content = data.get("content", "").strip()
        bot_name = data.get("robotName", "")
        
        message_chain = []
        import re
        if bot_name:
            # Yunzhijia payloads include the literal "@BotName " string in the text.
            # AstrBot needs us to strip this and inject an `At` component so its routing recognizes the mention.
            pattern = r"^(?:回复\s*)?@?" + re.escape(bot_name) + r"\s*[:：]?\s*"
            match = re.search(pattern, content)
            if match:
                message_chain.append(At(qq=abm.self_id))
                content = content[match.end():].strip()
                
        if content:
            message_chain.append(Plain(text=content))
            
        abm.message_str = content
        abm.message = message_chain if message_chain else [Plain(text="")]
        
        abm.sender = MessageMember(
            user_id=data.get("operatorOpenid", "unknown"), 
            nickname=data.get("operatorName", "未知用户")
        )
        abm.raw_message = data
        abm.session_id = data.get("robotId", "unknown") 
        abm.message_id = data.get("msgId", str(time.time()))
        
        return abm
    
    async def handle_msg(self, message: AstrBotMessage):
        message_event = YunzhijiaPlatformEvent(
            message_str=message.message_str,
            message_obj=message,
            platform_meta=self.meta(),
            session_id=message.session_id,
            send_msg_url=self.config.get("send_msg_url")
        )
        self.commit_event(message_event)
