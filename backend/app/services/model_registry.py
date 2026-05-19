from typing import Dict, List, Optional
from pydantic import BaseModel
import os

class ModelConfig(BaseModel):
    """单个模型配置"""
    id: str
    name: str
    provider: str
    model_name: str
    base_url: str
    api_key_env: str
    description: str
    enabled: bool = True
    features: List[str] = []

class ModelRegistry:
    """模型注册表 - 管理所有可用的AI模型"""
    
    def __init__(self):
        self.models: Dict[str, ModelConfig] = {}
        self.current_model_id: str = "deepseek-flash"
        self._register_default_models()
    
    def _register_default_models(self):
        """注册默认模型"""
        
        # DeepSeek 模型
        self.register(ModelConfig(
            id="deepseek-flash",
            name="DeepSeek V4 Flash",
            provider="DeepSeek",
            model_name="deepseek-v4-flash",
            base_url="https://api.deepseek.com",
            api_key_env="DEEPSEEK_API_KEY",
            description="快速响应，适合日常对话，成本低",
            enabled=True,
            features=["对话", "低成本", "快速"]
        ))
        
        self.register(ModelConfig(
            id="deepseek-pro",
            name="DeepSeek V4 Pro",
            provider="DeepSeek",
            model_name="deepseek-v4-pro",
            base_url="https://api.deepseek.com",
            api_key_env="DEEPSEEK_API_KEY",
            description="更强的推理能力，适合复杂任务",
            enabled=True,
            features=["对话", "强推理", "复杂任务"]
        ))
        
        # OpenAI 模型
        self.register(ModelConfig(
            id="gpt-4o",
            name="GPT-4o",
            provider="OpenAI",
            model_name="gpt-4o",
            base_url="https://api.openai.com/v1",
            api_key_env="OPENAI_API_KEY",
            description="OpenAI最强模型，多模态支持",
            enabled=False,
            features=["对话", "多模态", "最强"]
        ))
        
        self.register(ModelConfig(
            id="gpt-4o-mini",
            name="GPT-4o Mini",
            provider="OpenAI",
            model_name="gpt-4o-mini",
            base_url="https://api.openai.com/v1",
            api_key_env="OPENAI_API_KEY",
            description="轻量级模型，速度快成本低",
            enabled=False,
            features=["对话", "快速", "低成本"]
        ))
        
        # 通义千问
        self.register(ModelConfig(
            id="qwen-plus",
            name="通义千问 Plus",
            provider="阿里云",
            model_name="qwen-plus",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key_env="DASHSCOPE_API_KEY",
            description="阿里云通义千问，中文能力强",
            enabled=False,
            features=["对话", "中文优化", "长文本"]
        ))
        
        self.register(ModelConfig(
            id="qwen-max",
            name="通义千问 Max",
            provider="阿里云",
            model_name="qwen-max",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key_env="DASHSCOPE_API_KEY",
            description="通义千问最强版本",
            enabled=False,
            features=["对话", "最强", "中文优化"]
        ))
        
        # 智谱清言
        self.register(ModelConfig(
            id="glm-4",
            name="智谱清言 GLM-4",
            provider="智谱AI",
            model_name="glm-4",
            base_url="https://open.bigmodel.cn/api/paas/v4",
            api_key_env="ZHIPU_API_KEY",
            description="智谱AI最新模型",
            enabled=False,
            features=["对话", "中文优化"]
        ))
        
        # 百度文心
        self.register(ModelConfig(
            id="ernie-4.0",
            name="文心一言 4.0",
            provider="百度",
            model_name="ernie-4.0-8k",
            base_url="https://qianfan.baidubce.com/v2",
            api_key_env="BAIDU_API_KEY",
            description="百度文心一言最强版本",
            enabled=False,
            features=["对话", "中文优化", "知识丰富"]
        ))
    
    def register(self, model: ModelConfig):
        """注册新模型"""
        self.models[model.id] = model
    
    def get_model(self, model_id: str) -> Optional[ModelConfig]:
        """获取指定模型配置"""
        return self.models.get(model_id)
    
    def get_current_model(self) -> ModelConfig:
        """获取当前使用的模型"""
        return self.models.get(self.current_model_id)
    
    def set_current_model(self, model_id: str) -> bool:
        """切换当前使用的模型"""
        if model_id in self.models:
            self.current_model_id = model_id
            return True
        return False
    
    def list_models(self, enabled_only: bool = False) -> List[ModelConfig]:
        """列出所有模型"""
        if enabled_only:
            return [m for m in self.models.values() if m.enabled]
        return list(self.models.values())
    
    def list_by_provider(self, provider: str) -> List[ModelConfig]:
        """按提供商列出模型"""
        return [m for m in self.models.values() if m.provider == provider]
    
    def get_api_key(self, model_id: str) -> Optional[str]:
        """获取模型的API密钥"""
        model = self.get_model(model_id)
        if model:
            return os.getenv(model.api_key_env)
        return None

model_registry = ModelRegistry()
