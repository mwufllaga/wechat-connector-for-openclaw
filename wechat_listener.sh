#!/system/bin/sh

# 微信通知监听脚本 - 直接推送到 OpenClaw
# 使用方法: ./wechat_listener.sh
# 日志位置: /data/local/tmp/wechat_notifications.log

LOG_FILE="/data/local/tmp/wechat_notifications.log"
WEBHOOK_URL="http://10.0.2.2:18789/hooks/wake"
AUTH_TOKEN="wechat-bridge-2026"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 微信通知监听器启动..." | tee -a "$LOG_FILE"

# 记录上一次处理的通知内容，用于检测变化
last_content=""

while true; do
    # 获取当前所有通知
    notifications=$(cmd notification list 2>/dev/null)
    
    # 检查是否有微信通知
    if echo "$notifications" | grep -q "com.tencent.mm"; then
        # 提取微信通知的 key
        mm_keys=$(echo "$notifications" | grep "com.tencent.mm")
        
        # 处理每个微信通知（只处理第一条）
        key=$(echo "$mm_keys" | head -1)
        
        if [ -n "$key" ]; then
            # 获取通知详情
            details=$(cmd notification get "$key" 2>/dev/null)
            
            # 提取标题和内容
            title=$(echo "$details" | grep "android.title=String" | sed 's/.*android.title=String (\(.*\)).*/\1/')
            text=$(echo "$details" | grep "android.text=String" | sed 's/.*android.text=String (\(.*\)).*/\1/')
            ticker=$(echo "$details" | grep "tickerText=" | head -1 | sed 's/.*tickerText= //')
            
            # 去除 title 的前后空格
            title=$(echo "$title" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            
            # 如果提取失败，尝试从 tickerText 获取
            if [ -z "$title" ] && [ -n "$ticker" ]; then
                title=$(echo "$ticker" | cut -d':' -f1)
                text=$(echo "$ticker" | cut -d':' -f2- | sed 's/^ //')
            fi
            
            # 跳过空消息
            if [ -z "$title" ]; then
                sleep 1
                continue
            fi
            
            if [ -z "$text" ]; then
                text="[图片/语音/其他]"
            fi
            
            # 判断是群聊还是私聊
            is_group=0
            chat_name="Mwu！"
            sender="$title"
            message_content="$text"
            
            # 处理 [x条] 前缀（未读消息数）
            clean_text="$text"
            if echo "$text" | grep -qE '^\[[0-9]+条\] '; then
                clean_text=$(echo "$text" | sed 's/^\[[0-9]*条\] //')
            fi
            
            # 检查 clean_text 是否包含 ": "（发送者: 内容 格式）
            if echo "$clean_text" | grep -q ': '; then
                # 提取 text 中的发送者
                text_sender=$(echo "$clean_text" | sed 's/^\([^:]*\): .*/\1/')
                text_content=$(echo "$clean_text" | sed 's/^[^:]*: //')
                
                # 判断：如果 title == text_sender，是私聊；否则是群聊
                if [ "$title" = "$text_sender" ]; then
                    # 私聊
                    is_group=0
                    chat_name="Mwu！"
                    sender="$title"
                    message_content="$text_content"
                else
                    # 群聊
                    is_group=1
                    chat_name="group_with_AI"
                    sender="$text_sender"
                    message_content="$text_content"
                fi
            else
                # 没有 ": " 格式，直接显示 clean_text
                message_content="$clean_text"
            fi
            
            # 构造完整内容标识
            current_content="$chat_name|$sender|$message_content"
            
            # 检测内容是否变化
            if [ "$current_content" = "$last_content" ]; then
                sleep 1
                continue
            fi
            
            # 更新上一次处理的内容
            last_content="$current_content"
            
            # 记录到本地日志
            timestamp=$(date '+%Y-%m-%d %H:%M:%S')
            echo "[$timestamp] [$chat_name] $sender: $message_content" | tee -a "$LOG_FILE"
            
            # 构造消息文本
            # 添加说明：这是系统消息渠道转发的微信消息，需要用 send_wechat_message 工具回复
            if [ "$chat_name" = "Mwu！" ]; then
                reply_target="Mwu！"
            else
                reply_target="group_with_AI"
            fi
            message_text="[系统消息-微信转发，需要使用send_wechat_message(target='$reply_target')回复] 来源：$chat_name | 发送者：$sender | 内容：$message_content"
            
            # 简单的 JSON 转义（只处理双引号）
            escaped_text=$(echo "$message_text" | sed 's/"/\\"/g')
            
            # 推送到 OpenClaw webhook
            json_payload="{\"text\":\"$escaped_text\",\"mode\":\"now\"}"
            
            response=$(curl -s -X POST "$WEBHOOK_URL" \
                -H "Content-Type: application/json" \
                -H "Authorization: Bearer $AUTH_TOKEN" \
                -d "$json_payload" \
                -w "\nHTTP_CODE:%{http_code}" \
                --connect-timeout 5 \
                --max-time 10 2>/dev/null)
            
            http_code=$(echo "$response" | grep "HTTP_CODE:" | sed 's/HTTP_CODE://')
            
            if [ "$http_code" = "200" ]; then
                echo "  [OK] 已发送到 OpenClaw" | tee -a "$LOG_FILE"
            else
                echo "  [FAIL] 发送失败 (HTTP $http_code)" | tee -a "$LOG_FILE"
            fi
        fi
    fi
    
    # 每 1 秒检查一次
    sleep 1
done
