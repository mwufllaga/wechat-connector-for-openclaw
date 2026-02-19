#!/usr/bin/env python3
"""启动 connector"""
import sys
sys.path.insert(0, '/Users/mwu/.openclaw/workspace/weChat-connector')

from src.connector import WeChatConnector

connector = WeChatConnector()
print("启动 connector...")
connector.start_polling()
