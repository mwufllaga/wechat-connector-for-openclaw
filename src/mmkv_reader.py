#!/usr/bin/env python3
"""
MMKV 文件读取器
通过 ADB 读取 Android 模拟器中的微信 MMKV 存储文件
"""

import subprocess
import re
import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class MMKVMessage:
    """MMKV 消息结构"""
    message_svr_id: str
    msg_create_time: int
    sender: str
    content: str
    is_group: bool
    group_name: Optional[str] = None
    raw_xml: Optional[str] = None


class MMKVReader:
    """MMKV 文件读取器"""
    
    # 默认配置
    DEFAULT_ADB_HOST = "127.0.0.1"
    DEFAULT_ADB_PORT = 5555  # root 权限端口
    DEFAULT_MMKV_PATH = "/data/data/com.tencent.mm/files/mmkv/SyncMMKV_773985255"
    DEFAULT_ADB_PATH = "/Applications/MuMuPlayer.app/Contents/MacOS/MuMuEmulator.app/Contents/MacOS/tools/adb"
    
    def __init__(self, 
                 adb_host: str = None, 
                 adb_port: int = None,
                 mmkv_path: str = None,
                 adb_path: str = None):
        """
        初始化 MMKV 读取器
        
        Args:
            adb_host: ADB 主机地址
            adb_port: ADB 端口
            mmkv_path: MMKV 文件路径
            adb_path: ADB 可执行文件路径
        """
        self.adb_host = adb_host or self.DEFAULT_ADB_HOST
        self.adb_port = adb_port or self.DEFAULT_ADB_PORT
        self.mmkv_path = mmkv_path or self.DEFAULT_MMKV_PATH
        self.adb_path = adb_path or self.DEFAULT_ADB_PATH
        self.device_serial = f"{self.adb_host}:{self.adb_port}"
        
        # 缓存上次读取的文件状态
        self._last_mtime: Optional[float] = None
        self._last_size: int = 0
        
    def _run_adb_command(self, command: str) -> tuple[bool, str]:
        """
        执行 ADB 命令
        
        Args:
            command: 要执行的 shell 命令
            
        Returns:
            (success, output) 元组
        """
        full_command = f"{self.adb_path} -s {self.device_serial} shell {command}"
        try:
            result = subprocess.run(
                full_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr
        except subprocess.TimeoutExpired:
            return False, "Command timeout"
        except Exception as e:
            return False, str(e)
    
    def check_device_connected(self) -> bool:
        """检查设备是否已连接"""
        success, output = self._run_adb_command("echo 'connected'")
        return success and "connected" in output
    
    def get_file_stat(self) -> Optional[Dict[str, Any]]:
        """
        获取 MMKV 文件状态
        
        Returns:
            包含 mtime 和 size 的字典，或 None
        """
        success, output = self._run_adb_command(f"stat {self.mmkv_path}")
        if not success:
            return None
        
        try:
            stat = {}
            for line in output.split('\n'):
                if 'Size:' in line:
                    # 格式: Size: 131072	 Blocks: 256	 ...
                    parts = line.split()
                    if len(parts) >= 2:
                        stat['size'] = int(parts[1])
                elif 'Modify:' in line:
                    # 格式: Modify: 2026-02-18 20:55:49.028003312 +0800
                    # 转换为时间戳
                    import time
                    time_str = line.split(':', 1)[1].strip()
                    # 解析时间字符串
                    try:
                        from datetime import datetime
                        dt = datetime.strptime(time_str.split('.')[0], "%Y-%m-%d %H:%M:%S")
                        stat['mtime'] = int(dt.timestamp())
                    except:
                        pass
            
            if 'size' in stat and 'mtime' in stat:
                return stat
        except Exception as e:
            print(f"Parse stat error: {e}")
        return None
    
    def has_new_content(self) -> bool:
        """
        检查文件是否有新内容
        
        Returns:
            True 如果有新内容，False 否则
        """
        stat = self.get_file_stat()
        if stat is None:
            return False
        
        current_mtime = stat["mtime"]
        current_size = stat["size"]
        
        # 首次检查
        if self._last_mtime is None:
            self._last_mtime = current_mtime
            self._last_size = current_size
            return True  # 首次认为有新内容
        
        # 检查是否有变化
        has_changed = (current_mtime != self._last_mtime or 
                      current_size != self._last_size)
        
        # 更新缓存
        self._last_mtime = current_mtime
        self._last_size = current_size
        
        return has_changed
    
    def read_raw_content(self) -> Optional[bytes]:
        """
        读取 MMKV 文件的原始二进制内容
        
        Returns:
            文件内容字节，或 None
        """
        full_command = f"{self.adb_path} -s {self.device_serial} shell cat {self.mmkv_path}"
        try:
            result = subprocess.run(
                full_command,
                shell=True,
                capture_output=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout
            else:
                print(f"Error reading file: {result.stderr.decode('utf-8', errors='ignore')}")
                return None
        except Exception as e:
            print(f"Exception reading file: {e}")
            return None
    
    def read_text_content(self) -> Optional[str]:
        """
        读取 MMKV 文件的文本内容（自动处理编码）
        
        Returns:
            文件内容字符串，或 None
        """
        raw = self.read_raw_content()
        if raw is None:
            return None
        
        # 尝试多种编码
        for encoding in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
            try:
                return raw.decode(encoding, errors='ignore')
            except:
                continue
        return raw.decode('utf-8', errors='replace')
    
    def extract_pushcontent(self, content: str) -> List[Dict[str, str]]:
        """
        从内容中提取 pushcontent XML 标签
        
        Args:
            content: MMKV 文件内容
            
        Returns:
            pushcontent 列表，每个包含 content 和 nickname
        """
        results = []
        # 匹配 pushcontent 标签
        pattern = r'<pushcontent\s+content="([^"]*)"\s+nickname="([^"]*)"\s*/>'
        matches = re.findall(pattern, content)
        
        for content_text, nickname in matches:
            results.append({
                "content": content_text,
                "nickname": nickname
            })
        
        return results
    
    def extract_message_metadata(self, content: str) -> List[Dict[str, str]]:
        """
        提取消息元数据（messageSvrId 和 MsgCreateTime）
        
        Args:
            content: MMKV 文件内容
            
        Returns:
            元数据列表
        """
        results = []
        
        # 匹配 messageSvrId
        svr_id_pattern = r'"messageSvrId"\s*:\s*"(\d+)"'
        svr_ids = re.findall(svr_id_pattern, content)
        
        # 匹配 MsgCreateTime
        time_pattern = r'"MsgCreateTime"\s*:\s*"(\d+)"'
        times = re.findall(time_pattern, content)
        
        # 配对
        for i in range(min(len(svr_ids), len(times))):
            results.append({
                "message_svr_id": svr_ids[i],
                "msg_create_time": int(times[i])
            })
        
        return results
    
    def parse_messages(self, content: str) -> List[MMKVMessage]:
        """
        解析 MMKV 内容为消息列表
        
        Args:
            content: MMKV 文件内容
            
        Returns:
            MMKVMessage 列表
        """
        import hashlib
        messages = []
        
        # 提取 pushcontent
        pushcontents = self.extract_pushcontent(content)
        
        # 合并信息
        for i, pc in enumerate(pushcontents):
            # 解析发送者和内容
            nickname = pc["nickname"].strip()
            content_text = pc["content"]
            
            # 判断消息类型
            # 群聊：nickname 是 "群聊" 或 "group_with_AI"
            is_group = (nickname == "群聊" or nickname == "group_with_AI")
            
            if is_group:
                # 群聊：从 content 提取发送者
                # 格式: " 发送者 : 消息内容"
                if " : " in content_text:
                    parts = content_text.split(" : ", 1)
                    sender = parts[0].strip()
                    msg_content = parts[1].strip() if len(parts) > 1 else ""
                else:
                    sender = "未知"
                    msg_content = content_text
                group_name = None  # 可以从其他字段获取
            else:
                # 私聊：nickname 就是发送者
                sender = nickname
                # 从 content 提取实际消息内容
                if " : " in content_text:
                    parts = content_text.split(" : ", 1)
                    msg_content = parts[1].strip() if len(parts) > 1 else content_text
                else:
                    msg_content = content_text
                group_name = None
            
            # 使用内容哈希作为消息 ID（因为 metadata 和 pushcontent 数量/顺序不匹配）
            message_id = hashlib.md5(f"{nickname}:{content_text}".encode()).hexdigest()
            # 使用当前时间戳（因为无法可靠获取原始时间戳）
            import time
            message_time = int(time.time()) - (len(pushcontents) - i)  # 递减时间戳保持顺序
            
            msg = MMKVMessage(
                message_svr_id=message_id,
                msg_create_time=message_time,
                sender=sender,
                content=msg_content,
                is_group=is_group,
                group_name=group_name,
                raw_xml=f'<pushcontent content="{pc["content"]}" nickname="{pc["nickname"]}" />'
            )
            messages.append(msg)
        
        return messages
    
    def get_messages(self, only_new: bool = True) -> List[MMKVMessage]:
        """
        获取消息列表
        
        Args:
            only_new: 是否只返回新消息（基于文件变化）
            
        Returns:
            MMKVMessage 列表
        """
        if only_new and not self.has_new_content():
            return []
        
        content = self.read_text_content()
        if content is None:
            return []
        
        return self.parse_messages(content)


# 测试代码
if __name__ == "__main__":
    reader = MMKVReader()
    
    # 检查设备连接
    if not reader.check_device_connected():
        print("设备未连接，请检查 ADB 连接")
        exit(1)
    
    print("设备已连接")
    
    # 获取文件状态
    stat = reader.get_file_stat()
    if stat:
        print(f"文件大小: {stat['size']} bytes")
        print(f"修改时间: {datetime.fromtimestamp(stat['mtime'])}")
    
    # 读取并解析消息
    messages = reader.get_messages(only_new=False)
    print(f"\n解析到 {len(messages)} 条消息:\n")
    
    for msg in messages:
        print(f"[{msg.msg_create_time}] {msg.sender}: {msg.content}")
        print(f"  ID: {msg.message_svr_id}, 群聊: {msg.is_group}")
        print()
