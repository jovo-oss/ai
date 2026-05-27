from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.models.database import get_db, GreetingSchedule, SpecialDate, CareReminder
from app.services.proactive_interaction_service import proactive_interaction_service
from datetime import datetime

router = APIRouter(prefix="/api/proactive", tags=["主动互动"])

# ==================== 问候时间表 ====================

class GreetingScheduleCreate(BaseModel):
    user_id: int
    greeting_type: str  # morning, noon, evening, night, custom
    greeting_time: str  # HH:MM
    character_id: Optional[str] = None
    character_name: Optional[str] = None
    custom_message: Optional[str] = None
    is_enabled: bool = True
    enable_tts: bool = True

class GreetingScheduleUpdate(BaseModel):
    greeting_time: Optional[str] = None
    character_id: Optional[str] = None
    character_name: Optional[str] = None
    custom_message: Optional[str] = None
    is_enabled: Optional[bool] = None
    enable_tts: Optional[bool] = None

@router.get("/greetings/{user_id}")
async def get_greeting_schedules(user_id: int, db = Depends(get_db)):
    """获取用户的问候时间表"""
    schedules = db.query(GreetingSchedule).filter(
        GreetingSchedule.user_id == user_id
    ).all()
    
    return {
        "success": True,
        "schedules": [
            {
                "id": s.id,
                "greeting_type": s.greeting_type,
                "greeting_time": s.greeting_time,
                "character_name": s.character_name,
                "custom_message": s.custom_message,
                "is_enabled": s.is_enabled,
                "enable_tts": s.enable_tts,
                "last_triggered": s.last_triggered.isoformat() if s.last_triggered else None
            }
            for s in schedules
        ]
    }

@router.post("/greetings")
async def create_greeting_schedule(data: GreetingScheduleCreate, db = Depends(get_db)):
    """创建问候时间表"""
    schedule = GreetingSchedule(
        user_id=data.user_id,
        greeting_type=data.greeting_type,
        greeting_time=data.greeting_time,
        character_id=data.character_id,
        character_name=data.character_name,
        custom_message=data.custom_message,
        is_enabled=data.is_enabled,
        enable_tts=data.enable_tts
    )
    
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    
    return {
        "success": True,
        "message": "问候时间已创建",
        "schedule_id": schedule.id
    }

@router.put("/greetings/{schedule_id}")
async def update_greeting_schedule(schedule_id: int, data: GreetingScheduleUpdate, db = Depends(get_db)):
    """更新问候时间表"""
    schedule = db.query(GreetingSchedule).filter(GreetingSchedule.id == schedule_id).first()
    if not schedule:
        return {"success": False, "message": "问候时间不存在"}
    
    if data.greeting_time is not None:
        schedule.greeting_time = data.greeting_time
    if data.character_id is not None:
        schedule.character_id = data.character_id
    if data.character_name is not None:
        schedule.character_name = data.character_name
    if data.custom_message is not None:
        schedule.custom_message = data.custom_message
    if data.is_enabled is not None:
        schedule.is_enabled = data.is_enabled
    if data.enable_tts is not None:
        schedule.enable_tts = data.enable_tts
    
    schedule.updated_at = datetime.utcnow()
    db.commit()
    
    return {"success": True, "message": "问候时间已更新"}

@router.delete("/greetings/{schedule_id}")
async def delete_greeting_schedule(schedule_id: int, db = Depends(get_db)):
    """删除问候时间表"""
    schedule = db.query(GreetingSchedule).filter(GreetingSchedule.id == schedule_id).first()
    if not schedule:
        return {"success": False, "message": "问候时间不存在"}
    
    db.delete(schedule)
    db.commit()
    
    return {"success": True, "message": "问候时间已删除"}

# ==================== 特殊日子 ====================

class SpecialDateCreate(BaseModel):
    user_id: int
    title: str
    date_type: str  # birthday, anniversary, custom
    month: int
    day: int
    year: Optional[int] = None
    related_person: Optional[str] = None
    character_id: Optional[str] = None
    character_name: Optional[str] = None
    remind_days_before: int = 0
    is_enabled: bool = True
    enable_tts: bool = True
    custom_message: Optional[str] = None

class SpecialDateUpdate(BaseModel):
    title: Optional[str] = None
    month: Optional[int] = None
    day: Optional[int] = None
    year: Optional[int] = None
    related_person: Optional[str] = None
    character_id: Optional[str] = None
    character_name: Optional[str] = None
    remind_days_before: Optional[int] = None
    is_enabled: Optional[bool] = None
    enable_tts: Optional[bool] = None
    custom_message: Optional[str] = None

@router.get("/special-dates/{user_id}")
async def get_special_dates(user_id: int, db = Depends(get_db)):
    """获取用户的特殊日子"""
    dates = db.query(SpecialDate).filter(
        SpecialDate.user_id == user_id
    ).all()
    
    return {
        "success": True,
        "dates": [
            {
                "id": d.id,
                "title": d.title,
                "date_type": d.date_type,
                "month": d.month,
                "day": d.day,
                "year": d.year,
                "related_person": d.related_person,
                "character_name": d.character_name,
                "remind_days_before": d.remind_days_before,
                "is_enabled": d.is_enabled,
                "enable_tts": d.enable_tts,
                "custom_message": d.custom_message,
                "last_triggered": d.last_triggered.isoformat() if d.last_triggered else None
            }
            for d in dates
        ]
    }

@router.post("/special-dates")
async def create_special_date(data: SpecialDateCreate, db = Depends(get_db)):
    """创建特殊日子"""
    special_date = SpecialDate(
        user_id=data.user_id,
        title=data.title,
        date_type=data.date_type,
        month=data.month,
        day=data.day,
        year=data.year,
        related_person=data.related_person,
        character_id=data.character_id,
        character_name=data.character_name,
        remind_days_before=data.remind_days_before,
        is_enabled=data.is_enabled,
        enable_tts=data.enable_tts,
        custom_message=data.custom_message
    )
    
    db.add(special_date)
    db.commit()
    db.refresh(special_date)
    
    return {
        "success": True,
        "message": "特殊日子已创建",
        "date_id": special_date.id
    }

@router.put("/special-dates/{date_id}")
async def update_special_date(date_id: int, data: SpecialDateUpdate, db = Depends(get_db)):
    """更新特殊日子"""
    special_date = db.query(SpecialDate).filter(SpecialDate.id == date_id).first()
    if not special_date:
        return {"success": False, "message": "特殊日子不存在"}
    
    if data.title is not None:
        special_date.title = data.title
    if data.month is not None:
        special_date.month = data.month
    if data.day is not None:
        special_date.day = data.day
    if data.year is not None:
        special_date.year = data.year
    if data.related_person is not None:
        special_date.related_person = data.related_person
    if data.character_id is not None:
        special_date.character_id = data.character_id
    if data.character_name is not None:
        special_date.character_name = data.character_name
    if data.remind_days_before is not None:
        special_date.remind_days_before = data.remind_days_before
    if data.is_enabled is not None:
        special_date.is_enabled = data.is_enabled
    if data.enable_tts is not None:
        special_date.enable_tts = data.enable_tts
    if data.custom_message is not None:
        special_date.custom_message = data.custom_message
    
    special_date.updated_at = datetime.utcnow()
    db.commit()
    
    return {"success": True, "message": "特殊日子已更新"}

@router.delete("/special-dates/{date_id}")
async def delete_special_date(date_id: int, db = Depends(get_db)):
    """删除特殊日子"""
    special_date = db.query(SpecialDate).filter(SpecialDate.id == date_id).first()
    if not special_date:
        return {"success": False, "message": "特殊日子不存在"}
    
    db.delete(special_date)
    db.commit()
    
    return {"success": True, "message": "特殊日子已删除"}

# ==================== 习惯关怀提醒 ====================

class CareReminderCreate(BaseModel):
    user_id: int
    care_type: str  # water, rest, exercise, eye, meal, sleep
    reminder_time: str  # HH:MM
    repeat_type: str = "daily"  # once, daily, weekly, custom
    repeat_days: Optional[list] = None
    character_id: Optional[str] = None
    character_name: Optional[str] = None
    custom_message: Optional[str] = None
    is_enabled: bool = True
    enable_tts: bool = True

class CareReminderUpdate(BaseModel):
    reminder_time: Optional[str] = None
    repeat_type: Optional[str] = None
    repeat_days: Optional[list] = None
    character_id: Optional[str] = None
    character_name: Optional[str] = None
    custom_message: Optional[str] = None
    is_enabled: Optional[bool] = None
    enable_tts: Optional[bool] = None

@router.get("/care-reminders/{user_id}")
async def get_care_reminders(user_id: int, db = Depends(get_db)):
    """获取用户的关怀提醒"""
    reminders = db.query(CareReminder).filter(
        CareReminder.user_id == user_id
    ).all()
    
    return {
        "success": True,
        "reminders": [
            {
                "id": r.id,
                "care_type": r.care_type,
                "reminder_time": r.reminder_time,
                "repeat_type": r.repeat_type,
                "repeat_days": r.repeat_days,
                "character_name": r.character_name,
                "custom_message": r.custom_message,
                "is_enabled": r.is_enabled,
                "enable_tts": r.enable_tts,
                "last_triggered": r.last_triggered.isoformat() if r.last_triggered else None
            }
            for r in reminders
        ]
    }

@router.post("/care-reminders")
async def create_care_reminder(data: CareReminderCreate, db = Depends(get_db)):
    """创建关怀提醒"""
    reminder = CareReminder(
        user_id=data.user_id,
        care_type=data.care_type,
        reminder_time=data.reminder_time,
        repeat_type=data.repeat_type,
        repeat_days=data.repeat_days,
        character_id=data.character_id,
        character_name=data.character_name,
        custom_message=data.custom_message,
        is_enabled=data.is_enabled,
        enable_tts=data.enable_tts
    )
    
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    
    return {
        "success": True,
        "message": "关怀提醒已创建",
        "reminder_id": reminder.id
    }

@router.put("/care-reminders/{reminder_id}")
async def update_care_reminder(reminder_id: int, data: CareReminderUpdate, db = Depends(get_db)):
    """更新关怀提醒"""
    reminder = db.query(CareReminder).filter(CareReminder.id == reminder_id).first()
    if not reminder:
        return {"success": False, "message": "关怀提醒不存在"}
    
    if data.reminder_time is not None:
        reminder.reminder_time = data.reminder_time
    if data.repeat_type is not None:
        reminder.repeat_type = data.repeat_type
    if data.repeat_days is not None:
        reminder.repeat_days = data.repeat_days
    if data.character_id is not None:
        reminder.character_id = data.character_id
    if data.character_name is not None:
        reminder.character_name = data.character_name
    if data.custom_message is not None:
        reminder.custom_message = data.custom_message
    if data.is_enabled is not None:
        reminder.is_enabled = data.is_enabled
    if data.enable_tts is not None:
        reminder.enable_tts = data.enable_tts
    
    reminder.updated_at = datetime.utcnow()
    db.commit()
    
    return {"success": True, "message": "关怀提醒已更新"}

@router.delete("/care-reminders/{reminder_id}")
async def delete_care_reminder(reminder_id: int, db = Depends(get_db)):
    """删除关怀提醒"""
    reminder = db.query(CareReminder).filter(CareReminder.id == reminder_id).first()
    if not reminder:
        return {"success": False, "message": "关怀提醒不存在"}
    
    db.delete(reminder)
    db.commit()
    
    return {"success": True, "message": "关怀提醒已删除"}

# ==================== 服务控制 ====================

@router.post("/service/start")
async def start_service():
    """启动主动互动服务"""
    if not proactive_interaction_service.is_running:
        import asyncio
        asyncio.create_task(proactive_interaction_service.start())
    
    return {
        "success": True,
        "message": "主动互动服务已启动",
        "is_running": proactive_interaction_service.is_running
    }

@router.post("/service/stop")
async def stop_service():
    """停止主动互动服务"""
    proactive_interaction_service.stop()
    
    return {
        "success": True,
        "message": "主动互动服务已停止",
        "is_running": proactive_interaction_service.is_running
    }

@router.get("/service/status")
async def get_service_status():
    """获取服务状态"""
    return {
        "success": True,
        "is_running": proactive_interaction_service.is_running,
        "check_interval": proactive_interaction_service.check_interval
    }
