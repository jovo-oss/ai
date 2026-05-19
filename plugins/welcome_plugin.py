"""
示例插件 - 欢迎消息
演示如何创建一个简单的插件
"""
from app.plugins.plugin_base import BasePlugin
from typing import Any, Dict, Optional

class WelcomePlugin(BasePlugin):
    """欢迎插件 - 新用户首次聊天时发送欢迎消息"""
    
    def __init__(self):
        super().__init__()
        self.metadata.name = "WelcomePlugin"
        self.metadata.version = "1.0.0"
        self.metadata.description = "新用户欢迎消息插件"
        self.metadata.author = "AI Chat System"
        self.welcomed_users = set()
    
    async def on_message_received(self, message: str, user_id: str) -> Optional[Dict[str, Any]]:
        """当收到消息时检查是否需要发送欢迎消息"""
        if user_id not in self.welcomed_users:
            self.welcomed_users.add(user_id)
            return {
                "type": "welcome",
                "message": f"欢迎使用AI聊天系统！我是您的AI助手，有什么可以帮助您的吗？",
                "user_id": user_id
            }
        return None
