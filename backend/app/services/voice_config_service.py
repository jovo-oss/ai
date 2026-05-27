from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from app.models.database import SessionLocal, CharacterVoiceConfig


class VoiceConfigCreate(BaseModel):
    """创建语音配置请求"""
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


class VoiceConfigUpdate(BaseModel):
    """更新语音配置请求"""
    tts_model: Optional[str] = None
    tts_voice: Optional[str] = None
    speed: Optional[float] = None
    volume: Optional[float] = None
    pitch: Optional[float] = None
    audio_format: Optional[str] = None
    response_format: Optional[str] = None
    enable_tts: Optional[bool] = None
    auto_play: Optional[bool] = None


class VoiceConfigService:
    """角色语音配置服务"""
    
    def __init__(self):
        pass
    
    def create_config(self, data: VoiceConfigCreate) -> Dict[str, Any]:
        """创建新的语音配置"""
        db = SessionLocal()
        try:
            # 检查是否已存在该角色的配置
            existing = db.query(CharacterVoiceConfig).filter(
                CharacterVoiceConfig.user_id == data.user_id,
                CharacterVoiceConfig.character_id == data.character_id
            ).first()
            
            if existing:
                return {
                    "success": False,
                    "message": "该角色已存在语音配置，请使用更新接口"
                }
            
            new_config = CharacterVoiceConfig(
                user_id=data.user_id,
                character_id=data.character_id,
                tts_model=data.tts_model,
                tts_voice=data.tts_voice,
                speed=data.speed,
                volume=data.volume,
                pitch=data.pitch,
                audio_format=data.audio_format,
                response_format=data.response_format,
                enable_tts=data.enable_tts,
                auto_play=data.auto_play
            )
            db.add(new_config)
            db.commit()
            db.refresh(new_config)
            
            return {
                "success": True,
                "message": "语音配置创建成功",
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
    
    def get_config(self, user_id: int, character_id: str) -> Dict[str, Any]:
        """获取角色的语音配置"""
        db = SessionLocal()
        try:
            config = db.query(CharacterVoiceConfig).filter(
                CharacterVoiceConfig.user_id == user_id,
                CharacterVoiceConfig.character_id == character_id
            ).first()
            
            if not config:
                return {
                    "success": False,
                    "message": "未找到该角色的语音配置"
                }
            
            return {
                "success": True,
                "config": self._to_dict(config)
            }
        finally:
            db.close()
    
    def get_all_configs(self, user_id: int) -> Dict[str, Any]:
        """获取用户的所有语音配置"""
        db = SessionLocal()
        try:
            configs = db.query(CharacterVoiceConfig).filter(
                CharacterVoiceConfig.user_id == user_id
            ).all()
            
            return {
                "success": True,
                "configs": [self._to_dict(config) for config in configs]
            }
        finally:
            db.close()
    
    def update_config(self, user_id: int, character_id: str, data: VoiceConfigUpdate) -> Dict[str, Any]:
        """更新角色的语音配置"""
        db = SessionLocal()
        try:
            config = db.query(CharacterVoiceConfig).filter(
                CharacterVoiceConfig.user_id == user_id,
                CharacterVoiceConfig.character_id == character_id
            ).first()
            
            if not config:
                return {
                    "success": False,
                    "message": "未找到该角色的语音配置"
                }
            
            update_data = data.dict(exclude_unset=True)
            for key, value in update_data.items():
                setattr(config, key, value)
            
            config.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(config)
            
            return {
                "success": True,
                "message": "语音配置更新成功",
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
    
    def delete_config(self, user_id: int, character_id: str) -> Dict[str, Any]:
        """删除角色的语音配置"""
        db = SessionLocal()
        try:
            config = db.query(CharacterVoiceConfig).filter(
                CharacterVoiceConfig.user_id == user_id,
                CharacterVoiceConfig.character_id == character_id
            ).first()
            
            if not config:
                return {
                    "success": False,
                    "message": "未找到该角色的语音配置"
                }
            
            db.delete(config)
            db.commit()
            
            return {
                "success": True,
                "message": "语音配置删除成功"
            }
        except Exception as e:
            db.rollback()
            return {
                "success": False,
                "message": f"删除失败: {str(e)}"
            }
        finally:
            db.close()
    
    def _to_dict(self, config: CharacterVoiceConfig) -> Dict[str, Any]:
        """将配置对象转换为字典"""
        return {
            "id": config.id,
            "user_id": config.user_id,
            "character_id": config.character_id,
            "tts_model": config.tts_model,
            "tts_voice": config.tts_voice,
            "speed": config.speed,
            "volume": config.volume,
            "pitch": config.pitch,
            "audio_format": config.audio_format,
            "response_format": config.response_format,
            "enable_tts": config.enable_tts,
            "auto_play": config.auto_play,
            "created_at": config.created_at.isoformat() if config.created_at else None,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None
        }


voice_config_service = VoiceConfigService()
