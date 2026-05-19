"""
示例插件 - 情感分析
分析用户消息的情感倾向
"""
from app.plugins.plugin_base import BasePlugin
from typing import Any, Dict, Optional

class SentimentAnalysisPlugin(BasePlugin):
    """情感分析插件 - 分析用户情绪"""
    
    def __init__(self):
        super().__init__()
        self.metadata.name = "SentimentAnalysisPlugin"
        self.metadata.version = "1.0.0"
        self.metadata.description = "分析用户消息的情感倾向"
        self.metadata.author = "AI Chat System"
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行情感分析"""
        message = context.get("message", "")
        
        # 简单的情感分析示例
        positive_words = ["开心", "高兴", "喜欢", "爱", "棒", "好", "谢谢"]
        negative_words = ["难过", "生气", "讨厌", "恨", "糟糕", "差", "失望"]
        
        sentiment = "neutral"
        for word in positive_words:
            if word in message:
                sentiment = "positive"
                break
        
        for word in negative_words:
            if word in message:
                sentiment = "negative"
                break
        
        return {
            "sentiment": sentiment,
            "message": message
        }
