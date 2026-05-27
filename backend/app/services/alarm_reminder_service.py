from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from app.models.database import SessionLocal, AlarmReminder


class AlarmReminderCreate(BaseModel):
    """创建闹钟提醒请求"""
    user_id: int
    title: str = "提醒"
    message: Optional[str] = None
    alarm_time: str  # HH:MM格式
    repeat_type: str = "once"  # once, daily, weekly, custom
    repeat_days: Optional[list] = None  # [0,1,2,3,4,5,6] 0=周一
    character_id: Optional[str] = None
    character_name: Optional[str] = None
    enable_tts: bool = True


class AlarmReminderUpdate(BaseModel):
    """更新闹钟提醒请求"""
    title: Optional[str] = None
    message: Optional[str] = None
    alarm_time: Optional[str] = None
    repeat_type: Optional[str] = None
    repeat_days: Optional[list] = None
    character_id: Optional[str] = None
    character_name: Optional[str] = None
    enable_tts: Optional[bool] = None
    is_enabled: Optional[bool] = None


class AlarmReminderService:
    """闹钟提醒服务"""
    
    def create_reminder(self, data: AlarmReminderCreate) -> Dict[str, Any]:
        """创建闹钟提醒"""
        db = SessionLocal()
        try:
            reminder = AlarmReminder(
                user_id=data.user_id,
                title=data.title,
                message=data.message,
                alarm_time=data.alarm_time,
                repeat_type=data.repeat_type,
                repeat_days=data.repeat_days,
                character_id=data.character_id,
                character_name=data.character_name,
                enable_tts=data.enable_tts,
                is_enabled=True,
                is_active=True
            )
            db.add(reminder)
            db.commit()
            db.refresh(reminder)
            
            return {
                "success": True,
                "message": "闹钟提醒创建成功",
                "reminder": self._reminder_to_dict(reminder)
            }
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"创建失败: {str(e)}"
            }
        finally:
            db.close()
    
    def get_reminders(self, user_id: int) -> Dict[str, Any]:
        """获取用户的所有闹钟提醒"""
        db = SessionLocal()
        try:
            reminders = db.query(AlarmReminder).filter(
                AlarmReminder.user_id == user_id
            ).order_by(AlarmReminder.alarm_time).all()
            
            return {
                "success": True,
                "reminders": [self._reminder_to_dict(r) for r in reminders]
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"查询失败: {str(e)}"
            }
        finally:
            db.close()
    
    def get_reminder(self, reminder_id: int, user_id: int) -> Dict[str, Any]:
        """获取单个闹钟提醒"""
        db = SessionLocal()
        try:
            reminder = db.query(AlarmReminder).filter(
                AlarmReminder.id == reminder_id,
                AlarmReminder.user_id == user_id
            ).first()
            
            if not reminder:
                return {
                    "success": False,
                    "message": "闹钟提醒不存在"
                }
            
            return {
                "success": True,
                "reminder": self._reminder_to_dict(reminder)
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"查询失败: {str(e)}"
            }
        finally:
            db.close()
    
    def update_reminder(self, reminder_id: int, user_id: int, data: AlarmReminderUpdate) -> Dict[str, Any]:
        """更新闹钟提醒"""
        db = SessionLocal()
        try:
            reminder = db.query(AlarmReminder).filter(
                AlarmReminder.id == reminder_id,
                AlarmReminder.user_id == user_id
            ).first()
            
            if not reminder:
                return {
                    "success": False,
                    "message": "闹钟提醒不存在"
                }
            
            # 更新字段
            if data.title is not None:
                reminder.title = data.title
            if data.message is not None:
                reminder.message = data.message
            if data.alarm_time is not None:
                reminder.alarm_time = data.alarm_time
            if data.repeat_type is not None:
                reminder.repeat_type = data.repeat_type
            if data.repeat_days is not None:
                reminder.repeat_days = data.repeat_days
            if data.character_id is not None:
                reminder.character_id = data.character_id
            if data.character_name is not None:
                reminder.character_name = data.character_name
            if data.enable_tts is not None:
                reminder.enable_tts = data.enable_tts
            if data.is_enabled is not None:
                reminder.is_enabled = data.is_enabled
            
            reminder.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(reminder)
            
            return {
                "success": True,
                "message": "闹钟提醒更新成功",
                "reminder": self._reminder_to_dict(reminder)
            }
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"更新失败: {str(e)}"
            }
        finally:
            db.close()
    
    def delete_reminder(self, reminder_id: int, user_id: int) -> Dict[str, Any]:
        """删除闹钟提醒"""
        db = SessionLocal()
        try:
            reminder = db.query(AlarmReminder).filter(
                AlarmReminder.id == reminder_id,
                AlarmReminder.user_id == user_id
            ).first()
            
            if not reminder:
                return {
                    "success": False,
                    "message": "闹钟提醒不存在"
                }
            
            db.delete(reminder)
            db.commit()
            
            return {
                "success": True,
                "message": "闹钟提醒删除成功"
            }
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"删除失败: {str(e)}"
            }
        finally:
            db.close()
    
    def toggle_reminder(self, reminder_id: int, user_id: int) -> Dict[str, Any]:
        """开关闹钟提醒"""
        db = SessionLocal()
        try:
            reminder = db.query(AlarmReminder).filter(
                AlarmReminder.id == reminder_id,
                AlarmReminder.user_id == user_id
            ).first()
            
            if not reminder:
                return {
                    "success": False,
                    "message": "闹钟提醒不存在"
                }
            
            reminder.is_enabled = not reminder.is_enabled
            reminder.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(reminder)
            
            status = "已启用" if reminder.is_enabled else "已禁用"
            
            return {
                "success": True,
                "message": f"闹钟提醒{status}",
                "reminder": self._reminder_to_dict(reminder)
            }
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"操作失败: {str(e)}"
            }
        finally:
            db.close()
    
    def get_active_reminders(self) -> List[AlarmReminder]:
        """获取所有激活的闹钟提醒（用于定时检查）"""
        db = SessionLocal()
        try:
            reminders = db.query(AlarmReminder).filter(
                AlarmReminder.is_enabled == True,
                AlarmReminder.is_active == True
            ).all()
            return reminders
        finally:
            db.close()
    
    def mark_triggered(self, reminder_id: int):
        """标记闹钟已触发"""
        db = SessionLocal()
        try:
            reminder = db.query(AlarmReminder).filter(
                AlarmReminder.id == reminder_id
            ).first()
            
            if reminder:
                reminder.last_triggered = datetime.utcnow()
                
                # 如果是一次性闹钟，触发后禁用
                if reminder.repeat_type == "once":
                    reminder.is_enabled = False
                
                db.commit()
        finally:
            db.close()
    
    def _reminder_to_dict(self, reminder: AlarmReminder) -> Dict[str, Any]:
        """将闹钟提醒对象转换为字典"""
        return {
            "id": reminder.id,
            "user_id": reminder.user_id,
            "title": reminder.title,
            "message": reminder.message,
            "alarm_time": reminder.alarm_time,
            "repeat_type": reminder.repeat_type,
            "repeat_days": reminder.repeat_days,
            "character_id": reminder.character_id,
            "character_name": reminder.character_name,
            "is_enabled": reminder.is_enabled,
            "is_active": reminder.is_active,
            "enable_tts": reminder.enable_tts,
            "created_at": reminder.created_at.isoformat() if reminder.created_at else None,
            "updated_at": reminder.updated_at.isoformat() if reminder.updated_at else None,
            "last_triggered": reminder.last_triggered.isoformat() if reminder.last_triggered else None
        }


alarm_reminder_service = AlarmReminderService()
