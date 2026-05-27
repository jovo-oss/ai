from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from app.models.database import SessionLocal, ApiConfig
import httpx


class ApiConfigCreate(BaseModel):
    """创建API配置请求"""
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


class ApiConfigUpdate(BaseModel):
    """更新API配置请求"""
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


class ConfigService:
    """API配置服务"""
    
    def __init__(self):
        pass
    
    def create_config(self, data: ApiConfigCreate) -> Dict[str, Any]:
        """创建新的API配置"""
        db = SessionLocal()
        try:
            # 先将该用户的所有其他配置设置为非活跃
            db.query(ApiConfig).filter(
                ApiConfig.user_id == data.user_id
            ).update({"is_active": 0})
            
            new_config = ApiConfig(
                user_id=data.user_id,
                name=data.name,
                api_spec=data.api_spec,
                api_key=data.api_key,
                base_url=data.base_url,
                chat_model=data.chat_model,
                embedding_model=data.embedding_model,
                summary_model=data.summary_model,
                tts_model=data.tts_model,
                image_model=data.image_model,
                vision_model=data.vision_model,
                speech_model=data.speech_model,
                temperature=data.temperature,
                max_tokens=data.max_tokens,
                top_p=data.top_p,
                system_prompt=data.system_prompt,
                is_active=1
            )
            db.add(new_config)
            db.commit()
            db.refresh(new_config)
            
            return {
                "success": True,
                "message": "配置创建成功",
                "config": self._to_dict(new_config)
            }
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"创建失败: {str(e)}"
            }
        finally:
            db.close()
    
    def update_config(self, config_id: int, data: ApiConfigUpdate) -> Dict[str, Any]:
        """更新API配置"""
        db = SessionLocal()
        try:
            config = db.query(ApiConfig).filter(ApiConfig.id == config_id).first()
            if not config:
                return {
                    "success": False,
                    "message": "配置不存在"
                }
            
            update_data = data.dict(exclude_unset=True)
            for key, value in update_data.items():
                setattr(config, key, value)
            
            config.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(config)
            
            return {
                "success": True,
                "message": "配置更新成功",
                "config": self._to_dict(config)
            }
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"更新失败: {str(e)}"
            }
        finally:
            db.close()
    
    def delete_config(self, config_id: int) -> Dict[str, Any]:
        """删除API配置"""
        db = SessionLocal()
        try:
            config = db.query(ApiConfig).filter(ApiConfig.id == config_id).first()
            if not config:
                return {
                    "success": False,
                    "message": "配置不存在"
                }
            
            db.delete(config)
            db.commit()
            
            return {
                "success": True,
                "message": "配置删除成功"
            }
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"删除失败: {str(e)}"
            }
        finally:
            db.close()
    
    def get_config(self, config_id: int) -> Dict[str, Any]:
        """获取单个配置"""
        db = SessionLocal()
        try:
            config = db.query(ApiConfig).filter(ApiConfig.id == config_id).first()
            if not config:
                return {
                    "success": False,
                    "message": "配置不存在"
                }
            
            return {
                "success": True,
                "config": self._to_dict(config)
            }
        finally:
            db.close()
    
    def list_configs(self, user_id: int) -> Dict[str, Any]:
        """获取用户的所有配置"""
        db = SessionLocal()
        try:
            configs = db.query(ApiConfig).filter(
                ApiConfig.user_id == user_id
            ).order_by(ApiConfig.created_at.desc()).all()
            
            return {
                "success": True,
                "configs": [self._to_dict(c) for c in configs]
            }
        finally:
            db.close()
    
    def get_active_config(self, user_id: int) -> Dict[str, Any]:
        """获取用户的活跃配置"""
        db = SessionLocal()
        try:
            config = db.query(ApiConfig).filter(
                ApiConfig.user_id == user_id,
                ApiConfig.is_active == 1
            ).first()
            
            if not config:
                return {
                    "success": False,
                    "message": "没有活跃配置"
                }
            
            return {
                "success": True,
                "config": self._to_dict(config)
            }
        finally:
            db.close()
    
    def set_active_config(self, config_id: int, user_id: int) -> Dict[str, Any]:
        """设置活跃配置"""
        db = SessionLocal()
        try:
            db.query(ApiConfig).filter(
                ApiConfig.user_id == user_id
            ).update({"is_active": 0})
            
            config = db.query(ApiConfig).filter(
                ApiConfig.id == config_id,
                ApiConfig.user_id == user_id
            ).first()
            
            if not config:
                db.rollback()
                return {
                    "success": False,
                    "message": "配置不存在"
                }
            
            config.is_active = 1
            config.updated_at = datetime.utcnow()
            db.commit()
            
            return {
                "success": True,
                "message": "已设置为活跃配置"
            }
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"设置失败: {str(e)}"
            }
        finally:
            db.close()
    
    async def test_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """测试API配置是否可用"""
        try:
            api_key = config_data.get("api_key")
            base_url = config_data.get("base_url")
            model = config_data.get("chat_model", "gpt-3.5-turbo")
            
            if not api_key or not base_url:
                return {
                    "success": False,
                    "message": "API密钥和基础URL不能为空"
                }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": "你好"}],
                        "max_tokens": 10
                    }
                )
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "message": "API连接测试成功"
                    }
                else:
                    return {
                        "success": False,
                        "message": f"API连接失败: {response.status_code} - {response.text}"
                    }
        except Exception as e:
            return {
                "success": False,
                "message": f"测试失败: {str(e)}"
            }
    
    async def fetch_models(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """从API服务器获取可用模型列表"""
        try:
            api_key = config_data.get("api_key")
            base_url = config_data.get("base_url")
            
            if not api_key or not base_url:
                return {
                    "success": False,
                    "message": "API密钥和基础URL不能为空"
                }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{base_url}/models",
                    headers={
                        "Authorization": f"Bearer {api_key}"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("data", [])
                    return {
                        "success": True,
                        "models": [
                            {
                                "id": m.get("id"),
                                "name": m.get("id"),
                                "created": m.get("created")
                            }
                            for m in models
                        ]
                    }
                else:
                    return {
                        "success": False,
                        "message": f"获取模型列表失败: {response.status_code}"
                    }
        except Exception as e:
            return {
                "success": False,
                "message": f"获取模型列表失败: {str(e)}"
            }
    
    def _to_dict(self, config: ApiConfig) -> Dict[str, Any]:
        """将配置对象转换为字典"""
        return {
            "id": config.id,
            "user_id": config.user_id,
            "name": config.name,
            "api_spec": config.api_spec,
            "api_key": config.api_key[:8] + "..." + config.api_key[-4:] if len(config.api_key) > 12 else config.api_key,
            "api_key_full": config.api_key,
            "base_url": config.base_url,
            "chat_model": config.chat_model,
            "embedding_model": config.embedding_model,
            "summary_model": config.summary_model,
            "tts_model": config.tts_model,
            "image_model": config.image_model,
            "vision_model": config.vision_model,
            "speech_model": config.speech_model,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "system_prompt": config.system_prompt,
            "is_active": config.is_active,
            "created_at": config.created_at.isoformat() if config.created_at else None,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None
        }


config_service = ConfigService()
