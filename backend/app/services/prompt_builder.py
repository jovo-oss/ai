from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class PromptBuilder:
    """
    模块化提示词构建器 - 基于SillyTavern的Prompt Order架构
    
    功能：
    1. 将发送给AI的内容分解为多个独立模块
    2. 每个模块可以单独启用/禁用、调整顺序
    3. 支持Token预算管理
    4. 智能组装最终提示词
    
    模块顺序（默认）：
    0. Main Prompt (角色设定 + 环境感知)
    1. Worldbook (世界书 - 智能激活)
    2. Memory/Summary (长期记忆)
    3. Chat History (聊天历史 - 含Author's Note)
    4. Current Message (当前用户输入)
    """
    
    def __init__(self):
        self.modules = {
            'main_prompt': {
                'name': '主提示词',
                'content': '',
                'enabled': True,
                'position': 0,
                'token_budget': 1024,
                'required': True  # 必需模块，不可禁用
            },
            'worldbook': {
                'name': '世界书',
                'content': '',
                'enabled': True,
                'position': 1,
                'token_budget': 2048,
                'required': False
            },
            'memory_summary': {
                'name': '记忆摘要',
                'content': '',
                'enabled': True,
                'position': 2,
                'token_budget': 512,
                'required': False
            },
            'chat_history': {
                'name': '聊天历史',
                'content': [],  # 特殊：存储消息列表
                'enabled': True,
                'position': 3,
                'token_budget': 4096,
                'required': False
            }
        }
        
        self.total_token_limit = 8192  # 默认总Token限制
        
    def set_module_content(self, module_name: str, content: Any) -> bool:
        """设置指定模块的内容"""
        if module_name in self.modules:
            self.modules[module_name]['content'] = content
            return True
        return False
    
    def enable_module(self, module_name: str, enabled: bool = True) -> bool:
        """启用/禁用模块"""
        if module_name in self.modules:
            if not self.modules[module_name]['required']:
                self.modules[module_name]['enabled'] = enabled
                return True
            else:
                logger.warning(f"模块 {module_name} 是必需模块，不能禁用")
        return False
    
    def set_module_position(self, module_name: str, position: int) -> bool:
        """调整模块位置"""
        if module_name in self.modules:
            self.modules[module_name]['position'] = position
            return True
        return False
    
    def set_token_budget(self, module_name: str, budget: int) -> bool:
        """设置模块Token预算"""
        if module_name in self.modules and budget > 0:
            self.modules[module_name]['token_budget'] = budget
            return True
        return False
    
    def build(
        self,
        current_message: str = "",
        include_user_message: bool = True
    ) -> Dict[str, Any]:
        """
        构建最终的提示词
        
        Args:
            current_message: 当前用户消息
            include_user_message: 是否在末尾添加用户消息
            
        Returns:
            {
                "full_prompt": "完整的提示文字符串",
                "modules_used": ["使用的模块列表"],
                "total_tokens_estimated": Token估算数,
                "module_details": {...}
            }
        """
        try:
            # 1. 按 position 排序模块
            sorted_modules = sorted(
                [(name, config) for name, config in self.modules.items() 
                 if config['enabled']],
                key=lambda x: x[1]['position']
            )
            
            # 2. 组装各模块内容
            parts = []
            modules_used = []
            total_tokens = 0
            
            for name, config in sorted_modules:
                content = config['content']
                
                if not content:
                    continue
                
                # 处理不同类型的内容
                if isinstance(content, list):
                    # 聊天历史等列表类型
                    formatted = self._format_chat_messages(content)
                elif isinstance(content, str):
                    formatted = content.strip()
                else:
                    formatted = str(content).strip()
                
                if not formatted:
                    continue
                
                # 检查Token预算
                tokens_estimate = len(formatted) // 4  # 粗略估算：1 token ≈ 4字符
                
                if total_tokens + tokens_estimate > self.total_token_limit:
                    logger.warning(f"达到Token限制，跳过模块: {name}")
                    continue
                
                parts.append(formatted)
                modules_used.append(name)
                total_tokens += tokens_estimate
            
            # 3. 添加当前用户消息（如果需要）
            if include_user_message and current_message:
                user_msg = f"\n\n【用户】\n{current_message}"
                parts.append(user_msg)
            
            # 4. 拼接最终提示词
            full_prompt = "\n\n".join(parts)
            
            result = {
                "full_prompt": full_prompt,
                "modules_used": modules_used,
                "total_tokens_estimated": total_tokens,
                "module_details": {
                    name: {
                        "enabled": config['enabled'],
                        "position": config['position'],
                        "has_content": bool(config['content'])
                    }
                    for name, config in self.modules.items()
                }
            }
            
            logger.info(
                f"[PromptBuilder] ✅ 构建完成! 使用{len(modules_modules)}个模块, "
                f"估算Token数: {total_tokens}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"[PromptBuilder] ❌ 构建失败: {str(e)}")
            raise
    
    def _format_chat_messages(self, messages: List[Dict[str, str]]) -> str:
        """格式化聊天消息列表为文本"""
        if not messages:
            return ""
        
        parts = []
        
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            
            if role == "user":
                role_display = "用户"
            elif role == "assistant":
                role_display = "AI"
            elif role == "system":
                role_display = "系统"
            else:
                role_display = role
            
            parts.append(f"{role_display}: {content}")
        
        return "\n".join(parts)
    
    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return {
            "modules": {
                name: {
                    "name": config["name"],
                    "enabled": config["enabled"],
                    "position": config["position"],
                    "token_budget": config["token_budget"],
                    "has_content": bool(config["content"]),
                    "required": config.get("required", False)
                }
                for name, config in self.modules.items()
            },
            "total_token_limit": self.total_token_limit
        }
    
    def reset(self):
        """重置所有模块内容（保留配置）"""
        for name in self.modules:
            if name != 'chat_history':
                self.modules[name]['content'] = ''
            else:
                self.modules[name]['content'] = []


# 全局实例
prompt_builder = PromptBuilder()
