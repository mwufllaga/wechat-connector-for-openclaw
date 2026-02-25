# WeChat Connector for OpenClaw

让 AI 能够通过微信与外界沟通的桥梁（Android 通知监听版）。

## 工作原理

### 整体架构

```
接收消息：
┌─────────────┐     通知监听    ┌─────────────┐     Webhook    ┌─────────────┐
│  微信APP    │ ──────────────→ │  Listener   │ ─────────────→ │   OpenClaw  │
│ (Android)   │  cmd notification│ (Android端) │  发送消息      │   (AI助手)   │
└─────────────┘              └─────────────┘                └─────────────┘
                                                                   ↓
                                                            收到微信消息
                                                            用 Tool 回复

发送消息：
┌─────────────┐     AppleScript   ┌─────────────┐
│  OpenClaw   │ ────────────────→ │  macOS微信   │
│  (AI回复)   │   操作微信客户端   │  (桌面端)    │
└─────────────┘                 └─────────────┘
```

**说明：**
- **接收**：Android 设备运行 `wechat_listener.sh` 监听通知，推送到 OpenClaw
- **发送**：Mac 端运行 `sender.py` 通过 AppleScript 操作 macOS 微信客户端发送消息

**相比旧版的优势：**
- ✅ 无需 ADB 持续连接
- ✅ 无需读取 MMKV 文件
- ✅ 无需模拟器（支持真机）
- ✅ Android 端无需 root 权限
- ✅ 更简单稳定

## 前置条件

### 1. 硬件/环境
- **Android 设备**：真机或模拟器（MuMu、雷电等），用于接收微信消息
- **macOS 电脑**：用于运行 OpenClaw 和发送微信消息
- **微信**：
  - Android 端：登录用于接收消息
  - macOS 端：登录用于发送消息（可与 Android 同时在线）
- **网络**：Android 设备需要能访问 OpenClaw 所在机器

### 2. 网络配置

Android 设备需要能访问 OpenClaw 的 webhook 端口（默认 18789）。

**如果是模拟器：**
- 使用 `10.0.2.2` 访问宿主机（已在脚本中配置）

**如果是真机：**
- 需要修改脚本中的 `WEBHOOK_URL` 为实际 IP
- 确保手机和电脑在同一局域网

### 3. OpenClaw 配置

确保 OpenClaw 已启动，并且 webhook 端口可访问：

```bash
# 在电脑上测试
curl http://127.0.0.1:18789/hooks/wake
# 应返回 200 OK
```

检查 OpenClaw 配置 `~/.openclaw/openclaw.json`：
```json
{
  "hooks": {
    "token": "wechat-bridge-2026",
    "mappings": [
      {
        "id": "wechat-bridge",
        "match": { "path": "wake" },
        "action": "wake"
      }
    ]
  }
}
```

## 安装步骤

### 1. 克隆代码

```bash
git clone https://github.com/mwufllaga/wech--connector-for-openclaw.git
cd wech--connector-for-openclaw
```

### 2. 配置 Mac 端发送器（sender.py）

Mac 端使用 `sender.py` 通过 AppleScript 操作 macOS 微信客户端发送消息。

**前置条件：**
- macOS 微信已安装并登录
- Python 3 已安装

**配置步骤：**

1. 测试 sender.py：
```bash
# 测试发送消息到私聊
python3 src/sender.py 'Mwu！' '测试消息'

# 测试发送消息到群聊
python3 src/sender.py 'group_with_AI' '群聊测试'
```

2. 在 OpenClaw 中配置 `send_wechat_message` tool：
   - 将 `src/sender.py` 注册为 OpenClaw 的 tool
   - 确保 AI 可以通过 tool 调用发送消息

**注意：**
- 发送消息时 macOS 微信窗口必须在屏幕上可见
- 窗口名称必须与脚本中的 target 参数完全一致

### 3. 推送脚本到 Android 设备

**如果是模拟器（MuMu/雷电）：**
```bash
# 连接模拟器（MuMu 默认端口 5555）
adb connect 127.0.0.1:5555

# 推送脚本
adb push wechat_listener.sh /data/local/tmp/

# 赋予执行权限
adb shell chmod +x /data/local/tmp/wechat_listener.sh
```

**如果是真机：**
```bash
# 通过 USB 连接手机，开启 USB 调试
adb devices
# 应显示设备列表

# 推送脚本
adb push wechat_listener.sh /data/local/tmp/
adb shell chmod +x /data/local/tmp/wechat_listener.sh
```

### 4. 配置修改（可选）

编辑 `wechat_listener.sh`，根据你的环境修改：

```bash
# 如果是真机，需要修改 webhook URL 为电脑的实际 IP
WEBHOOK_URL="http://192.168.1.xxx:18789/hooks/wake"  # 改成你的电脑 IP

# 如果修改了 OpenClaw 的 token，也需要同步修改
AUTH_TOKEN="wechat-bridge-2026"
```

**修改群聊名称（如果需要）：**
```bash
# 默认群聊名称是 "group_with_AI"
# 修改第 75 行：
chat_name="group_with_AI"  # 改成你的实际群名称
```

## 使用方法

### 启动 Android 端监听

```bash
# 进入 Android shell
adb shell

# 运行脚本
cd /data/local/tmp
./wechat_listener.sh
```

看到以下输出表示成功：
```
[2026-02-25 23:00:00] 微信通知监听器启动...
```

### 后台运行

```bash
# 在 Android shell 中
nohup ./wechat_listener.sh > /data/local/tmp/wechat_listener.log 2>&1 &

# 查看日志
tail -f /data/local/tmp/wechat_listener.log
```

### 停止监听

```bash
# 查找进程
ps | grep wechat_listener

# 结束进程
kill <PID>
```

## 消息格式

脚本发送到 OpenClaw 的消息格式：
```
[系统消息-微信转发，需要使用send_wechat_message(target='Mwu！')回复] 
来源：Mwu！ | 发送者：Mwu！ | 内容：消息内容
```

示例：
- 私聊：`[系统消息-微信转发，需要使用send_wechat_message(target='Mwu！')回复] 来源：Mwu！ | 发送者：Mwu！ | 内容：在吗`
- 群聊：`[系统消息-微信转发，需要使用send_wechat_message(target='group_with_AI')回复] 来源：group_with_AI | 发送者：Mwu！ | 内容：大家好`

## AI 回复规则（关键）

AI 收到微信消息后，**必须使用 `send_wechat_message` Tool 回复**：

```python
# 私聊回复（target 为对方昵称）
send_wechat_message(target="Mwu！", content="回复内容")

# 群聊回复（target 必须与群名称一致）
send_wechat_message(target="group_with_AI", content="回复内容")
```

**重要识别规则：**
- 以 `[系统消息-微信转发` 开头的消息需要用 Tool 回复到微信
- AI 会自动识别消息来源，私聊从私聊返回，群聊从群聊返回

## 故障排查

### 脚本无法运行
```
/system/bin/sh: ./wechat_listener.sh: not found
```
- 检查文件是否推送成功：`adb shell ls -la /data/local/tmp/wechat_listener.sh`
- 检查执行权限：`adb shell chmod +x /data/local/tmp/wechat_listener.sh`

### 没有新消息
- 检查微信是否有通知权限（设置 → 通知管理 → 微信 → 允许通知）
- 检查微信是否在后台运行（锁定后台，避免被系统清理）
- 查看日志：`tail -f /data/local/tmp/wechat_notifications.log`

### Webhook 发送失败
```
[FAIL] 发送失败 (HTTP 000)
```
- 检查 OpenClaw 是否运行
- 检查网络连接（模拟器用 10.0.2.2，真机用实际 IP）
- 检查防火墙/路由器是否阻挡端口 18789

### 消息发送失败
- 检查 macOS 微信是否已登录且窗口可见
- 检查 `src/sender.py` 是否能正常运行：`python3 src/sender.py 'Mwu！' '测试消息'`
- 检查 target 名称是否与微信聊天窗口名称完全一致（包括空格、标点）

## 文件说明

| 文件 | 说明 |
|------|------|
| `wechat_listener.sh` | Android 端脚本，监听通知并发送 webhook 到 OpenClaw |
| `src/sender.py` | Mac 端脚本，通过 AppleScript 操作 macOS 微信发送消息 |
| `README.md` | 本文档 |

## 注意事项

1. **双端登录**：
   - Android 端微信用于接收消息（通过通知监听）
   - macOS 端微信用于发送消息（通过 AppleScript 操作）
   - 两个客户端可以同时登录同一账号

2. **通知权限**：Android 微信必须有通知权限，否则无法监听到消息

3. **后台运行**：Android 微信需要在后台保持运行，建议锁定后台

4. **电池优化**：建议关闭 Android 微信的电池优化，避免被系统清理

5. **网络**：确保 Android 设备能访问 OpenClaw 所在机器的 18789 端口

6. **去重**：相同内容的消息不会重复处理，如需测试请发送不同内容

7. **Mac 微信窗口**：发送消息时 macOS 微信窗口必须在屏幕上可见，不能最小化

## 版本历史

### 2.0 (2026-02-25)
- 全新架构：基于 Android 通知监听
- 移除 ADB 持续连接、MMKV 读取依赖
- 支持真机和模拟器
- 更简单的部署流程

### 1.0 (2026-02-19)
- 基础消息收发功能
- 基于 ADB + MMKV 读取
- 仅支持模拟器

## License

MIT
