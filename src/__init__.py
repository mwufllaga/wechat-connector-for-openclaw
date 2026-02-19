"""
WeChat Connector - 微信连接器

基于 Android 模拟器的微信消息读取方案
"""

__version__ = "1.0.0"
__author__ = "OpenClaw"

from .mmkv_reader import MMKVReader
from .message_dedup import MessageDeduplicator
from .connector import WeChatConnector
from .sender import WeChatSender, send_message

__all__ = [
    "MMKVReader",
    "MessageDeduplicator",
    "WeChatConnector",
    "WeChatSender",
    "send_message",
]
