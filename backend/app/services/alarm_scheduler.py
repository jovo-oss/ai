import asyncio
from datetime import datetime
from typing import List
from app.services.alarm_reminder_service import alarm_reminder_service
from app.services.tts_service import tts_service
from app.models.database import AlarmReminder


class AlarmScheduler:
    """闹钟调度器 - 定时检查并触发闹钟提醒"""
    
    def __init__(self):
        self.is_running = False
        self.check_interval = 30  # 每30秒检查一次
    
    async def start(self):
        """启动闹钟调度器"""
        if self.is_running:
            return
        
        self.is_running = True
        print("闹钟调度器已启动")
        
        while self.is_running:
            try:
                await self.check_alarms()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                print(f"闹钟调度器错误: {e}")
                await asyncio.sleep(self.check_interval)
    
    def stop(self):
        """停止闹钟调度器"""
        self.is_running = False
        print("闹钟调度器已停止")
    
    async def check_alarms(self):
        """检查是否有闹钟需要触发"""
        try:
            # 获取当前时间
            now = datetime.now()
            current_time = now.strftime("%H:%M")
            current_weekday = now.weekday()  # 0=周一, 6=周日
            
            # 获取所有激活的闹钟
            reminders = alarm_reminder_service.get_active_reminders()
            
            for reminder in reminders:
                # 检查时间是否匹配
                if reminder.alarm_time != current_time:
                    continue
                
                # 检查重复类型
                if not self._should_trigger(reminder, current_weekday):
                    continue
                
                # 检查是否已经触发过（避免同一分钟重复触发）
                if reminder.last_triggered:
                    last_triggered_minute = reminder.last_triggered.strftime("%H:%M")
                    if last_triggered_minute == current_time:
                        continue
                
                # 触发闹钟
                await self.trigger_reminder(reminder)
                
        except Exception as e:
            print(f"检查闹钟时出错: {e}")
    
    def _should_trigger(self, reminder: AlarmReminder, current_weekday: int) -> bool:
        """检查闹钟是否应该触发"""
        if reminder.repeat_type == "once":
            return True
        elif reminder.repeat_type == "daily":
            return True
        elif reminder.repeat_type == "weekly":
            return True
        elif reminder.repeat_type == "custom":
            if reminder.repeat_days:
                return current_weekday in reminder.repeat_days
            return True
        return True
    
    async def trigger_reminder(self, reminder: AlarmReminder):
        """触发闹钟提醒"""
        try:
            print(f"触发闹钟: {reminder.title} ({reminder.alarm_time})")
            
            # 标记为已触发
            alarm_reminder_service.mark_triggered(reminder.id)
            
            # 如果启用了TTS，生成语音提醒
            if reminder.enable_tts and reminder.message:
                try:
                    # 获取角色的语音配置
                    voice = "nova"  # 默认音色
                    speed = 1.0
                    
                    # 这里可以集成角色的语音配置
                    # 暂时使用默认值
                    
                    audio_base64 = await tts_service.text_to_speech_base64(
                        reminder.message,
                        voice=voice,
                        speed=speed
                    )
                    
                    # 这里可以将音频发送给前端播放
                    # 目前只是打印日志
                    print(f"已生成语音提醒: {reminder.title}")
                    
                except Exception as e:
                    print(f"生成语音提醒失败: {e}")
            
            # 这里可以添加其他通知方式，如：
            # - WebSocket推送给前端
            # - 发送邮件通知
            # - 发送短信通知
            
        except Exception as e:
            print(f"触发闹钟失败: {e}")


# 全局闹钟调度器实例
alarm_scheduler = AlarmScheduler()
