# WeChat Connector 1.0

让 AI 能够通过微信与外界沟通的桥梁。

## 工作原理

```
┌─────────────┐     ADB      ┌─────────────┐     Webhook    ┌─────────────┐
│  微信APP    │ ────────────→ │  Connector  │ ─────────────→ │   OpenClaw  │
│ (Android)   │  读取MMKV    │  (本工具)    │  发送消息      │   (AI助手)   │
└─────────────┘              └─────────────┘                └─────────────┘
                                                                  ↓
                                                           收到微信消息
                                                           用 Tool 回复
```

## 前置条件

### 1. 硬件/环境
- **macOS**（当前仅支持 Mac，Linux/Windows 需自行适配 ADB 路径）
- **Android 模拟器**：MuMuPlayer Pro（网易 MuMu）
- **微信**：安装并登录在模拟器中

### 2. 模拟器配置

#### 2.1 开启 ADB 调试
1. 打开 MuMuPlayer Pro
2. 进入 设置 → 关于 → 连续点击版本号 7 次开启开发者模式
3. 返回设置 → 开发者选项 → 开启 USB 调试

#### 2.2 获取 root 权限
```bash
# MuMu 默认端口是 5555，需要 root 权限才能读取微信数据
adb connect 127.0.0.1:5555
adb -s 127.0.0.1:5555 shell
# 在 shell 中执行 su 获取 root
```

#### 2.3 确认 MMKV 文件路径
```bash
adb shell su -c "ls -la /data/data/com.tencent.mm/files/mmkv/"
# 找到类似 SyncMMKV_xxxxxxxx 的文件，记录完整路径
```

### 3. OpenClaw 配置

确保 OpenClaw 已启动，并且 webhook 端口可访问：
```bash
curl http://127.0.0.1:18789/hooks/wake
# 应返回 200 OK
```

## 安装步骤

### 1. 克隆/放置代码
```bash
cd ~/.openclaw/workspace
git clone <repo-url> weChat-connector
cd weChat-connector
```

### 2. 配置 ADB 路径（如需要）
编辑 `src/mmkv_reader.py`，修改 `DEFAULT_ADB_PATH`：
```python
DEFAULT_ADB_PATH = "/Applications/MuMuPlayer.app/Contents/MacOS/MuMuEmulator.app/Contents/MacOS/tools/adb"
```

### 3. 配置 MMKV 路径（如需要）
编辑 `src/mmkv_reader.py`，修改 `DEFAULT_MMKV_PATH`：
```python
DEFAULT_MMKV_PATH = "/data/data/com.tencent.mm/files/mmkv/SyncMMKV_773985255"
# 注意：数字部分每个人不同，请按实际修改
```

### 4. 配置 Webhook Token（如需要）
编辑 `src/connector.py`，修改 `Authorization`：
```python
headers={
    'Content-Type': 'application/json',
    'Authorization': 'Bearer wechat-bridge-2026'  # 与 OpenClaw 配置一致
}
```

## 使用方法

### 启动 Connector
```bash
cd ~/.openclaw/workspace/weChat-connector
python3 start_connector.py
```

看到以下输出表示成功：
```
==================================================
WeChat Connector 初始化完成
数据目录: /Users/xxx/.openclaw/workspace/weChat-connector/data
轮询间隔: 1.0 秒
==================================================

开始轮询监听消息...
按 Ctrl+C 停止
```

### 后台运行
```bash
nohup python3 start_connector.py > logs/connector.log 2>&1 &
```

### 检查状态
```bash
python3 -c "from src.connector import WeChatConnector; c = WeChatConnector(); print(c.get_status())"
```

## 消息格式

Connector 发送到 OpenClaw 的消息格式：
```
[微信消息] [对话名称] [发送者] 消息内容
```

示例：
- 群聊：`[微信消息] [group_with_AI] [Mwu！] 大家好`
- 私聊：`[微信消息] [Mwu！] [Mwu！] 在吗`

## AI 回复规则

AI 收到微信消息后，必须使用 `send_wechat_message` Tool 回复：

```python
# 群聊回复
send_wechat_message(target="group_with_AI", content="回复内容")

# 私聊回复
send_wechat_message(target="Mwu！", content="回复内容")
```

**重要**：AI 必须识别消息来源，只有以 `[微信消息]` 开头的消息才需要用 Tool 回复到微信。

## 目录结构

```
weChat-connector/
├── start_connector.py      # 启动入口
├── src/
│   ├── connector.py        # 主连接器逻辑
│   ├── mmkv_reader.py      # MMKV 文件读取
│   └── message_dedup.py    # 消息去重
├── data/                   # 数据目录（自动创建）
│   └── dedup_state.json    # 去重状态
└── logs/                   # 日志目录
```

## 故障排查

### 设备未连接
```
错误: 设备未连接，请检查 ADB 连接
```
- 检查模拟器是否运行
- 检查 ADB 端口是否正确（默认 5555）
- 执行 `adb connect 127.0.0.1:5555`

### 没有新消息
- 检查 MMKV 文件路径是否正确
- 检查微信是否收到新消息（通知栏是否有提示）
- 检查去重状态是否需要重置（删除 `data/dedup_state.json`）

### Webhook 发送失败
- 检查 OpenClaw 是否运行
- 检查端口 18789 是否可访问
- 检查 Authorization Token 是否匹配

## 注意事项

1. **隐私**：此工具会读取微信消息，请确保在受信任的环境中使用
2. **稳定性**：MMKV 文件可能会被微信清理，如遇问题尝试重启微信
3. **去重**：相同内容的消息不会重复处理，如需测试请发送不同内容
4. **权限**：需要 root 权限读取微信数据，模拟器必须已 root

## 版本历史

### 1.0 (2026-02-19)
- 基础消息收发功能
- 支持群聊和私聊
- 消息去重
- 通过 Webhook 与 OpenClaw 通信

## License

MIT
