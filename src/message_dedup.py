#!/usr/bin/env python3
"""
消息去重器
基于消息内容哈希实现去重

去重键：md5(f"{is_group}:{sender}:{content}")
存储文件：data/dedup_state.json
"""

import json
import os
from typing import Set, Dict, Any
from datetime import datetime


class MessageDeduplicator:
    """消息去重器"""

    def __init__(self, storage_path: str = None):
        """
        初始化去重器

        Args:
            storage_path: 存储文件路径，默认 data/dedup_state.json
        """
        if storage_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            storage_path = os.path.join(base_dir, "data", "dedup_state.json")

        self.storage_path = storage_path
        self._processed_ids: Set[str] = set()

        # 加载已有状态
        self._load()

    def _load(self):
        """从文件加载状态"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._processed_ids = set(data.get("processed_ids", []))
                print(f"[DEDUP] 已加载 {len(self._processed_ids)} 条已处理消息")
            except Exception as e:
                print(f"[DEDUP] 加载状态失败: {e}")
                self._processed_ids = set()

    def _save(self):
        """保存状态到文件"""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            data = {
                "processed_ids": list(self._processed_ids),
                "last_update": datetime.now().isoformat()
            }
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[DEDUP] 保存状态失败: {e}")

    def is_processed(self, message_id: str) -> bool:
        """
        检查消息是否已处理

        Args:
            message_id: 消息唯一 ID（通常是 md5 哈希）

        Returns:
            True 如果已处理，False 否则
        """
        return message_id in self._processed_ids

    def mark_processed(self, message_id: str):
        """
        标记消息为已处理

        Args:
            message_id: 消息唯一 ID
        """
        self._processed_ids.add(message_id)
        self._save()

    def reset(self):
        """重置所有状态"""
        self._processed_ids = set()
        self._save()
        print("[DEDUP] 状态已重置")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_processed": len(self._processed_ids),
            "storage_path": self.storage_path
        }


# 测试代码
if __name__ == "__main__":
    import tempfile
    import hashlib

    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name

    dedup = MessageDeduplicator(temp_path)

    # 测试消息 ID 计算
    def compute_id(is_group, sender, content):
        key = f"{is_group}:{sender}:{content}"
        return hashlib.md5(key.encode('utf-8')).hexdigest()

    # 测试新消息检查
    print("测试去重逻辑:")
    
    msg1_id = compute_id(True, "Mwu！", "hello")
    msg2_id = compute_id(False, "Mwu！", "world")
    msg3_id = compute_id(True, "Mwu！", "hello")  # 和 msg1 相同
    
    print(f"  消息1 (群聊, Mwu！, 'hello'): {dedup.is_processed(msg1_id)}")  # False
    print(f"  消息2 (私聊, Mwu！, 'world'): {dedup.is_processed(msg2_id)}")  # False
    
    # 标记为已处理
    dedup.mark_processed(msg1_id)
    dedup.mark_processed(msg2_id)
    
    print(f"  消息1 再次检查: {dedup.is_processed(msg1_id)}")  # True
    print(f"  消息3 (和消息1相同): {dedup.is_processed(msg3_id)}")  # True

    print("\n统计信息:")
    print(json.dumps(dedup.get_stats(), indent=2))

    # 清理
    os.unlink(temp_path)
    print("\n✅ 测试完成")
