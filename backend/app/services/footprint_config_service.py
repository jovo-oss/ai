from sqlalchemy.orm import Session
from app.models.database import FootprintConfig
from typing import Optional


class FootprintConfigService:
    """足迹配置管理服务"""
    
    def get_config(self, db: Session, user_id: int, character_id: str) -> Optional[FootprintConfig]:
        """获取足迹配置"""
        return db.query(FootprintConfig).filter(
            FootprintConfig.user_id == user_id,
            FootprintConfig.character_id == character_id
        ).first()
    
    def create_or_update_config(
        self,
        db: Session,
        user_id: int,
        character_id: str,
        auto_extract_enabled: bool = False,
        context_limit: int = 50,
        extract_interval: int = 5
    ) -> FootprintConfig:
        """创建或更新足迹配置"""
        config = self.get_config(db, user_id, character_id)
        
        if config:
            config.auto_extract_enabled = auto_extract_enabled
            config.context_limit = context_limit
            config.extract_interval = extract_interval
        else:
            config = FootprintConfig(
                user_id=user_id,
                character_id=character_id,
                auto_extract_enabled=auto_extract_enabled,
                context_limit=context_limit,
                extract_interval=extract_interval,
                chat_count=0
            )
            db.add(config)
        
        db.commit()
        db.refresh(config)
        
        return config
    
    def increment_chat_count(self, db: Session, user_id: int, character_id: str) -> int:
        """增加聊天计数并返回当前计数"""
        config = self.get_config(db, user_id, character_id)
        
        if not config:
            config = FootprintConfig(
                user_id=user_id,
                character_id=character_id,
                auto_extract_enabled=False,
                context_limit=50,
                extract_interval=5,
                chat_count=1
            )
            db.add(config)
            db.commit()
            return 1
        
        config.chat_count = (config.chat_count or 0) + 1
        db.commit()
        
        return config.chat_count
    
    def reset_chat_count(self, db: Session, user_id: int, character_id: str):
        """重置聊天计数器"""
        config = self.get_config(db, user_id, character_id)
        
        if config:
            config.chat_count = 0
            db.commit()


footprint_config_service = FootprintConfigService()
