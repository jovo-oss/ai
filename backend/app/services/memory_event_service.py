from sqlalchemy.orm import Session
from app.models.database import MemoryEvent
from typing import List, Optional, Dict, Any
from datetime import datetime


class MemoryEventService:
    """记忆事件管理服务"""
    
    def create_event(
        self,
        db: Session,
        user_id: int,
        character_id: str,
        title: str,
        description: str,
        event_type: str = "main",
        parent_event_id: Optional[int] = None,
        chat_context: Optional[str] = None,
        importance: int = 5,
        tags: Optional[List[str]] = None,
        occurred_at: Optional[datetime] = None
    ) -> MemoryEvent:
        """创建新的事件节点"""
        parent_event = None
        level = 0
        
        if parent_event_id:
            parent_event = db.query(MemoryEvent).filter(
                MemoryEvent.id == parent_event_id,
                MemoryEvent.user_id == user_id,
                MemoryEvent.character_id == character_id
            ).first()
            
            if parent_event:
                level = parent_event.level + 1
        
        event = MemoryEvent(
            user_id=user_id,
            character_id=character_id,
            event_type=event_type,
            title=title,
            description=description,
            parent_event_id=parent_event_id,
            level=level,
            chat_context=chat_context,
            importance=importance,
            tags=tags or [],
            status="active",
            occurred_at=occurred_at or datetime.utcnow()
        )
        
        db.add(event)
        db.commit()
        db.refresh(event)
        
        return event
    
    def get_event(self, db: Session, event_id: int, user_id: int, character_id: str) -> Optional[MemoryEvent]:
        """获取单个事件"""
        return db.query(MemoryEvent).filter(
            MemoryEvent.id == event_id,
            MemoryEvent.user_id == user_id,
            MemoryEvent.character_id == character_id
        ).first()
    
    def get_events_by_character(
        self,
        db: Session,
        user_id: int,
        character_id: str,
        event_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[MemoryEvent]:
        """获取角色的所有事件"""
        query = db.query(MemoryEvent).filter(
            MemoryEvent.user_id == user_id,
            MemoryEvent.character_id == character_id
        )
        
        if event_type:
            query = query.filter(MemoryEvent.event_type == event_type)
        
        if status:
            query = query.filter(MemoryEvent.status == status)
        
        return query.order_by(MemoryEvent.created_at.desc()).all()
    
    def get_event_tree(
        self,
        db: Session,
        user_id: int,
        character_id: str,
        event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取事件树结构"""
        query = db.query(MemoryEvent).filter(
            MemoryEvent.user_id == user_id,
            MemoryEvent.character_id == character_id
        )
        
        if event_type:
            query = query.filter(MemoryEvent.event_type == event_type)
        
        events = query.order_by(MemoryEvent.created_at).all()
        
        event_dict = {}
        root_events = []
        
        for event in events:
            event_data = {
                "id": event.id,
                "title": event.title,
                "description": event.description,
                "event_type": event.event_type,
                "status": event.status,
                "importance": event.importance,
                "tags": event.tags or [],
                "level": event.level,
                "created_at": event.created_at.isoformat() if event.created_at else None,
                "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
                "children": []
            }
            
            event_dict[event.id] = event_data
            
            if event.parent_event_id and event.parent_event_id in event_dict:
                event_dict[event.parent_event_id]["children"].append(event_data)
            else:
                root_events.append(event_data)
        
        return root_events
    
    def update_event(
        self,
        db: Session,
        event_id: int,
        user_id: int,
        character_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        importance: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[MemoryEvent]:
        """更新事件信息"""
        event = self.get_event(db, event_id, user_id, character_id)
        
        if not event:
            return None
        
        if title is not None:
            event.title = title
        if description is not None:
            event.description = description
        if status is not None:
            event.status = status
        if importance is not None:
            event.importance = importance
        if tags is not None:
            event.tags = tags
        
        event.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(event)
        
        return event
    
    def delete_event(self, db: Session, event_id: int, user_id: int, character_id: str) -> bool:
        """删除事件及其所有子事件"""
        event = self.get_event(db, event_id, user_id, character_id)
        
        if not event:
            return False
        
        child_events = db.query(MemoryEvent).filter(
            MemoryEvent.parent_event_id == event_id,
            MemoryEvent.user_id == user_id,
            MemoryEvent.character_id == character_id
        ).all()
        
        for child in child_events:
            self.delete_event(db, child.id, user_id, character_id)
        
        db.delete(event)
        db.commit()
        
        return True
    
    def clear_all_events(self, db: Session, user_id: int, character_id: str) -> bool:
        """清空指定角色的所有事件"""
        events = db.query(MemoryEvent).filter(
            MemoryEvent.user_id == user_id,
            MemoryEvent.character_id == character_id
        ).all()
        
        for event in events:
            db.delete(event)
        
        db.commit()
        return True
    
    def get_child_events(self, db: Session, parent_event_id: int, user_id: int, character_id: str) -> List[MemoryEvent]:
        """获取子事件列表"""
        return db.query(MemoryEvent).filter(
            MemoryEvent.parent_event_id == parent_event_id,
            MemoryEvent.user_id == user_id,
            MemoryEvent.character_id == character_id
        ).order_by(MemoryEvent.created_at).all()


memory_event_service = MemoryEventService()
