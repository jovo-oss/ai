from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional, List
from app.services.voice_config_service import voice_config_service, VoiceConfigCreate, VoiceConfigUpdate

router = APIRouter(prefix="/api/voice-configs", tags=["角色语音配置"])


class VoiceConfigCreateRequest(BaseModel):
    user_id: int
    character_id: str
    
    tts_model: str = "tts-1"
    tts_voice: str = "nova"
    speed: float = 1.0
    volume: float = 1.0
    pitch: float = 1.0
    audio_format: str = "mp3"
    response_format: str = "mp3"
    enable_tts: bool = True
    auto_play: bool = False


class VoiceConfigUpdateRequest(BaseModel):
    tts_model: Optional[str] = None
    tts_voice: Optional[str] = None
    speed: Optional[float] = None
    volume: Optional[float] = None
    pitch: Optional[float] = None
    audio_format: Optional[str] = None
    response_format: Optional[str] = None
    enable_tts: Optional[bool] = None
    auto_play: Optional[bool] = None


@router.post("/create")
async def create_voice_config(request: VoiceConfigCreateRequest):
    """创建角色语音配置"""
    return voice_config_service.create_config(request)


@router.get("/get")
async def get_voice_config(character_id: str, user_id: int = Query(default=1)):
    """获取角色语音配置"""
    return voice_config_service.get_config(user_id, character_id)


@router.get("/list")
async def list_voice_configs(user_id: int = Query(default=1)):
    """获取用户所有语音配置"""
    return voice_config_service.get_all_configs(user_id)


@router.put("/update/{character_id}")
async def update_voice_config(character_id: str, request: VoiceConfigUpdateRequest, user_id: int = Query(default=1)):
    """更新角色语音配置"""
    return voice_config_service.update_config(user_id, character_id, request)


@router.delete("/delete/{character_id}")
async def delete_voice_config(character_id: str, user_id: int = Query(default=1)):
    """删除角色语音配置"""
    return voice_config_service.delete_config(user_id, character_id)
