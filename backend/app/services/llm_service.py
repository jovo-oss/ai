from openai import AsyncOpenAI
from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv
from app.services.model_registry import model_registry

load_dotenv()

class LLMService:
    """大语言模型服务 - 支持多模型切换"""
    
    def __init__(self):
        self.client = None
        self.current_model_config = None
        self._init_client()
    
    def _init_client(self):
        """初始化客户端"""
        self.current_model_config = model_registry.get_current_model()
        api_key = model_registry.get_api_key(self.current_model_config.id)
        
        if not api_key:
            print(f"警告: 模型 {self.current_model_config.name} 的API密钥未配置")
        
        self.client = AsyncOpenAI(
            api_key=api_key or "dummy-key",
            base_url=self.current_model_config.base_url
        )
    
    def switch_model(self, model_id: str) -> bool:
        """切换模型"""
        if model_registry.set_current_model(model_id):
            self._init_client()
            return True
        return False
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        model_id: Optional[str] = None
    ) -> str:
        """
        获取AI聊天回复
        :param messages: 聊天消息历史
        :param system_prompt: 系统提示词
        :param temperature: 创造性程度 (0-1)
        :param max_tokens: 最大token数
        :param model_id: 指定使用的模型（可选，不指定则使用当前模型）
        :return: AI回复文本
        """
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages
        
        # 如果指定了模型，临时切换
        original_model = None
        if model_id:
            original_model = self.current_model_config.id
            self.switch_model(model_id)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.current_model_config.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content
        finally:
            # 恢复原来的模型
            if original_model:
                self.switch_model(original_model)
    
    async def extract_user_info(self, message: str) -> Dict[str, Any]:
        """从用户消息中提取重要信息（用于记忆系统）"""
        prompt = """从以下用户消息中提取重要信息，如偏好、习惯、兴趣等。
以JSON格式返回，如果没有重要信息则返回空对象。

示例：
用户消息："我喜欢吃辣，但是对海鲜过敏"
返回：{"food_preferences": ["喜欢吃辣"], "allergies": ["海鲜过敏"]}

用户消息："""
        
        try:
            result = await self.chat_completion(
                messages=[{"role": "user", "content": message}],
                system_prompt=prompt,
                temperature=0.3
            )
            return eval(result)
        except:
            return {}
    
    async def vision_completion(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        image_base64: Optional[str] = None,
        model_id: Optional[str] = None
    ) -> str:
        """
        获取AI视觉分析回复（支持图片输入）
        :param messages: 聊天消息历史
        :param system_prompt: 系统提示词
        :param temperature: 创造性程度 (0-1)
        :param max_tokens: 最大token数
        :param image_base64: 图片的base64编码
        :param model_id: 指定使用的模型（可选，不指定则使用当前模型）
        :return: AI回复文本
        """
        # 如果指定了模型，临时切换
        original_model = None
        if model_id:
            original_model = self.current_model_config.id
            self.switch_model(model_id)
        
        try:
            # 构建消息列表
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + messages
            
            # 添加图片消息
            if image_base64:
                # 检查是否已有用户消息，如果有则在最后一条用户消息中添加图片
                user_message_found = False
                for i in range(len(messages) - 1, -1, -1):
                    if messages[i].get("role") == "user":
                        # 在现有用户消息中添加图片
                        current_content = messages[i]["content"]
                        messages[i]["content"] = [
                            {"type": "text", "text": current_content},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                        user_message_found = True
                        break
                
                # 如果没有用户消息，创建一个新的
                if not user_message_found:
                    messages.append({
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "请分析这张图片"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    })
            
            response = await self.client.chat.completions.create(
                model=self.current_model_config.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content
        finally:
            # 恢复原来的模型
            if original_model:
                self.switch_model(original_model)

llm_service = LLMService()
