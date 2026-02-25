# WeChat Listener for OpenClaw

让 AI 能够通过微信与外界沟通的桥梁（Android 通知监听版）。

## 工作原理

```
┌─────────────┐     通知监听    ┌─────────────┐     Webhook    ┌─────────────┐
│  微信APP    │ ──────────────→ │  Listener   │ ─────────────→ │   OpenClaw  │
│ (Android)   │  cmd notification│  (本脚本)    │  发送消息      │   (AI助手)   │
└─────────────┘              └─────────────┘                └─────────────┘
                                                                   ↓
                                                            收到微信消息
                                                            用 Tool 回复
```

**相比旧版的优势：**
- ✅ 无需 ADB 连接
- ✅ 无需读取 MMKV 文件
- ✅ 无需模拟器
- ✅ 无需 root 权限（普通 shell 即可）
- ✅ 支持真机和模拟器
- ✅ 更简单稳定

## 前置条件

### 1. 硬件/环境
- **Android 设备**：真机或模拟器（MuMu、雷电等）
- **微信**：安装并登录
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

### 2. 推送脚本到 Android 设备

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

### 3. 配置修改（可选）

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

### 启动监听

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
- 检查 `send_wechat_message` tool 是否正确配置
- 检查 target 名称是否与消息来源一致

## 文件说明

| 文件 | 说明 |
|------|------|
| `wechat_listener.sh` | 主脚本，监听通知并发送 webhook |
| `README.md` | 本文档 |

## 注意事项

1. **通知权限**：微信必须有通知权限，否则无法监听到消息
2. **后台运行**：微信需要在后台保持运行，建议锁定后台
3. **电池优化**：建议关闭微信的电池优化，避免被系统清理
4. **网络**：确保 Android 设备能访问 OpenClaw 所在机器的 18789 端口
5. **去重**：相同内容的消息不会重复处理，如需测试请发送不同内容

## 版本历史

### 2.0 (2026-02-25)
- 全新架构：基于 Android 通知监听
- 移除 ADB、MMKV、模拟器依赖
- 支持真机和模拟器
- 更简单的部署流程

### 1.0 (2026-02-19)
- 基础消息收发功能
- 基于 ADB + MMKV 读取
- 仅支持模拟器

## License

MIT
