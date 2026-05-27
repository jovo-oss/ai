from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.services.footprint_config_service import footprint_config_service

router = APIRouter(prefix="/api/footprint-config", tags=["足迹配置"])


class FootprintConfigRequest(BaseModel):
    character_id: str
    auto_extract_enabled: bool = False
    context_limit: int = 50
    extract_interval: int = 5
    user_id: int = 1


class FootprintConfigResponse(BaseModel):
    success: bool
    message: str
    config: Optional[dict] = None


@router.get("/get/{character_id}", response_model=FootprintConfigResponse)
async def get_footprint_config(
    character_id: str,
    user_id: int = 1,
    db: Session = Depends(get_db)
):
    """获取足迹配置"""
    try:
        config = footprint_config_service.get_config(db, user_id, character_id)
        
        if not config:
            return {
                "success": True,
                "message": "使用默认配置",
                "config": {
                    "auto_extract_enabled": False,
                    "context_limit": 50,
                    "extract_interval": 5,
                    "chat_count": 0
                }
            }
        
        return {
            "success": True,
            "message": "获取配置成功",
            "config": {
                "auto_extract_enabled": config.auto_extract_enabled,
                "context_limit": config.context_limit,
                "extract_interval": config.extract_interval,
                "chat_count": config.chat_count or 0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.post("/update", response_model=FootprintConfigResponse)
async def update_footprint_config(
    request: FootprintConfigRequest,
    db: Session = Depends(get_db)
):
    """更新足迹配置"""
    try:
        config = footprint_config_service.create_or_update_config(
            db=db,
            user_id=request.user_id,
            character_id=request.character_id,
            auto_extract_enabled=request.auto_extract_enabled,
            context_limit=request.context_limit,
            extract_interval=request.extract_interval
        )
        
        return {
            "success": True,
            "message": "配置更新成功",
            "config": {
                "auto_extract_enabled": config.auto_extract_enabled,
                "context_limit": config.context_limit,
                "extract_interval": config.extract_interval
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")
