from datetime import datetime
from typing import Dict, Any


class TimeAwarenessService:
    """时间感知服务 - 让角色知道当前时间并生成合适的问候"""
    
    # 时段定义
    TIME_PERIODS = {
        "early_morning": {"start": 5, "end": 7, "name": "清晨"},
        "morning": {"start": 7, "end": 11, "name": "上午"},
        "noon": {"start": 11, "end": 13, "name": "中午"},
        "afternoon": {"start": 13, "end": 17, "name": "下午"},
        "evening": {"start": 17, "end": 19, "name": "傍晚"},
        "night": {"start": 19, "end": 23, "name": "夜晚"},
        "late_night": {"start": 23, "end": 5, "name": "深夜"}
    }
    
    # 问候语模板
    GREETINGS = {
        "early_morning": [
            "早安呀~ 这么早就起来了，真是个勤奋的孩子呢！",
            "清晨好！新的一天开始了，今天也要加油哦~",
            "早上好呀！清晨的空气最清新了，深呼吸一下吧~"
        ],
        "morning": [
            "上午好！今天过得怎么样呀？",
            "嗨~ 上午好！有什么我可以帮你的吗？",
            "上午好呀！希望你今天心情愉快~"
        ],
        "noon": [
            "中午好！该吃午饭了吧？记得好好吃饭哦~",
            "午安！忙碌了一上午，休息一下吧~",
            "中午好呀！今天过得还顺利吗？"
        ],
        "afternoon": [
            "下午好！下午的时光最适合做喜欢的事情了~",
            "嗨~ 下午好！今天过得怎么样？",
            "下午好呀！喝杯茶休息一下吧~"
        ],
        "evening": [
            "傍晚好！辛苦一天了，该放松一下了~",
            "晚上好！今天过得开心吗？",
            "傍晚好呀！夕阳很美呢，你今天过得怎么样？"
        ],
        "night": [
            "晚上好！夜晚安静下来了，适合聊聊天呢~",
            "晚安前的时光~ 今天有什么想和我分享的吗？",
            "晚上好呀！忙碌了一天，好好休息一下吧~"
        ],
        "late_night": [
            "这么晚还没睡呀？要注意身体哦~",
            "深夜了，早点休息吧，明天还要元气满满呢！",
            "夜深了~ 如果睡不着的话，我陪你聊聊天吧~"
        ]
    }
    
    # 关怀提示
    CARE_TIPS = {
        "early_morning": "清晨记得喝杯温水，唤醒身体哦~",
        "morning": "上午是工作效率最高的时候，加油！",
        "noon": "午饭时间到了，记得好好吃饭，不要饿肚子哦~",
        "afternoon": "下午容易犯困，起来活动一下吧~",
        "evening": "傍晚了，今天辛苦啦，好好放松一下吧~",
        "night": "夜晚了，别太晚睡哦，充足的睡眠很重要~",
        "late_night": "已经很晚了，早点休息吧，身体最重要~"
    }
    
    def get_current_time_info(self) -> Dict[str, Any]:
        """获取当前时间信息"""
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        
        # 判断时段
        period = self._get_time_period(hour)
        
        return {
            "hour": hour,
            "minute": minute,
            "time_str": now.strftime("%H:%M"),
            "date_str": now.strftime("%Y年%m月%d日"),
            "weekday": now.weekday(),
            "weekday_name": self._get_weekday_name(now.weekday()),
            "period": period,
            "period_name": self.TIME_PERIODS[period]["name"]
        }
    
    def _get_time_period(self, hour: int) -> str:
        """根据小时判断时段"""
        for period, info in self.TIME_PERIODS.items():
            if period == "late_night":
                # 深夜跨天处理
                if hour >= info["start"] or hour < info["end"]:
                    return period
            else:
                if info["start"] <= hour < info["end"]:
                    return period
        return "morning"  # 默认
    
    def _get_weekday_name(self, weekday: int) -> str:
        """获取星期名称"""
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        return weekdays[weekday]
    
    def get_greeting(self, character_name: str = None) -> str:
        """获取当前时段的问候语"""
        now = datetime.now()
        hour = now.hour
        period = self._get_time_period(hour)
        
        greetings = self.GREETINGS.get(period, self.GREETINGS["morning"])
        
        # 随机选择一个问候语（这里简单取第一个，可以改为随机）
        greeting = greetings[0]
        
        if character_name:
            greeting = f"{character_name}：{greeting}"
        
        return greeting
    
    def get_care_tip(self) -> str:
        """获取当前时段的关怀提示"""
        now = datetime.now()
        hour = now.hour
        period = self._get_time_period(hour)
        
        return self.CARE_TIPS.get(period, "记得照顾好自己哦~")
    
    def is_sleep_time(self) -> bool:
        """判断是否是睡觉时间"""
        hour = datetime.now().hour
        return hour >= 23 or hour < 6
    
    def is_meal_time(self) -> str:
        """判断是否是用餐时间"""
        hour = datetime.now().hour
        if 7 <= hour < 9:
            return "breakfast"  # 早餐时间
        elif 11 <= hour < 13:
            return "lunch"  # 午餐时间
        elif 17 <= hour < 19:
            return "dinner"  # 晚餐时间
        return None


# 全局时间感知服务实例
time_awareness_service = TimeAwarenessService()
