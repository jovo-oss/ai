from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.services.model_registry import model_registry, ModelConfig
from app.services.llm_service import llm_service
from app.services.model_discovery import model_discovery
from app.models.database import SessionLocal, UserApiKey
import os
import dotenv
import asyncio

router = APIRouter(prefix="/api/models", tags=["模型广场"])

class ModelListResponse(BaseModel):
    success: bool
    models: List[Dict[str, Any]]
    current_model: str

class SwitchModelRequest(BaseModel):
    model_id: str

class SwitchModelResponse(BaseModel):
    success: bool
    message: str
    current_model: str

class ApiKeyConfig(BaseModel):
    env_name: str
    api_key: str
    provider: str

class ApiKeyResponse(BaseModel):
    success: bool
    message: str

def get_user_api_key(user_id: int, provider: str) -> Optional[str]:
    """获取用户的API密钥"""
    db = SessionLocal()
    try:
        api_key_record = db.query(UserApiKey).filter(
            UserApiKey.user_id == user_id,
            UserApiKey.provider == provider
        ).first()
        return api_key_record.api_key if api_key_record else None
    finally:
        db.close()

def save_user_api_key(user_id: int, provider: str, env_name: str, api_key: str):
    """保存用户的API密钥"""
    db = SessionLocal()
    try:
        api_key_record = db.query(UserApiKey).filter(
            UserApiKey.user_id == user_id,
            UserApiKey.provider == provider
        ).first()
        
        if api_key_record:
            api_key_record.api_key = api_key
            api_key_record.env_name = env_name
        else:
            new_record = UserApiKey(
                user_id=user_id,
                provider=provider,
                env_name=env_name,
                api_key=api_key
            )
            db.add(new_record)
        
        db.commit()
    finally:
        db.close()

@router.get("/list", response_model=ModelListResponse)
async def list_models():
    """获取所有可用模型列表"""
    models = model_registry.list_models()
    
    return ModelListResponse(
        success=True,
        models=[
            {
                "id": m.id,
                "name": m.name,
                "provider": m.provider,
                "model_name": m.model_name,
                "description": m.description,
                "enabled": m.enabled,
                "features": m.features,
                "api_key_configured": bool(model_registry.get_api_key(m.id)),
                "api_key_env": m.api_key_env,
                "api_key": model_registry.get_api_key(m.id) or ""
            }
            for m in models
        ],
        current_model=model_registry.current_model_id
    )

@router.get("/providers")
async def list_providers():
    """获取所有提供商列表"""
    providers = {}
    for model in model_registry.models.values():
        if model.provider not in providers:
            providers[model.provider] = []
        providers[model.provider].append({
            "id": model.id,
            "name": model.name,
            "enabled": model.enabled
        })
    
    return {
        "success": True,
        "providers": providers
    }

@router.post("/switch", response_model=SwitchModelResponse)
async def switch_model(request: SwitchModelRequest):
    """切换当前使用的模型"""
    success = llm_service.switch_model(request.model_id)
    
    if success:
        current = model_registry.get_current_model()
        return SwitchModelResponse(
            success=True,
            message=f"已切换到 {current.name}",
            current_model=request.model_id
        )
    else:
        return SwitchModelResponse(
            success=False,
            message=f"模型 {request.model_id} 不存在",
            current_model=model_registry.current_model_id
        )

@router.get("/current")
async def get_current_model():
    """获取当前使用的模型"""
    current = model_registry.get_current_model()
    return {
        "success": True,
        "model": {
            "id": current.id,
            "name": current.name,
            "provider": current.provider,
            "model_name": current.model_name,
            "description": current.description,
            "features": current.features
        }
    }

@router.get("/api-keys")
async def get_api_keys_status(user_id: int = Query(default=1)):
    """获取用户的API密钥配置状态"""
    providers = {}
    for model in model_registry.models.values():
        if model.provider not in providers:
            # 优先使用用户API密钥，其次使用.env中的
            api_key = get_user_api_key(user_id, model.provider)
            if not api_key:
                api_key = model_registry.get_api_key(model.id)
            
            providers[model.provider] = {
                "env_name": model.api_key_env,
                "configured": bool(api_key),
                "masked_key": api_key[:8] + "..." + api_key[-4:] if api_key and len(api_key) > 12 else None
            }
    
    return {
        "success": True,
        "providers": providers
    }

@router.post("/api-keys", response_model=ApiKeyResponse)
async def update_api_key(config: ApiKeyConfig, user_id: int = Query(default=1)):
    """更新用户的API密钥配置"""
    try:
        # 保存到数据库
        save_user_api_key(user_id, config.provider, config.env_name, config.api_key)
        
        # 同时更新环境变量（当前会话生效）
        os.environ[config.env_name] = config.api_key
        
        # 重新加载LLM服务
        llm_service._init_client()
        
        return ApiKeyResponse(
            success=True,
            message=f"API密钥已保存"
        )
    except Exception as e:
        return ApiKeyResponse(
            success=False,
            message=f"保存失败: {str(e)}"
        )

@router.get("/discover")
async def discover_all_models():
    """从所有已配置供应商拉取可用模型"""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, model_discovery.fetch_all_providers_models)
    
    return {
        "success": True,
        "providers": result,
        "total": sum(len(models) for models in result.values())
    }

@router.get("/discover/{provider}")
async def discover_models(provider: str):
    """从指定供应商拉取可用模型列表"""
    loop = asyncio.get_event_loop()
    models = await loop.run_in_executor(None, model_discovery.fetch_models_from_provider, provider)
    
    return {
        "success": True,
        "provider": provider,
        "models": models,
        "count": len(models)
    }

@router.post("/add-custom")
async def add_custom_model(model_data: Dict[str, Any]):
    """添加自定义模型到注册表"""
    try:
        config = ModelConfig(
            id=model_data.get("id", model_data.get("model_id")),
            name=model_data.get("name", model_data.get("model_id")),
            provider=model_data.get("provider", "Custom"),
            model_name=model_data.get("model_id"),
            base_url=model_data.get("base_url", "https://api.openai.com/v1"),
            api_key_env=model_data.get("api_key_env", "CUSTOM_API_KEY"),
            description=model_data.get("description", ""),
            enabled=True,
            features=model_data.get("features", [])
        )
        
        model_registry.register(config)
        
        return {
            "success": True,
            "message": f"模型 {config.name} 已添加",
            "model": {
                "id": config.id,
                "name": config.name,
                "provider": config.provider
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"添加失败: {str(e)}"
        }
