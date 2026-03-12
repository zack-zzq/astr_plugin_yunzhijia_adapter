# astrbot_plugin_yunzhijia_adapter

✨ 为 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 提供云之家 (Yunzhijia) 机器人平台适配能力的插件。

## 简介
本插件是 AstrBot 的平台适配器，通过监听 Webhook 接收云之家机器人推送的消息，并解析为 AstrBot 可处理的标准格式。同时提供向云之家发送消息的能力，使 AstrBot 可以无缝对接到云之家平台。

## 特性
- **消息接收**：支持通过 Webhook 接收群聊（或机器人上下文）文本消息。
- **消息发送**：支持自动响应 AstrBot 处理后的纯文本消息到云之家。

## 安装与配置

请将本插件放置于 AstrBot 的 `data/plugins/` 目录中。如果您使用此源码仓库，请确保安装了相关依赖：
```bash
pip install aiohttp
```
（也可以在管理面板中一键重载安装或者通过 `requirements.txt` 自动安装）

### 插件配置 (`adapter.yunzhijia`)
在 AstrBot 的插件配置页面，或 `data/config.yaml` 对应适配器下填入以下配置项：

```json
{
    "host": "0.0.0.0",
    "port": 8090,
    "path": "/yzj/webhook",
    "send_msg_url": "YOUR_YUNZHIJIA_BOT_SEND_MSG_URL",
    "secret": ""
}
```

- `host`: Webhook 监听 IP (通常不需要修改，默认为 `0.0.0.0`)
- `port`: Webhook 监听端口 (默认为 `8090`)
- `path`: Webhook 监听路径 (默认为 `/yzj/webhook`)
- `send_msg_url`: 云之家机器人的发消息 API 地址 (必填)
- `secret`: 云之家机器人的验证密钥 (选填)

云之家平台侧，需要将机器人的回调地址(Webhook)填入为：`http://服务器IP:8090/yzj/webhook`。

## 当前局限性
- 根据云之家默认的机器人文本回调接口，目前主要对齐了纯文本 (`Plain`) 消息的收发。富文本/图片能力依据云之家的具体接口情况扩展。
