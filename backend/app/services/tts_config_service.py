from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from app.models.database import SessionLocal, TtsConfig
import httpx


class TtsConfigCreate(BaseModel):
    """创建TTS配置请求"""
    user_id: int
    name: str = "默认TTS配置"
    api_key: str
    base_url: str
    api_spec: str = "OpenAI"
    tts_model: str = "tts-1"
    tts_voice: str = "nova"


class TtsConfigUpdate(BaseModel):
    """更新TTS配置请求"""
    name: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    api_spec: Optional[str] = None
    tts_model: Optional[str] = None
    tts_voice: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class TtsConfigService:
    """TTS配置服务"""
    
    def __init__(self):
        pass
    
    def create_config(self, data: TtsConfigCreate) -> Dict[str, Any]:
        """创建新的TTS配置"""
        db = SessionLocal()
        try:
            # 如果是第一个配置，设为默认
            existing_count = db.query(TtsConfig).filter(
                TtsConfig.user_id == data.user_id
            ).count()
            
            new_config = TtsConfig(
                user_id=data.user_id,
                name=data.name,
                api_key=data.api_key,
                base_url=data.base_url,
                api_spec=data.api_spec,
                tts_model=data.tts_model,
                tts_voice=data.tts_voice,
                is_active=True,
                is_default=(existing_count == 0)
            )
            db.add(new_config)
            db.commit()
            db.refresh(new_config)
            
            return {
                "success": True,
                "message": "TTS配置创建成功",
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
    
    def update_config(self, config_id: int, user_id: int, data: TtsConfigUpdate) -> Dict[str, Any]:
        """更新TTS配置"""
        db = SessionLocal()
        try:
            config = db.query(TtsConfig).filter(
                TtsConfig.id == config_id,
                TtsConfig.user_id == user_id
            ).first()
            
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
                "message": "TTS配置更新成功",
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
    
    def delete_config(self, config_id: int, user_id: int) -> Dict[str, Any]:
        """删除TTS配置"""
        db = SessionLocal()
        try:
            config = db.query(TtsConfig).filter(
                TtsConfig.id == config_id,
                TtsConfig.user_id == user_id
            ).first()
            
            if not config:
                return {
                    "success": False,
                    "message": "配置不存在"
                }
            
            db.delete(config)
            db.commit()
            
            return {
                "success": True,
                "message": "TTS配置删除成功"
            }
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"删除失败: {str(e)}"
            }
        finally:
            db.close()
    
    def get_config(self, config_id: int, user_id: int) -> Dict[str, Any]:
        """获取单个TTS配置"""
        db = SessionLocal()
        try:
            config = db.query(TtsConfig).filter(
                TtsConfig.id == config_id,
                TtsConfig.user_id == user_id
            ).first()
            
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
        """获取用户的所有TTS配置"""
        db = SessionLocal()
        try:
            configs = db.query(TtsConfig).filter(
                TtsConfig.user_id == user_id
            ).order_by(TtsConfig.created_at.desc()).all()
            
            return {
                "success": True,
                "configs": [self._to_dict(c) for c in configs]
            }
        finally:
            db.close()
    
    def get_default_config(self, user_id: int) -> Dict[str, Any]:
        """获取用户的默认TTS配置"""
        db = SessionLocal()
        try:
            config = db.query(TtsConfig).filter(
                TtsConfig.user_id == user_id,
                TtsConfig.is_default == True
            ).first()
            
            if not config:
                # 如果没有默认配置，返回第一个配置
                config = db.query(TtsConfig).filter(
                    TtsConfig.user_id == user_id
                ).first()
            
            if not config:
                return {
                    "success": False,
                    "message": "没有可用的TTS配置"
                }
            
            return {
                "success": True,
                "config": self._to_dict(config)
            }
        finally:
            db.close()
    
    def set_default_config(self, config_id: int, user_id: int) -> Dict[str, Any]:
        """设置默认TTS配置"""
        db = SessionLocal()
        try:
            # 先将该用户的所有其他配置设置为非默认
            db.query(TtsConfig).filter(
                TtsConfig.user_id == user_id
            ).update({"is_default": False})
            
            config = db.query(TtsConfig).filter(
                TtsConfig.id == config_id,
                TtsConfig.user_id == user_id
            ).first()
            
            if not config:
                db.rollback()
                return {
                    "success": False,
                    "message": "配置不存在"
                }
            
            config.is_default = True
            config.updated_at = datetime.utcnow()
            db.commit()
            
            return {
                "success": True,
                "message": "已设置为默认TTS配置"
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
        """测试TTS API配置是否可用"""
        try:
            api_key = config_data.get("api_key")
            base_url = config_data.get("base_url")
            
            if not api_key or not base_url:
                return {
                    "success": False,
                    "message": "API密钥和基础URL不能为空"
                }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # 测试TTS接口
                response = await client.post(
                    f"{base_url}/audio/speech",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": config_data.get("tts_model", "tts-1"),
                        "input": "测试语音",
                        "voice": config_data.get("tts_voice", "nova")
                    }
                )
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "message": "TTS API连接测试成功"
                    }
                else:
                    return {
                        "success": False,
                        "message": f"TTS API连接失败: {response.status_code} - {response.text}"
                    }
        except Exception as e:
            return {
                "success": False,
                "message": f"测试失败: {str(e)}"
            }
    
    def _to_dict(self, config: TtsConfig) -> Dict[str, Any]:
        """将配置对象转换为字典"""
        return {
            "id": config.id,
            "user_id": config.user_id,
            "name": config.name,
            "api_key": config.api_key[:8] + "..." + config.api_key[-4:] if len(config.api_key) > 12 else config.api_key,
            "api_key_full": config.api_key,
            "base_url": config.base_url,
            "api_spec": config.api_spec,
            "tts_model": config.tts_model,
            "tts_voice": config.tts_voice,
            "is_active": config.is_active,
            "is_default": config.is_default,
            "created_at": config.created_at.isoformat() if config.created_at else None,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None
        }


tts_config_service = TtsConfigService()
