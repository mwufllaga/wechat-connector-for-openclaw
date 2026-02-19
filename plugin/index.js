const { execSync } = require('child_process');

export default function (api) {
  api.registerTool({
    name: "send_wechat_message",
    description: "发送微信消息到指定对话",
    parameters: {
      type: "object",
      properties: {
        target: {
          type: "string",
          enum: ["Mwu！", "group_with_AI"],
          description: "发送目标：Mwu！（私聊）或 group_with_AI（群聊）"
        },
        content: {
          type: "string",
          description: "消息内容"
        }
      },
      required: ["target", "content"]
    },
    async execute(_id, params) {
      const { target, content } = params;
      
      try {
        const workspace = process.env.HOME + '/.openclaw/workspace';
        const isGroup = target === "group_with_AI";
        
        // 使用临时文件传递参数
        const fs = require('fs');
        const tmpFile = `/tmp/wechat_msg_${Date.now()}.json`;
        fs.writeFileSync(tmpFile, JSON.stringify({ target, content, isGroup }));
        
        const script = `
import sys
import json
sys.path.insert(0, '${workspace}/weChat-connector')
from src.sender import WeChatSender
with open('${tmpFile}') as f:
    data = json.load(f)
sender = WeChatSender()
result = sender.send_message(data['content'], data['target'], data['isGroup'])
print('SUCCESS' if result else 'FAILED')
`;
        
        const result = execSync(`cd ${workspace}/weChat-connector && python3 -c "${script}"`, {
          encoding: 'utf8',
          timeout: 30000
        });
        
        // 清理临时文件
        try { fs.unlinkSync(tmpFile); } catch (e) {}
        
        return {
          content: [{
            type: "text",
            text: result.includes("SUCCESS") ? "消息已发送" : "发送失败"
          }]
        };
      } catch (error) {
        return {
          content: [{
            type: "text",
            text: `发送失败: ${error.message}`
          }],
          isError: true
        };
      }
    }
  });
}
