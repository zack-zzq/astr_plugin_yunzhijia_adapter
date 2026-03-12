from astrbot.api.event import AstrMessageEvent, MessageChain
from astrbot.api.platform import AstrBotMessage, PlatformMetadata
from astrbot.api import logger
import aiohttp

class YunzhijiaPlatformEvent(AstrMessageEvent):
    def __init__(self, message_str: str, message_obj: AstrBotMessage, platform_meta: PlatformMetadata, session_id: str, send_msg_url: str, client_session: aiohttp.ClientSession = None):
        super().__init__(message_str, message_obj, platform_meta, session_id)
        self.send_msg_url = send_msg_url
        self.client_session = client_session
        
    async def send(self, message: MessageChain):
        # We will compile text elements to send them as a single message
        text_content = ""
        
        for i in message.chain:
            if isinstance(i, Plain):
                text_content += i.text
            elif isinstance(i, Image):
                # Yunzhijia text webhook doesn't seem to natively support images based on openclaw reference
                logger.warning(f"Yunzhijia webhook interface currently does not support sending images natively. Ignoring image: {i.file}")
                text_content += "[图片]"
            else:
                logger.warning(f"Unsupported message component type for Yunzhijia: {type(i)}")

        if text_content:
            await self._send_yunzhijia_message(text_content)

        await super().send(message)
        
    async def _send_yunzhijia_message(self, text: str):
        if not self.send_msg_url:
            logger.error("Yunzhijia send_msg_url is not configured.")
            return

        payload = {
            "msgtype": 2, # Text message
            "content": text
        }
        
        # If we need to send to a specific group/user, we could theoretically populate notifyParams
        # Yunzhijia webhook usually defaults to replying in the same context where the bot is installed.
        # But we could check if we have a sender_id and add it to notifyParams for @ mentions.
        sender_id = self.get_sender_id()
        if sender_id and sender_id != 'unknown':
            payload["notifyParams"] = [{
                "type": "openIds",
                "values": [sender_id]
            }]

        try:
            if self.client_session and not self.client_session.closed:
                async with self.client_session.post(self.send_msg_url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Failed to send Yunzhijia message: HTTP {response.status} - {error_text}")
                    else:
                        logger.info(f"Successfully sent Yunzhijia message: {text[:50]}...")
            else:
                # Fallback to creating a single-use session if the long-lived one isn't available
                async with aiohttp.ClientSession() as session:
                    async with session.post(self.send_msg_url, json=payload) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"Failed to send Yunzhijia message: HTTP {response.status} - {error_text}")
                        else:
                            logger.info(f"Successfully sent Yunzhijia message: {text[:50]}...")
        except Exception as e:
            logger.error(f"Error sending Yunzhijia message: {e}")
