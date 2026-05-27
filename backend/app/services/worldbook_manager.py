from typing import Dict, List, Optional, Any
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
    collection: str = ""  # 集合标识，用于将相关条目分组（如从同一角色生成的条目）
    character_id: str = ""  # 绑定的角色ID，空表示全局共享
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
    
    def list_entries(self, category: Optional[str] = None, active_only: bool = False, character_id: Optional[str] = None) -> List[WorldBookEntry]:
        """列出世界书条目
        
        Args:
            category: 按分类过滤
            active_only: 只返回激活的条目
            character_id: 按角色过滤。如果指定，返回该角色的条目 + 全局条目（character_id为空的条目）
        """
        entries = list(self.entries.values())
        
        if category:
            entries = [e for e in entries if e.category == category]
        
        if active_only:
            entries = [e for e in entries if e.is_active]
        
        if character_id:
            entries = [e for e in entries if e.character_id == character_id or e.character_id == ""]
        
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
    
    def get_active_context(self, character_id: Optional[str] = None) -> str:
        """获取激活条目的上下文文本（用于注入到系统提示词）
        
        Args:
            character_id: 如果指定，只返回该角色的条目 + 全局条目
        """
        active_entries = [e for e in self.entries.values() if e.is_active]
        
        if character_id:
            active_entries = [e for e in active_entries if e.character_id == character_id or e.character_id == ""]
        
        if not active_entries:
            return ""
        
        context_parts = []
        for entry in active_entries:
            context_parts.append(f"【{entry.title}】\n{entry.content}")
        
        return "\n\n".join(context_parts)
    
    def smart_activate_entries(
        self,
        chat_history: List[Dict[str, str]],
        current_message: str = "",
        token_limit: int = 2048,
        character_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        智能激活世界书条目（基于SillyTavern架构增强版）
        
        功能：
        1. 始终激活(always)类型的条目
        2. 根据关键词匹配普通(normal)类型
        3. 按"位置常数"(constant)排序控制插入顺序
        4. 尊重Token预算限制
        
        Args:
            chat_history: 聊天历史消息列表 [{"role": "...", "content": "..."}]
            current_message: 当前用户输入的消息
            token_limit: 最大Token限制
            character_id: 角色ID过滤
            
        Returns:
            激活的条目列表，按constant排序
        """
        activated = []
        used_tokens = 0
        
        # 获取所有激活的条目
        active_entries = [e for e in self.entries.values() if e.is_active]
        
        if character_id:
            active_entries = [e for e in active_entries 
                            if e.character_id == character_id or e.character_id == ""]
        
        # 1. 先激活"始终激活"的条目
        always_entries = [e for e in active_entries 
                        if getattr(e, 'selective_type', 'always') == 'always' 
                        or not hasattr(e, 'selective_type')]
        
        for entry in always_entries:
            entry_tokens = getattr(entry, 'token_budget', 512)
            
            if used_tokens + entry_tokens <= token_limit:
                activated.append({
                    "id": entry.id,
                    "title": entry.title,
                    "content": entry.content,
                    "category": entry.category,
                    "constant": getattr(entry, 'constant', 0),
                    "type": "always"
                })
                used_tokens += entry_tokens
        
        # 2. 构建用于关键词匹配的文本
        recent_text_parts = []
        
        # 提取最近N条消息的内容（scan_depth）
        scan_depth = 5
        for msg in chat_history[-scan_depth:]:
            if msg.get("content"):
                recent_text_parts.append(msg.get("content", ""))
        
        if current_message:
            recent_text_parts.append(current_message)
        
        recent_text = " ".join(recent_text_parts).lower()
        
        # 3. 按关键词匹配普通条目
        normal_entries = [e for e in active_entries 
                        if getattr(e, 'selective_type', 'normal') != 'always']
        
        # 按 constant 降序排序（优先级高的先处理）
        sorted_normal = sorted(
            normal_entries, 
            key=lambda x: getattr(x, 'constant', 0), 
            reverse=True
        )
        
        for entry in sorted_normal:
            keywords = getattr(entry, 'keywords', None)
            
            # 如果没有设置keywords，默认使用title和tags作为关键词
            if not keywords:
                keywords = [entry.title.lower()] + [tag.lower() for tag in entry.tags]
            
            # 检查是否匹配
            is_matched = False
            
            if isinstance(keywords, list):
                for kw in keywords:
                    if kw and kw.lower() in recent_text:
                        is_matched = True
                        break
            elif isinstance(keywords, str):
                if keywords.lower() in recent_text:
                    is_matched = True
            
            if is_matched:
                entry_tokens = getattr(entry, 'token_budget', 512)
                
                if used_tokens + entry_tokens <= token_limit:
                    activated.append({
                        "id": entry.id,
                        "title": entry.title,
                        "content": entry.content,
                        "category": entry.category,
                        "constant": getattr(entry, 'constant', 0),
                        "type": "matched"
                    })
                    used_tokens += entry_tokens
        
        # 4. 最终按 constant 排序输出（小的在前）
        activated.sort(key=lambda x: x["constant"])
        
        return activated
    
    def get_smart_context(
        self,
        chat_history: List[Dict[str, str]],
        current_message: str = "",
        token_limit: int = 2048,
        character_id: Optional[str] = None
    ) -> str:
        """
        获取智能激活后的上下文文本
        
        Args:
            chat_history: 聊天历史
            current_message: 当前消息
            token_limit: Token限制
            character_id: 角色ID
            
        Returns:
            格式化后的上下文字符串
        """
        activated = self.smart_activate_entries(
            chat_history=chat_history,
            current_message=current_message,
            token_limit=token_limit,
            character_id=character_id
        )
        
        if not activated:
            return ""
        
        context_parts = []
        for entry in activated:
            context_parts.append(f"【{entry['title']}】\n{entry['content']}")
        
        return "\n\n".join(context_parts)


worldbook_manager = WorldBookManager()
