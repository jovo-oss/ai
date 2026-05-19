from typing import Dict, List, Optional
from pydantic import BaseModel
import json
import os
from datetime import datetime

class WorldBookEntry(BaseModel):
    """世界书条目"""
    id: str
    title: str
    content: str
    category: str = "general"  # 分类：general, character, location, item, lore, rule
    tags: List[str] = []
    is_active: bool = True
    created_at: str = ""
    updated_at: str = ""

class WorldBookManager:
    """世界书管理器"""
    
    def __init__(self):
        self.entries: Dict[str, WorldBookEntry] = {}
        self.data_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "worldbook.json")
        self._ensure_data_dir()
        self._load_worldbook()
        if not self.entries:
            self._create_default_entries()
    
    def _ensure_data_dir(self):
        """确保数据目录存在"""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
    
    def _load_worldbook(self):
        """从文件加载世界书"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for entry_data in data:
                        entry = WorldBookEntry(**entry_data)
                        self.entries[entry.id] = entry
            except Exception as e:
                print(f"加载世界书失败: {e}")
    
    def _save_worldbook(self):
        """保存世界书到文件"""
        try:
            data = [entry.dict() for entry in self.entries.values()]
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存世界书失败: {e}")
    
    def _create_default_entries(self):
        """创建默认世界书条目"""
        now = datetime.now().isoformat()
        
        self.add_entry(WorldBookEntry(
            id="default-greeting",
            title="欢迎语",
            content="这是一个AI聊天系统，支持多模型切换、角色预设和世界书功能。",
            category="general",
            tags=["系统", "说明"],
            is_active=True,
            created_at=now,
            updated_at=now
        ))
        
        self._save_worldbook()
    
    def add_entry(self, entry: WorldBookEntry) -> WorldBookEntry:
        """添加世界书条目"""
        now = datetime.now().isoformat()
        if not entry.created_at:
            entry.created_at = now
        entry.updated_at = now
        self.entries[entry.id] = entry
        self._save_worldbook()
        return entry
    
    def get_entry(self, entry_id: str) -> Optional[WorldBookEntry]:
        """获取指定条目"""
        return self.entries.get(entry_id)
    
    def list_entries(self, category: Optional[str] = None, active_only: bool = False) -> List[WorldBookEntry]:
        """列出世界书条目"""
        entries = list(self.entries.values())
        
        if category:
            entries = [e for e in entries if e.category == category]
        
        if active_only:
            entries = [e for e in entries if e.is_active]
        
        return entries
    
    def update_entry(self, entry_id: str, updates: dict) -> Optional[WorldBookEntry]:
        """更新条目"""
        if entry_id in self.entries:
            entry = self.entries[entry_id]
            for key, value in updates.items():
                if hasattr(entry, key):
                    setattr(entry, key, value)
            entry.updated_at = datetime.now().isoformat()
            self._save_worldbook()
            return entry
        return None
    
    def delete_entry(self, entry_id: str) -> bool:
        """删除条目"""
        if entry_id in self.entries:
            del self.entries[entry_id]
            self._save_worldbook()
            return True
        return False
    
    def get_categories(self) -> List[str]:
        """获取所有分类"""
        categories = set()
        for entry in self.entries.values():
            categories.add(entry.category)
        return sorted(list(categories))
    
    def search_entries(self, keyword: str) -> List[WorldBookEntry]:
        """搜索条目"""
        keyword = keyword.lower()
        results = []
        for entry in self.entries.values():
            if (keyword in entry.title.lower() or 
                keyword in entry.content.lower() or 
                any(keyword in tag.lower() for tag in entry.tags)):
                results.append(entry)
        return results
    
    def get_active_context(self) -> str:
        """获取所有激活条目的上下文文本（用于注入到系统提示词）"""
        active_entries = [e for e in self.entries.values() if e.is_active]
        if not active_entries:
            return ""
        
        context_parts = []
        for entry in active_entries:
            context_parts.append(f"【{entry.title}】\n{entry.content}")
        
        return "\n\n".join(context_parts)

worldbook_manager = WorldBookManager()
