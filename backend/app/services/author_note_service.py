from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class AuthorNoteService:
    """
    Author's Note（作者注释）服务 - 基于SillyTavern架构
    
    功能：
    1. 管理每个角色的Author's Note配置
    2. 根据配置在聊天历史中智能插入注释
    3. 支持循环插入、深度控制等高级特性
    
    配置参数说明：
    - content: 注释内容
    - depth: 插入位置（倒数第N条消息后）
    - interval: 循环间隔（每N条用户消息重复一次）
    - enabled: 是否启用
    - position: before/after（在消息前/后插入）
    """
    
    def __init__(self):
        self.default_config = {
            "content": "",
            "depth": 3,
            "interval": 4,
            "enabled": False,
            "position": "after"
        }
    
    def insert_author_note(
        self,
        messages: List[Dict[str, str]],
        config: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """
        在消息列表中插入Author's Note
        
        Args:
            messages: 聊天消息列表 [{"role": "user/assistant", "content": "..."}]
            config: Author's Note配置
            
        Returns:
            插入后的消息列表
        """
        if not config.get("enabled") or not config.get("content"):
            return messages
        
        if len(messages) < 2:
            return messages
        
        try:
            depth = config.get("depth", self.default_config["depth"])
            interval = config.get("interval", self.default_config["interval"])
            position = config.get("position", self.default_config["position"])
            
            # 统计最近的用户消息数量（用于判断是否达到循环间隔）
            recent_user_messages = sum(
                1 for m in messages[-(depth + interval * 2):] 
                if m.get("role") == "user"
            )
            
            # 检查是否应该插入（根据interval）
            if interval > 0 and (recent_user_messages % interval != 0):
                logger.debug(f"[Author's Note] 未达循环间隔 ({recent_user_messages} % {interval} != 0)")
                return messages
            
            # 计算插入位置
            if depth >= len(messages):
                insert_index = 0  # 如果depth超出范围，插入到最前面
            else:
                insert_index = len(messages) - depth
            
            # 构建Author's Note消息
            note_content = f"[Author's Note: {config['content']}]"
            
            author_note_msg = {
                "role": "system",
                "content": note_content
            }
            
            # 插入消息
            if position == "before":
                # 在目标位置之前插入
                messages.insert(max(0, insert_index - 1), author_note_msg)
            else:
                # 在目标位置之后插入（默认）
                messages.insert(insert_index, author_note_msg)
            
            logger.info(
                f"[Author's Note] ✅ 已插入! 位置={insert_index}, "
                f"深度={depth}, 间隔={interval}, 内容长度={len(config['content'])}"
            )
            
            return messages
            
        except Exception as e:
            logger.error(f"[Author's Note] ❌ 插入失败: {str(e)}")
            return messages
    
    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return self.default_config.copy()
    
    def validate_config(self, config: Dict[str, Any]) -> tuple[bool, str]:
        """
        验证配置的有效性
        
        Returns:
            (是否有效, 错误信息)
        """
        required_fields = ["content"]
        
        for field in required_fields:
            if field not in config:
                return False, f"缺少必要字段: {field}"
        
        # 验证数值范围
        if "depth" in config and (not isinstance(config["depth"], int) or config["depth"] < 0):
            return False, "depth必须是非负整数"
        
        if "interval" in config and (not isinstance(config["interval"], int) or config["interval"] < 0):
            return False, "interval必须是非负整数"
        
        if "position" in config and config["position"] not in ["before", "after"]:
            return False, "position必须是'before'或'after'"
        
        return True, ""


# 全局实例
author_note_service = AuthorNoteService()
