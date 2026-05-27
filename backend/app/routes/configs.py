from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional, List
from app.services.config_service import config_service, ApiConfigCreate, ApiConfigUpdate

router = APIRouter(prefix="/api/configs", tags=["API配置"])


class ConfigCreateRequest(BaseModel):
    user_id: int
    name: str = "默认配置"
    api_spec: str = "OpenAI"
    api_key: str
    base_url: str
    
    chat_model: Optional[str] = None
    embedding_model: Optional[str] = None
    summary_model: Optional[str] = None
    tts_model: Optional[str] = None
    image_model: Optional[str] = None
    vision_model: Optional[str] = None
    speech_model: Optional[str] = None
    
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 1.0
    system_prompt: Optional[str] = None


class ConfigUpdateRequest(BaseModel):
    name: Optional[str] = None
    api_spec: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    
    chat_model: Optional[str] = None
    embedding_model: Optional[str] = None
    summary_model: Optional[str] = None
    tts_model: Optional[str] = None
    image_model: Optional[str] = None
    vision_model: Optional[str] = None
    speech_model: Optional[str] = None
    
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    system_prompt: Optional[str] = None
    
    is_active: Optional[int] = None


class TestConfigRequest(BaseModel):
    api_key: str
    base_url: str
    chat_model: str = "gpt-3.5-turbo"


class FetchModelsRequest(BaseModel):
    api_key: str
    base_url: str


@router.post("/create")
async def create_config(request: ConfigCreateRequest):
    """创建新的API配置"""
    data = ApiConfigCreate(**request.dict())
    return config_service.create_config(data)


@router.put("/update/{config_id}")
async def update_config(config_id: int, request: ConfigUpdateRequest):
    """更新API配置"""
    data = ApiConfigUpdate(**request.dict(exclude_unset=True))
    return config_service.update_config(config_id, data)


@router.delete("/delete/{config_id}")
async def delete_config(config_id: int):
    """删除API配置"""
    return config_service.delete_config(config_id)


@router.get("/get/{config_id}")
async def get_config(config_id: int):
    """获取单个配置"""
    return config_service.get_config(config_id)


@router.get("/list")
async def list_configs(user_id: int = Query(default=1)):
    """获取用户的所有配置"""
    return config_service.list_configs(user_id)


@router.get("/active")
async def get_active_config(user_id: int = Query(default=1)):
    """获取用户的活跃配置"""
    return config_service.get_active_config(user_id)


@router.post("/set-active/{config_id}")
async def set_active_config(config_id: int, user_id: int = Query(default=1)):
    """设置活跃配置"""
    return config_service.set_active_config(config_id, user_id)


@router.post("/test")
async def test_config(request: TestConfigRequest):
    """测试API配置"""
    return await config_service.test_config(request.dict())


@router.post("/fetch-models")
async def fetch_models(request: FetchModelsRequest):
    """获取可用模型列表"""
    return await config_service.fetch_models(request.dict())
