from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any
from app.services.model_registry import model_registry, ModelConfig
from app.services.llm_service import llm_service
from app.services.model_discovery import model_discovery
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

class ApiKeyResponse(BaseModel):
    success: bool
    message: str

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
async def get_api_keys_status():
    """获取所有API密钥的配置状态"""
    providers = {}
    for model in model_registry.models.values():
        if model.provider not in providers:
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
async def update_api_key(config: ApiKeyConfig):
    """更新API密钥配置"""
    env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
    
    try:
        # 读取现有的.env文件
        lines = []
        if os.path.exists(env_file):
            with open(env_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        
        # 查找并更新对应的环境变量
        found = False
        for i, line in enumerate(lines):
            if line.startswith(f"{config.env_name}="):
                lines[i] = f"{config.env_name}={config.api_key}\n"
                found = True
                break
        
        # 如果没有找到，添加新的
        if not found:
            lines.append(f"\n{config.env_name}={config.api_key}\n")
        
        # 写回文件
        with open(env_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        # 更新当前环境变量
        os.environ[config.env_name] = config.api_key
        
        # 重新加载LLM服务
        llm_service._init_client()
        
        return ApiKeyResponse(
            success=True,
            message=f"API密钥已更新"
        )
    except Exception as e:
        return ApiKeyResponse(
            success=False,
            message=f"更新失败: {str(e)}"
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
