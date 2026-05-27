from sqlalchemy.orm import Session
from app.models.database import ContextLog
from typing import List, Optional
from datetime import datetime


class ContextLogService:
    """上下文日志管理服务"""
    
    def create_log(
        self,
        db: Session,
        user_id: int,
        character_id: str,
        log_type: str = "auto_extract",
        status: str = "success",
        message: str = "",
        context_count: Optional[int] = None,
        extracted_count: int = 0,
        updated_count: int = 0,
        error_message: Optional[str] = None
    ) -> ContextLog:
        """创建日志记录"""
        log = ContextLog(
            user_id=user_id,
            character_id=character_id,
            log_type=log_type,
            status=status,
            message=message,
            context_count=context_count,
            extracted_count=extracted_count,
            updated_count=updated_count,
            error_message=error_message
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        
        return log
    
    def get_logs_by_character(
        self,
        db: Session,
        user_id: int,
        character_id: str,
        limit: int = 50
    ) -> List[ContextLog]:
        """获取角色的日志记录"""
        return db.query(ContextLog).filter(
            ContextLog.user_id == user_id,
            ContextLog.character_id == character_id
        ).order_by(ContextLog.created_at.desc()).limit(limit).all()
    
    def get_logs_by_user(
        self,
        db: Session,
        user_id: int,
        limit: int = 100
    ) -> List[ContextLog]:
        """获取用户的日志记录"""
        return db.query(ContextLog).filter(
            ContextLog.user_id == user_id
        ).order_by(ContextLog.created_at.desc()).limit(limit).all()


context_log_service = ContextLogService()
