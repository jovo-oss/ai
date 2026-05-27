from typing import Dict, List, Optional
from pydantic import BaseModel
import json
import os

class CharacterPreset(BaseModel):
    """角色预设配置"""
    id: str
    name: str
    description: str
    personality: str  # 性格描述
    greeting: str  # 开场白
    system_prompt: str  # 系统提示词
    avatar: str = "🤖"  # 头像emoji
    tags: List[str] = []  # 标签
    is_default: bool = False

class CharacterManager:
    """角色预设管理器"""
    
    def __init__(self):
        self.characters: Dict[str, CharacterPreset] = {}
        self.current_character_id: str = "default"
        self.data_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "characters.json")
        self._ensure_data_dir()
        self._load_characters()
        if not self.characters:
            self._create_default_characters()
    
    def _ensure_data_dir(self):
        """确保数据目录存在"""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
    
    def _load_characters(self):
        """从文件加载角色预设"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for char_data in data:
                        char = CharacterPreset(**char_data)
                        self.characters[char.id] = char
                        if char.is_default:
                            self.current_character_id = char.id
                # 如果当前角色不存在，选择第一个角色
                if self.current_character_id not in self.characters and self.characters:
                    self.current_character_id = list(self.characters.keys())[0]
            except Exception as e:
                print(f"加载角色预设失败: {e}")
    
    def _save_characters(self):
        """保存角色预设到文件"""
        try:
            data = [char.dict() for char in self.characters.values()]
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存角色预设失败: {e}")
    
    def _create_default_characters(self):
        """创建默认角色预设 - 现在不再创建默认角色，让用户自己创建"""
        # 不再创建默认角色，用户可以自己创建
        pass
    
    def add_character(self, character: CharacterPreset):
        """添加角色预设"""
        self.characters[character.id] = character
        self._save_characters()
    
    def get_character(self, character_id: str) -> Optional[CharacterPreset]:
        """获取指定角色预设"""
        return self.characters.get(character_id)
    
    def get_current_character(self) -> CharacterPreset:
        """获取当前使用的角色"""
        return self.characters.get(self.current_character_id, self.characters.get("default"))
    
    def set_current_character(self, character_id: str) -> bool:
        """切换当前使用的角色"""
        if character_id in self.characters:
            self.current_character_id = character_id
            return True
        return False
    
    def list_characters(self) -> List[CharacterPreset]:
        """列出所有角色预设"""
        return list(self.characters.values())
    
    def delete_character(self, character_id: str) -> bool:
        """删除角色预设"""
        if character_id in self.characters:
            del self.characters[character_id]
            
            if self.current_character_id == character_id:
                if self.characters:
                    self.current_character_id = list(self.characters.keys())[0]
                else:
                    self.current_character_id = "default"
            
            self._save_characters()
            return True
        return False

character_manager = CharacterManager()
