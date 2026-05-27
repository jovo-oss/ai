from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from app.services.alarm_reminder_service import alarm_reminder_service, AlarmReminderCreate, AlarmReminderUpdate

router = APIRouter(prefix="/api/alarm-reminders", tags=["闹钟提醒"])


@router.post("/create")
async def create_reminder(data: AlarmReminderCreate):
    """创建闹钟提醒"""
    return alarm_reminder_service.create_reminder(data)


@router.get("/list")
async def get_reminders(user_id: int):
    """获取用户的闹钟提醒列表"""
    return alarm_reminder_service.get_reminders(user_id)


@router.get("/get/{reminder_id}")
async def get_reminder(reminder_id: int, user_id: int):
    """获取单个闹钟提醒"""
    return alarm_reminder_service.get_reminder(reminder_id, user_id)


@router.put("/update/{reminder_id}")
async def update_reminder(reminder_id: int, user_id: int, data: AlarmReminderUpdate):
    """更新闹钟提醒"""
    return alarm_reminder_service.update_reminder(reminder_id, user_id, data)


@router.delete("/delete/{reminder_id}")
async def delete_reminder(reminder_id: int, user_id: int):
    """删除闹钟提醒"""
    return alarm_reminder_service.delete_reminder(reminder_id, user_id)


@router.post("/toggle/{reminder_id}")
async def toggle_reminder(reminder_id: int, user_id: int):
    """开关闹钟提醒"""
    return alarm_reminder_service.toggle_reminder(reminder_id, user_id)
