#!/usr/bin/env python3
"""
WeChat Connector 主连接器
整合所有模块，实现完整的微信消息收发功能
"""

import os
import sys
import time
import json
import hashlib
import argparse
import urllib.request
from typing import Optional, List, Dict, Any
from datetime import datetime

# 导入子模块
from .mmkv_reader import MMKVReader
from .message_dedup import MessageDeduplicator


class WeChatConnector:
    """微信连接器主类"""

    def __init__(self,
                 data_dir: str = None,
                 poll_interval: float = 1.0):
        """
        初始化连接器

        Args:
            data_dir: 数据目录
            poll_interval: 轮询间隔（秒）
        """
        # 设置数据目录
        if data_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(base_dir, "data")

        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

        self.poll_interval = poll_interval

        # 初始化各模块
        self.reader = MMKVReader()
        self.dedup = MessageDeduplicator(os.path.join(data_dir, "dedup_state.json"))

        # 运行状态
        self._running = False

        print("=" * 50)
        print("WeChat Connector 初始化完成")
        print(f"数据目录: {data_dir}")
        print(f"轮询间隔: {poll_interval} 秒")
        print("=" * 50)

    def check_device(self) -> bool:
        """检查设备连接状态"""
        return self.reader.check_device_connected()

    def _extract_pushcontent(self, content: str) -> List[Dict[str, str]]:
        """
        从 MMKV 内容中提取所有 pushcontent
        
        Returns:
            列表，每个元素包含 nickname 和 content
        """
        import re
        results = []
        pattern = r'<pushcontent\s+content="([^"]*)"\s+nickname="([^"]*)"\s*/>'
        matches = re.findall(pattern, content)
        
        for content_text, nickname in matches:
            results.append({
                "content": content_text,
                "nickname": nickname
            })
        
        return results

    def _parse_message(self, pushcontent: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        解析单条 pushcontent 为结构化消息
        
        Args:
            pushcontent: {"content": "...", "nickname": "..."}
            
        Returns:
            {"sender": "...", "content": "...", "is_group": bool, "chat_name": "..."}
        """
        nickname = pushcontent["nickname"].strip()
        content_text = pushcontent["content"]
        
        # 群聊判断：nickname 是 "群聊" 或 "group_with_AI"
        is_group = (nickname == "群聊" or nickname == "group_with_AI")
        
        if is_group:
            # 群聊：从 content 提取发送者和消息内容
            # 格式: " 发送者 : 消息内容"
            chat_name = "group_with_AI"
            if " : " in content_text:
                parts = content_text.split(" : ", 1)
                sender = parts[0].strip()
                msg_content = parts[1].strip() if len(parts) > 1 else ""
            else:
                sender = "未知"
                msg_content = content_text
        else:
            # 私聊：nickname 就是发送者
            sender = nickname
            chat_name = "Mwu！"
            # 从 content 提取实际消息内容
            if " : " in content_text:
                parts = content_text.split(" : ", 1)
                msg_content = parts[1].strip() if len(parts) > 1 else content_text
            else:
                msg_content = content_text
        
        return {
            "sender": sender,
            "content": msg_content,
            "is_group": is_group,
            "chat_name": chat_name
        }

    def _compute_message_id(self, is_group: bool, sender: str, content: str) -> str:
        """
        计算消息唯一 ID
        
        去重键：md5(f"{is_group}:{sender}:{content}")
        """
        key = f"{is_group}:{sender}:{content}"
        return hashlib.md5(key.encode('utf-8')).hexdigest()

    def _send_to_webhook(self, chat_name: str, sender: str, content: str) -> bool:
        """
        发送消息到 OpenClaw webhook
        
        Args:
            chat_name: "Mwu！" 或 "group_with_AI"
            sender: 发送者昵称
            content: 消息内容
            
        Returns:
            是否成功
        """
        webhook_url = "http://127.0.0.1:18789/hooks/wake"
        payload = {
            "text": f"[微信消息] [{chat_name}] [{sender}] {content}",
            "mode": "now"
        }
        
        try:
            req = urllib.request.Request(
                webhook_url,
                data=json.dumps(payload).encode('utf-8'),
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer wechat-bridge-2026'
                },
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status == 200
        except Exception as e:
            print(f"[ERROR] Webhook 发送失败: {e}")
            return False

    def process_message(self, pushcontent: Dict[str, str]) -> bool:
        """
        处理单条 pushcontent 消息
        
        Args:
            pushcontent: {"content": "...", "nickname": "..."}
            
        Returns:
            是否成功处理（新消息且发送成功）
        """
        # 解析消息
        msg = self._parse_message(pushcontent)
        if not msg:
            return False
        
        sender = msg["sender"]
        content = msg["content"]
        is_group = msg["is_group"]
        chat_name = msg["chat_name"]
        
        # 计算消息 ID
        message_id = self._compute_message_id(is_group, sender, content)
        
        # 检查是否已处理
        if self.dedup.is_processed(message_id):
            return False
        
        print(f"[NEW] {'[群聊]' if is_group else '[私聊]'} {sender}: {content[:50]}")
        
        # 发送到 webhook
        success = self._send_to_webhook(chat_name, sender, content)
        
        if success:
            # 标记为已处理
            self.dedup.mark_processed(message_id)
            print(f"[OK] 消息已发送到主 session")
            return True
        else:
            print(f"[FAIL] 消息发送失败，不标记为已处理")
            return False

    def poll_once(self) -> int:
        """
        执行一次轮询

        Returns:
            处理的新消息数量
        """
        # 读取 MMKV 文件
        content = self.reader.read_text_content()
        if content is None:
            return 0
        
        # 提取所有 pushcontent
        pushcontents = self._extract_pushcontent(content)
        if not pushcontents:
            return 0
        
        print(f"[POLL] 发现 {len(pushcontents)} 条 pushcontent")
        
        # 处理每条消息
        processed_count = 0
        for pc in pushcontents:
            if self.process_message(pc):
                processed_count += 1
        
        return processed_count

    def start_polling(self):
        """开始轮询监听"""
        if not self.check_device():
            print("错误: 设备未连接，请检查 ADB 连接")
            return

        print("\n开始轮询监听消息...")
        print("按 Ctrl+C 停止\n")

        self._running = True

        try:
            while self._running:
                processed = self.poll_once()
                if processed > 0:
                    print(f"  本次处理了 {processed} 条新消息\n")

                time.sleep(self.poll_interval)

        except KeyboardInterrupt:
            print("\n\n停止监听")
            self._running = False

    def stop_polling(self):
        """停止轮询"""
        self._running = False

    def get_status(self) -> Dict[str, Any]:
        """获取连接器状态"""
        return {
            "device_connected": self.check_device(),
            "running": self._running,
            "dedup": self.dedup.get_stats(),
            "data_dir": self.data_dir
        }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="WeChat Connector")
    parser.add_argument("--data-dir", help="数据目录")
    parser.add_argument("--poll-interval", type=float, default=1.0, help="轮询间隔（秒）")
    parser.add_argument("--action", choices=["start", "status"],
                       default="start", help="操作")

    args = parser.parse_args()

    # 创建连接器
    connector = WeChatConnector(
        data_dir=args.data_dir,
        poll_interval=args.poll_interval
    )

    if args.action == "start":
        connector.start_polling()
    elif args.action == "status":
        status = connector.get_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
