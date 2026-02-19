# WeChat Connector for OpenClaw

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

## 前置条件（必须全部完成）

### 1. 硬件/环境
- **macOS**（当前仅支持 Mac，Linux/Windows 需自行适配 ADB 路径）
- **Android 模拟器**：MuMuPlayer Pro（网易 MuMu）
- **微信**：安装并登录在模拟器中

### 2. 模拟器配置（关键步骤）

#### 2.1 开启 ADB 调试
1. 打开 MuMu模拟器（推荐配置：OPPO Find N3 模拟）
2. 设置 → 关于手机 → 连续点击版本号 7 次开启开发者模式
3. 设置 → 系统 → 开发者选项 → 开启 **USB 调试**
4. 设置 → 其他设置 → 开启 **Root 权限**

#### 2.2 确认 ADB 连接
```bash
# 连接模拟器（MuMu 默认端口 5555）
adb connect 127.0.0.1:5555

# 验证连接
adb devices
# 应显示: 127.0.0.1:5555 device
```

#### 2.3 确认 MMKV 文件路径
```bash
# 进入模拟器 shell 并获取 root
adb -s 127.0.0.1:5555 shell
su

# 查看 MMKV 文件列表
ls -la /data/data/com.tencent.mm/files/mmkv/

# 找到类似 SyncMMKV_xxxxxxxx 的文件，记录完整路径
# 例如: /data/data/com.tencent.mm/files/mmkv/SyncMMKV_773985255
# 每个人的数字不同，必须按实际修改
```

#### 2.4 微信登录状态
- 模拟器中的微信必须**已登录**
- 建议先测试发送一条消息，确保微信正常工作
- 保持微信在前台或允许后台运行

### 3. OpenClaw 配置

确保 OpenClaw 已启动，并且 webhook 端口可访问：
```bash
curl http://127.0.0.1:18789/hooks/wake
# 应返回 200 OK
```

## 安装步骤

### 1. 克隆代码到指定位置

**必须放在此路径**，因为代码中有写死的路径：
```bash
cd ~/.openclaw/workspace
git clone https://github.com/mwufllaga/wech--connector-for-openclaw.git weChat-connector
cd weChat-connector
```

目录结构：
```
~/.openclaw/workspace/weChat-connector/
├── start_connector.py      # 启动入口
├── src/
│   ├── connector.py        # 主连接器逻辑
│   ├── mmkv_reader.py      # MMKV 文件读取（含写死路径）
│   ├── sender.py           # 消息发送逻辑（含写死群名称）
│   └── message_dedup.py    # 消息去重
├── data/                   # 数据目录（自动创建）
└── logs/                   # 日志目录
```

### 2. 配置 ADB 路径

编辑 `src/mmkv_reader.py`，确认或修改 `DEFAULT_ADB_PATH`：
```python
# 第 12 行
DEFAULT_ADB_PATH = "/Applications/MuMuPlayer.app/Contents/MacOS/MuMuEmulator.app/Contents/MacOS/tools/adb"
```

如果你的 MuMu 安装路径不同，必须修改此路径。

### 3. 配置 MMKV 文件路径（必须修改）

编辑 `src/mmkv_reader.py`，修改 `DEFAULT_MMKV_PATH`：
```python
# 第 13 行
DEFAULT_MMKV_PATH = "/data/data/com.tencent.mm/files/mmkv/SyncMMKV_773985255"
#                              ↑↑↑↑↑↑↑↑
# 注意：数字部分每个人不同，请按 2.3 步骤获取的实际路径修改
```

### 4. 配置 Webhook Token

编辑 `src/connector.py`，确认 `Authorization` 与 OpenClaw 配置一致：
```python
# 第 45-48 行
headers={
    'Content-Type': 'application/json',
    'Authorization': 'Bearer wechat-bridge-2026'  # 必须与 OpenClaw hooks.token 一致
}
```

检查 OpenClaw 配置 `~/.openclaw/openclaw.json`：
```json
{
  "hooks": {
    "token": "wechat-bridge-2026",
    "mappings": [
      {
        "id": "wechat-bridge",
        "match": { "path": "wechat" },
        "action": "wake"
      }
    ]
  }
}
```

### 5. 配置群名称（必须修改）

编辑 `src/sender.py`，修改默认群名称：
```python
# 第 15 行
DEFAULT_GROUP_NAME = "group_with_AI"  # 修改为你的实际群名称
```

**重要**：代码中写死了群名称，如果你要用于其他群，必须修改此处。

### 6. 安装 Python 依赖

```bash
cd ~/.openclaw/workspace/weChat-connector
pip install -r requirements.txt
```

依赖列表：
- requests
- pyautogui（用于发送消息时的 GUI 操作）

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
cd ~/.openclaw/workspace/weChat-connector
nohup python3 start_connector.py > logs/connector.log 2>&1 &
```

### 检查运行状态

```bash
# 查看进程
ps aux | grep start_connector | grep -v grep

# 查看日志
tail -f logs/connector.log
```

## 消息格式

Connector 发送到 OpenClaw 的消息格式：
```
[微信消息] [对话名称] [发送者] 消息内容
```

示例：
- 群聊：`[微信消息] [group_with_AI] [Mwu！] 大家好`
- 私聊：`[微信消息] [Mwu！] [Mwu！] 在吗`

## AI 回复规则（关键）

AI 收到微信消息后，**必须使用 `send_wechat_message` Tool 回复**：

```python
# 群聊回复（target 必须与群名称一致）
send_wechat_message(target="group_with_AI", content="回复内容")

# 私聊回复（target 为对方昵称）
send_wechat_message(target="Mwu！", content="回复内容")
```

**重要识别规则**：
- 只有以 `[微信消息]` 开头的消息才需要用 Tool 回复到微信
- 普通 OpenClaw 对话直接在当前 session 回复即可
- AI 必须识别消息来源，私聊从私聊返回，群聊从群聊返回

## 文件路径汇总

| 文件 | 路径 | 说明 |
|------|------|------|
| 启动脚本 | `~/.openclaw/workspace/weChat-connector/start_connector.py` | 主入口 |
| 核心逻辑 | `~/.openclaw/workspace/weChat-connector/src/connector.py` | Webhook 发送 |
| MMKV 读取 | `~/.openclaw/workspace/weChat-connector/src/mmkv_reader.py` | 含 ADB 和 MMKV 路径 |
| 消息发送 | `~/.openclaw/workspace/weChat-connector/src/sender.py` | 含群名称配置 |
| 去重逻辑 | `~/.openclaw/workspace/weChat-connector/src/message_dedup.py` | 无需修改 |
| 数据目录 | `~/.openclaw/workspace/weChat-connector/data/` | 自动创建 |
| 日志目录 | `~/.openclaw/workspace/weChat-connector/logs/` | 自动创建 |

## 必须修改的配置项

1. **MMKV 路径** (`src/mmkv_reader.py:13`)
2. **群名称** (`src/sender.py:15`)
3. **ADB 路径** (`src/mmkv_reader.py:12`，如 MuMu 路径不同）
4. **Webhook Token** (`src/connector.py:48`，如与 OpenClaw 配置不同）

## 故障排查

### 设备未连接
```
错误: 设备未连接，请检查 ADB 连接
```
- 检查模拟器是否运行
- 检查 ADB 端口是否正确（默认 5555）
- 执行 `adb connect 127.0.0.1:5555`

### 没有新消息
- 检查 MMKV 文件路径是否正确（必须按实际修改）
- 检查微信是否收到新消息（通知栏是否有提示）
- 检查去重状态是否需要重置（删除 `data/dedup_state.json`）

### Webhook 发送失败
- 检查 OpenClaw 是否运行
- 检查端口 18789 是否可访问
- 检查 Authorization Token 是否匹配

### 消息发送失败
- 检查模拟器窗口是否可见（不能最小化）
- 检查群名称是否正确（必须与微信中的完全一致）
- 检查微信是否在前台

## 注意事项

1. **窗口必须可见**：发送消息时需要模拟点击，微信窗口必须在屏幕上可见，不能最小化
2. **隐私**：此工具会读取微信消息，请确保在受信任的环境中使用
3. **稳定性**：MMKV 文件可能会被微信清理，如遇问题尝试重启微信
4. **去重**：相同内容的消息不会重复处理，如需测试请发送不同内容
5. **权限**：需要 root 权限读取微信数据，模拟器必须已 root

## 版本历史

### 1.0 (2026-02-19)
- 基础消息收发功能
- 支持群聊和私聊
- 消息去重
- 通过 Webhook 与 OpenClaw 通信

## License

MIT
