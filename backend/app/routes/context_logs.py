from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.database import get_db, ContextLog
from app.services.context_log_service import context_log_service

router = APIRouter(prefix="/api/context-logs", tags=["上下文日志"])


class ContextLogResponse(BaseModel):
    success: bool
    message: str
    logs: Optional[List[dict]] = None


class DeleteResponse(BaseModel):
    success: bool
    message: str


@router.get("/character/{character_id}", response_model=ContextLogResponse)
async def get_context_logs(
    character_id: str,
    user_id: int = 1,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """获取角色的上下文日志"""
    try:
        logs = context_log_service.get_logs_by_character(
            db=db,
            user_id=user_id,
            character_id=character_id,
            limit=limit
        )
        
        log_list = []
        for log in logs:
            log_list.append({
                "id": log.id,
                "user_id": log.user_id,
                "character_id": log.character_id,
                "log_type": log.log_type,
                "status": log.status,
                "message": log.message,
                "context_count": log.context_count,
                "extracted_count": log.extracted_count,
                "updated_count": log.updated_count,
                "error_message": log.error_message,
                "created_at": log.created_at.isoformat() if log.created_at else None
            })
        
        return {
            "success": True,
            "message": "获取日志成功",
            "logs": log_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取日志失败: {str(e)}")


@router.get("/user", response_model=ContextLogResponse)
async def get_user_context_logs(
    user_id: int = 1,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取用户的上下文日志"""
    try:
        logs = context_log_service.get_logs_by_user(
            db=db,
            user_id=user_id,
            limit=limit
        )
        
        log_list = []
        for log in logs:
            log_list.append({
                "id": log.id,
                "user_id": log.user_id,
                "character_id": log.character_id,
                "log_type": log.log_type,
                "status": log.status,
                "message": log.message,
                "context_count": log.context_count,
                "extracted_count": log.extracted_count,
                "updated_count": log.updated_count,
                "error_message": log.error_message,
                "created_at": log.created_at.isoformat() if log.created_at else None
            })
        
        return {
            "success": True,
            "message": "获取日志成功",
            "logs": log_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取日志失败: {str(e)}")


@router.delete("/character/{character_id}", response_model=DeleteResponse)
async def delete_context_logs(
    character_id: str,
    user_id: int = 1,
    db: Session = Depends(get_db)
):
    """删除角色的所有上下文日志"""
    try:
        logs = db.query(ContextLog).filter(
            ContextLog.user_id == user_id,
            ContextLog.character_id == character_id
        ).all()
        
        for log in logs:
            db.delete(log)
        
        db.commit()
        
        return {
            "success": True,
            "message": f"已删除 {len(logs)} 条日志"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除日志失败: {str(e)}")
