from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.tts_config_service import tts_config_service, TtsConfigCreate, TtsConfigUpdate

router = APIRouter(prefix="/api/tts-configs", tags=["TTS配置"])


class TtsTestRequest(BaseModel):
    """TTS测试请求"""
    config_id: int
    user_id: int
    text: str = "这是一段测试语音"


@router.post("/create")
async def create_tts_config(data: TtsConfigCreate):
    """创建TTS配置"""
    result = tts_config_service.create_config(data)
    return result


@router.put("/update/{config_id}")
async def update_tts_config(config_id: int, data: TtsConfigUpdate, user_id: int):
    """更新TTS配置"""
    result = tts_config_service.update_config(config_id, user_id, data)
    return result


@router.delete("/delete/{config_id}")
async def delete_tts_config(config_id: int, user_id: int):
    """删除TTS配置"""
    result = tts_config_service.delete_config(config_id, user_id)
    return result


@router.get("/get/{config_id}")
async def get_tts_config(config_id: int, user_id: int):
    """获取单个TTS配置"""
    result = tts_config_service.get_config(config_id, user_id)
    return result


@router.get("/list")
async def list_tts_configs(user_id: int):
    """获取用户的所有TTS配置"""
    result = tts_config_service.list_configs(user_id)
    return result


@router.get("/default")
async def get_default_tts_config(user_id: int):
    """获取用户的默认TTS配置"""
    result = tts_config_service.get_default_config(user_id)
    return result


@router.post("/set-default/{config_id}")
async def set_default_tts_config(config_id: int, user_id: int):
    """设置默认TTS配置"""
    result = tts_config_service.set_default_config(config_id, user_id)
    return result


@router.post("/test")
async def test_tts_config(request: TtsTestRequest):
    """测试TTS配置"""
    # 先获取配置
    config_result = tts_config_service.get_config(request.config_id, request.user_id)
    
    if not config_result["success"]:
        return config_result
    
    config = config_result["config"]
    
    # 测试配置
    test_data = {
        "api_key": config["api_key_full"],
        "base_url": config["base_url"],
        "tts_model": config["tts_model"],
        "tts_voice": config["tts_voice"]
    }
    
    result = await tts_config_service.test_config(test_data)
    return result
