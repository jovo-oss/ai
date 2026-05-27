from typing import Dict, Any, Optional
from app.services.time_awareness_service import time_awareness_service
from app.services.weather_awareness_service import weather_awareness_service


class GreetingEnhancer:
    """问候语增强器 - 根据时间和天气生成个性化的角色问候"""
    
    # 角色问候模板（可以根据角色性格调整）
    GREETING_TEMPLATES = {
        "morning": [
            "早安呀~ {weather_greeting}今天也要元气满满哦！",
            "早上好！{weather_greeting}新的一天，新的开始~",
            "清晨好~ {weather_greeting}希望你今天有个好心情！"
        ],
        "noon": [
            "中午好！{weather_greeting}该吃午饭了吧？",
            "午安~ {weather_greeting}忙碌了一上午，休息一下吧~",
            "中午好呀！{weather_greeting}今天过得怎么样？"
        ],
        "afternoon": [
            "下午好！{weather_greeting}下午的时光最适合做喜欢的事情了~",
            "嗨~ 下午好！{weather_greeting}今天过得还顺利吗？",
            "下午好呀！{weather_greeting}喝杯茶休息一下吧~"
        ],
        "evening": [
            "傍晚好！{weather_greeting}辛苦一天了，该放松一下了~",
            "晚上好！{weather_greeting}今天过得开心吗？",
            "傍晚好呀！{weather_greeting}夕阳很美呢~"
        ],
        "night": [
            "晚上好！{weather_greeting}夜晚安静下来了，适合聊聊天呢~",
            "晚安前的时光~ {weather_greeting}今天有什么想和我分享的吗？",
            "晚上好呀！{weather_greeting}忙碌了一天，好好休息一下吧~"
        ],
        "late_night": [
            "这么晚还没睡呀？{weather_greeting}要注意身体哦~",
            "深夜了~ {weather_greeting}早点休息吧，明天还要元气满满呢！",
            "夜深了~ {weather_greeting}如果睡不着的话，我陪你聊聊天吧~"
        ]
    }
    
    async def generate_greeting(self, character_name: str, user_id: int = None, city: str = "北京") -> str:
        """生成个性化的问候语"""
        try:
            # 获取时间信息
            time_info = time_awareness_service.get_current_time_info()
            period = time_info["period"]
            
            # 获取天气信息
            weather_result = await weather_awareness_service.get_weather(city)
            weather_info = weather_result.get("weather") if weather_result.get("success") else None
            
            # 生成天气问候
            weather_greeting = ""
            if weather_info:
                weather_greeting = weather_awareness_service.get_weather_greeting(weather_info)
            
            # 选择问候模板
            templates = self.GREETING_TEMPLATES.get(period, self.GREETING_TEMPLATES["morning"])
            
            # 简单选择第一个模板（可以改为随机）
            template = templates[0]
            
            # 填充模板
            greeting = template.format(
                weather_greeting=weather_greeting + " " if weather_greeting else ""
            )
            
            # 添加角色名称
            if character_name:
                greeting = f"{character_name}：{greeting}"
            
            return greeting
            
        except Exception as e:
            print(f"生成问候语失败: {e}")
            # 返回默认问候语
            return f"{character_name}：你好呀~ 很高兴见到你！" if character_name else "你好呀~ 很高兴见到你！"
    
    def get_simple_greeting(self, character_name: str = None) -> str:
        """获取简单的问候语（不需要异步）"""
        time_info = time_awareness_service.get_current_time_info()
        period = time_info["period"]
        
        templates = self.GREETING_TEMPLATES.get(period, self.GREETING_TEMPLATES["morning"])
        template = templates[0]
        
        greeting = template.format(weather_greeting="")
        
        if character_name:
            greeting = f"{character_name}：{greeting}"
        
        return greeting


# 全局问候语增强器实例
greeting_enhancer = GreetingEnhancer()
