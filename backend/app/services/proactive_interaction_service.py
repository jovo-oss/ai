import asyncio
from datetime import datetime
from typing import List, Dict, Any
from app.models.database import SessionLocal, GreetingSchedule, SpecialDate, CareReminder
from app.services.time_awareness_service import time_awareness_service
from app.services.weather_awareness_service import weather_awareness_service
from app.services.tts_service import tts_service


class ProactiveInteractionService:
    """主动互动服务 - 让角色主动关心用户"""
    
    # 问候语模板
    GREETING_MESSAGES = {
        "morning": [
            "早安呀~ 新的一天开始了，今天也要元气满满哦！",
            "早上好！清晨的阳光真美好，希望你今天有个好心情~",
            "早安~ 记得吃早餐哦，开启活力满满的一天！"
        ],
        "noon": [
            "中午好！该吃午饭了吧？记得好好吃饭，不要饿肚子哦~",
            "午安！忙碌了一上午，休息一下吧~",
            "中午好呀！今天过得还顺利吗？"
        ],
        "evening": [
            "晚上好！辛苦一天了，该放松一下了~",
            "傍晚好！今天过得开心吗？有什么想和我分享的吗？",
            "晚上好呀！忙碌了一天，好好休息一下吧~"
        ],
        "night": [
            "夜深了~ 早点休息吧，明天还要元气满满呢！",
            "晚安~ 今天辛苦啦，做个好梦哦~",
            "很晚了~ 如果睡不着的话，我陪你聊聊天吧~"
        ]
    }
    
    # 关怀提醒模板
    CARE_MESSAGES = {
        "water": [
            "该喝水啦~ 保持水分很重要哦！",
            "记得喝杯水休息一下~",
            "喝水时间到！身体需要补充水分啦~"
        ],
        "rest": [
            "休息一下吧~ 不要太累了哦！",
            "起来活动活动，放松一下眼睛和身体~",
            "该休息啦~ 劳逸结合效率更高哦！"
        ],
        "exercise": [
            "运动时间到！起来动一动吧~",
            "该锻炼身体啦~ 健康最重要！",
            "运动一下出出汗，心情会更好哦~"
        ],
        "eye": [
            "护眼时间！看看远处，放松一下眼睛~",
            "该让眼睛休息啦~ 看看绿色植物吧！",
            "眼睛辛苦了~ 闭眼休息一下吧~"
        ],
        "meal": [
            "该吃饭啦~ 好好享受美食吧！",
            "用餐时间到！记得好好吃饭哦~",
            "吃饭时间！吃饱饱才有力气继续加油~"
        ],
        "sleep": [
            "该睡觉啦~ 充足的睡眠很重要哦！",
            "夜深了，早点休息吧~ 晚安！",
            "睡觉时间到！做个好梦哦~"
        ]
    }
    
    # 特殊日子祝福模板
    SPECIAL_DATE_MESSAGES = {
        "birthday": [
            "生日快乐！ 祝你新的一岁更加幸福美好~",
            "今天是你的生日呢！🎉 生日快乐，愿你每天都开心~",
            "生日快乐呀！ 愿你所有的愿望都能实现~"
        ],
        "anniversary": [
            "纪念日快乐！💕 祝你们幸福长久~",
            "今天是特别的日子呢！🎊 纪念日快乐~",
            "纪念日快乐呀！✨ 愿你们的爱情越来越甜蜜~"
        ]
    }
    
    def __init__(self):
        self.is_running = False
        self.check_interval = 60  # 每60秒检查一次
    
    async def start(self):
        """启动主动互动服务"""
        if self.is_running:
            return
        
        self.is_running = True
        print("主动互动服务已启动")
        
        while self.is_running:
            try:
                await self.check_all_reminders()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                print(f"主动互动服务错误: {e}")
                await asyncio.sleep(self.check_interval)
    
    def stop(self):
        """停止主动互动服务"""
        self.is_running = False
        print("主动互动服务已停止")
    
    async def check_all_reminders(self):
        """检查所有提醒"""
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        current_month = now.month
        current_day = now.day
        
        # 1. 检查问候时间表
        await self.check_greeting_schedules(current_time)
        
        # 2. 检查特殊日子
        await self.check_special_dates(current_month, current_day)
        
        # 3. 检查习惯关怀提醒
        await self.check_care_reminders(current_time)
    
    async def check_greeting_schedules(self, current_time: str):
        """检查问候时间表"""
        try:
            db = SessionLocal()
            schedules = db.query(GreetingSchedule).filter(
                GreetingSchedule.is_enabled == True,
                GreetingSchedule.greeting_time == current_time
            ).all()
            
            for schedule in schedules:
                # 检查是否已经触发过
                if schedule.last_triggered:
                    last_triggered_minute = schedule.last_triggered.strftime("%H:%M")
                    if last_triggered_minute == current_time:
                        continue
                
                # 触发问候
                await self.trigger_greeting(schedule)
                
                # 更新最后触发时间
                schedule.last_triggered = datetime.utcnow()
                db.commit()
            
            db.close()
        except Exception as e:
            print(f"检查问候时间表失败: {e}")
    
    async def check_special_dates(self, current_month: int, current_day: int):
        """检查特殊日子"""
        try:
            db = SessionLocal()
            dates = db.query(SpecialDate).filter(
                SpecialDate.is_enabled == True,
                SpecialDate.month == current_month,
                SpecialDate.day == current_day
            ).all()
            
            for special_date in dates:
                # 检查是否已经触发过（今天）
                if special_date.last_triggered:
                    if special_date.last_triggered.date() == datetime.utcnow().date():
                        continue
                
                # 触发祝福
                await self.trigger_special_date_blessing(special_date)
                
                # 更新最后触发时间
                special_date.last_triggered = datetime.utcnow()
                db.commit()
            
            db.close()
        except Exception as e:
            print(f"检查特殊日子失败: {e}")
    
    async def check_care_reminders(self, current_time: str):
        """检查习惯关怀提醒"""
        try:
            db = SessionLocal()
            reminders = db.query(CareReminder).filter(
                CareReminder.is_enabled == True,
                CareReminder.reminder_time == current_time
            ).all()
            
            for reminder in reminders:
                # 检查是否已经触发过
                if reminder.last_triggered:
                    last_triggered_minute = reminder.last_triggered.strftime("%H:%M")
                    if last_triggered_minute == current_time:
                        continue
                
                # 触发关怀提醒
                await self.trigger_care_reminder(reminder)
                
                # 更新最后触发时间
                reminder.last_triggered = datetime.utcnow()
                db.commit()
            
            db.close()
        except Exception as e:
            print(f"检查习惯关怀提醒失败: {e}")
    
    async def trigger_greeting(self, schedule: GreetingSchedule):
        """触发问候"""
        try:
            print(f"触发问候: {schedule.greeting_type} ({schedule.greeting_time})")
            
            # 获取问候消息
            if schedule.custom_message:
                message = schedule.custom_message
            else:
                messages = self.GREETING_MESSAGES.get(schedule.greeting_type, self.GREETING_MESSAGES["morning"])
                message = messages[0]  # 简单取第一个
            
            # 添加角色名称
            if schedule.character_name:
                message = f"{schedule.character_name}：{message}"
            
            # 如果启用了TTS，生成语音
            if schedule.enable_tts:
                try:
                    audio_base64 = await tts_service.text_to_speech_base64(message)
                    print(f"已生成问候语音: {schedule.greeting_type}")
                except Exception as e:
                    print(f"生成问候语音失败: {e}")
            
            # 这里可以将消息推送给前端
            # 目前只是打印日志
            print(f"问候消息: {message}")
            
        except Exception as e:
            print(f"触发问候失败: {e}")
    
    async def trigger_special_date_blessing(self, special_date: SpecialDate):
        """触发特殊日子祝福"""
        try:
            print(f"触发特殊日子祝福: {special_date.title}")
            
            # 获取祝福消息
            if special_date.custom_message:
                message = special_date.custom_message
            else:
                messages = self.SPECIAL_DATE_MESSAGES.get(special_date.date_type, self.SPECIAL_DATE_MESSAGES["birthday"])
                message = messages[0]
            
            # 添加相关人物
            if special_date.related_person:
                message = f"今天是{special_date.related_person}的{special_date.title}！{message}"
            else:
                message = f"今天是{special_date.title}！{message}"
            
            # 添加角色名称
            if special_date.character_name:
                message = f"{special_date.character_name}：{message}"
            
            # 如果启用了TTS，生成语音
            if special_date.enable_tts:
                try:
                    audio_base64 = await tts_service.text_to_speech_base64(message)
                    print(f"已生成祝福语音: {special_date.title}")
                except Exception as e:
                    print(f"生成祝福语音失败: {e}")
            
            # 这里可以将消息推送给前端
            print(f"祝福消息: {message}")
            
        except Exception as e:
            print(f"触发特殊日子祝福失败: {e}")
    
    async def trigger_care_reminder(self, reminder: CareReminder):
        """触发关怀提醒"""
        try:
            print(f"触发关怀提醒: {reminder.care_type} ({reminder.reminder_time})")
            
            # 获取关怀消息
            if reminder.custom_message:
                message = reminder.custom_message
            else:
                messages = self.CARE_MESSAGES.get(reminder.care_type, self.CARE_MESSAGES["water"])
                message = messages[0]
            
            # 添加角色名称
            if reminder.character_name:
                message = f"{reminder.character_name}：{message}"
            
            # 如果启用了TTS，生成语音
            if reminder.enable_tts:
                try:
                    audio_base64 = await tts_service.text_to_speech_base64(message)
                    print(f"已生成关怀语音: {reminder.care_type}")
                except Exception as e:
                    print(f"生成关怀语音失败: {e}")
            
            # 这里可以将消息推送给前端
            print(f"关怀消息: {message}")
            
        except Exception as e:
            print(f"触发关怀提醒失败: {e}")


# 全局主动互动服务实例
proactive_interaction_service = ProactiveInteractionService()
