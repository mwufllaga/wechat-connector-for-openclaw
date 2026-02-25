#!/usr/bin/env python3
"""
微信消息发送器 (macOS 版)
通过 AppleScript 操作 macOS 微信客户端发送消息

发送流程：
1. 激活微信
2. 找到对应聊天窗口
3. 全屏（如果未全屏）
4. 点击输入框
5. 粘贴内容（剪贴板）
6. 回车发送
7. 退出全屏（如果之前未全屏）
"""

import subprocess
import time
from typing import Optional, Dict


class WeChatSender:
    """微信消息发送器"""
    
    # 输入框坐标（全屏后固定）
    # 基于 1920x1080 分辨率，如需适配其他分辨率需调整
    # 注意：Y坐标是从屏幕顶部开始计算的，所以底部位置的Y值更大
    INPUT_BOX_X = 915
    INPUT_BOX_Y = 1050
    
    def __init__(self):
        """初始化发送器"""
        pass
    
    def _run_applescript(self, script: str) -> tuple[bool, str]:
        """
        执行 AppleScript
        
        Args:
            script: AppleScript 代码
            
        Returns:
            (success, output) 元组
        """
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr
        except Exception as e:
            return False, str(e)
    
    def _set_clipboard(self, text: str) -> bool:
        """
        设置剪贴板内容
        
        Args:
            text: 要设置的文本
            
        Returns:
            是否成功
        """
        # 使用 pbcopy 设置剪贴板
        try:
            process = subprocess.Popen(
                ["pbcopy"],
                stdin=subprocess.PIPE,
                text=True
            )
            process.communicate(input=text, timeout=5)
            return process.returncode == 0
        except Exception as e:
            print(f"[SENDER] 设置剪贴板失败: {e}")
            return False
    
    def _find_window_index(self, target: str) -> Optional[int]:
        """
        查找窗口索引
        
        Args:
            target: 目标名称
            
        Returns:
            窗口索引（1-based），未找到返回 None
        """
        script = f'''
        tell application "System Events"
            tell process "WeChat"
                set winList to every window
                set idx to 0
                repeat with i from 1 to count of winList
                    set w to item i of winList
                    try
                        set winName to name of w
                        -- 去除首尾空格后比较
                        set trimmedName to do shell script "echo " & quoted form of winName & " | sed 's/^[ ]*//;s/[ ]*$//'"
                        if trimmedName is "{target}" then
                            set idx to i
                            exit repeat
                        end if
                    end try
                end repeat
                return idx
            end tell
        end tell
        '''
        success, output = self._run_applescript(script)
        if success and output.strip():
            try:
                idx = int(output.strip())
                return idx if idx > 0 else None
            except:
                pass
        return None
    
    def send_message(self, content: str, target: str, is_group: bool = False) -> bool:
        """
        发送微信消息
        
        Args:
            content: 消息内容
            target: 目标名称（"Mwu！" 或 "group_with_AI"）
            is_group: 是否群聊（保留参数，实际通过 target 判断）
            
        Returns:
            是否成功
        """
        print(f"[SENDER] 准备发送消息到: {target}")
        print(f"[SENDER] 内容: {content[:50]}...")
        
        # 1. 设置剪贴板
        if not self._set_clipboard(content):
            print("[SENDER] 错误: 设置剪贴板失败")
            return False
        
        # 2. 构建 AppleScript - 直接用名称查找窗口，避免索引变化问题
        script = f'''
        -- 首先强制退出所有全屏状态
        tell application "System Events"
            tell process "WeChat"
                try
                    set winList to every window
                    repeat with w in winList
                        try
                            set isFullscreen to value of attribute "AXFullScreen" of w
                            if isFullscreen then
                                set value of attribute "AXFullScreen" of w to false
                                delay 0.3
                            end if
                        end try
                    end repeat
                end try
            end tell
        end tell
        
        delay 0.5
        
        tell application "WeChat"
            activate
        end tell
        
        delay 0.5
        
        set targetName to "{target}"
        set wasFullscreen to false
        
        tell application "System Events"
            tell process "WeChat"
                -- 通过名称查找窗口（去除首尾空格后比较）
                set targetWindow to missing value
                set winList to every window
                repeat with w in winList
                    try
                        set winName to name of w
                        set trimmedName to do shell script "echo " & quoted form of winName & " | sed 's/^[ ]*//;s/[ ]*$//'"
                        if trimmedName is targetName then
                            set targetWindow to w
                            exit repeat
                        end if
                    end try
                end repeat
                
                -- 检查是否找到窗口
                if targetWindow is missing value then
                    return "ERROR: 找不到窗口 " & targetName
                end if
                
                -- 将目标窗口设为 frontmost（最前面）
                -- 使用 perform action 来激活窗口
                perform action "AXRaise" of targetWindow
                delay 0.5
                
                -- 检查是否已全屏
                try
                    set wasFullscreen to value of attribute "AXFullScreen" of targetWindow
                end try
                
                -- 点击激活窗口
                click targetWindow
                delay 0.5
                
                -- 如未全屏，进入全屏
                if not wasFullscreen then
                    set value of attribute "AXFullScreen" of targetWindow to true
                    delay 1.0
                end if
                
                -- 再次点击窗口确保获得焦点
                click targetWindow
                delay 0.8
                
                -- 点击输入框 - 使用固定的屏幕坐标（全屏后固定位置）
                -- 基于 2560x1440 分辨率，输入框在屏幕底部中央
                click at {1280, 1350}
                delay 0.5
                
                -- 粘贴内容
                keystroke "v" using command down
                delay 0.5
                
                -- 发送（回车）
                key code 36
                delay 0.5
                
                -- 如之前未全屏，按 ESC 退出全屏
                if not wasFullscreen then
                    key code 53
                    delay 0.5
                end if
            end tell
        end tell
        
        return "SUCCESS"
        '''
        
        # 3. 执行脚本
        success, output = self._run_applescript(script)
        
        if success and "SUCCESS" in output:
            print(f"[SENDER] 消息发送成功")
            return True
        else:
            print(f"[SENDER] 错误: {output}")
            return False


# 便捷函数
def send_message(content: str, target: str, is_group: bool = False) -> bool:
    """
    发送微信消息（便捷函数）
    
    Args:
        content: 消息内容
        target: 目标名称（"Mwu！" 或 "group_with_AI"）
        is_group: 是否群聊
        
    Returns:
        是否成功
    """
    sender = WeChatSender()
    return sender.send_message(content, target, is_group)


if __name__ == "__main__":
    # 测试
    import sys
    
    if len(sys.argv) < 3:
        print("用法: python3 sender.py <目标> <消息内容>")
        print("示例: python3 sender.py 'group_with_AI' '测试消息'")
        sys.exit(1)
    
    target = sys.argv[1]
    content = sys.argv[2]
    
    result = send_message(content, target)
    print(f"发送结果: {'成功' if result else '失败'}")
