from openai import OpenAI
from typing import List, Dict, Any, Optional
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

class ModelDiscoveryService:
    """模型发现服务 - 从供应商API拉取可用模型列表"""
    
    PROVIDER_CONFIGS = {
        "DeepSeek": {
            "base_url": "https://api.deepseek.com",
            "api_key_env": "DEEPSEEK_API_KEY",
        },
        "OpenAI": {
            "base_url": "https://api.openai.com/v1",
            "api_key_env": "OPENAI_API_KEY",
        },
        "阿里云": {
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key_env": "DASHSCOPE_API_KEY",
        },
        "智谱AI": {
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "api_key_env": "ZHIPU_API_KEY",
        },
        "百度": {
            "base_url": "https://qianfan.baidubce.com/v2",
            "api_key_env": "BAIDU_API_KEY",
        },
    }
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=3)
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """获取供应商的API Key"""
        config = self.PROVIDER_CONFIGS.get(provider)
        if config:
            key = os.getenv(config["api_key_env"])
            if key and key != f"your_{config['api_key_env'].lower()}":
                return key
        return None
    
    def _fetch_models_sync(self, provider: str) -> List[Dict[str, Any]]:
        """同步拉取模型（在后台线程中运行）"""
        api_key = self.get_api_key(provider)
        if not api_key:
            print(f"供应商 {provider} 的API Key未配置或为默认值")
            return []
        
        config = self.PROVIDER_CONFIGS[provider]
        
        try:
            client = OpenAI(
                api_key=api_key,
                base_url=config["base_url"],
                timeout=15.0
            )
            
            models = client.models.list()
            
            result = []
            for model in models.data:
                model_info = {
                    "id": model.id,
                    "name": model.id,
                    "provider": provider,
                    "created": getattr(model, 'created', None),
                    "owned_by": getattr(model, 'owned_by', provider.lower()),
                }
                result.append(model_info)
            
            print(f"从 {provider} 成功拉取 {len(result)} 个模型")
            return result
            
        except Exception as e:
            error_msg = str(e)
            print(f"从 {provider} 拉取模型失败: {error_msg}")
            return []
    
    def fetch_models_from_provider(self, provider: str) -> List[Dict[str, Any]]:
        """从供应商API拉取可用模型列表"""
        return self._fetch_models_sync(provider)
    
    def fetch_all_providers_models(self) -> Dict[str, List[Dict[str, Any]]]:
        """从所有已配置的供应商拉取模型"""
        result = {}
        
        # 使用线程池并发拉取
        futures = {}
        for provider in self.PROVIDER_CONFIGS.keys():
            future = self.executor.submit(self._fetch_models_sync, provider)
            futures[future] = provider
        
        for future in as_completed(futures):
            provider = futures[future]
            try:
                models = future.result(timeout=20)
                if models:
                    result[provider] = models
            except Exception as e:
                print(f"拉取 {provider} 模型时发生异常: {str(e)}")
        
        return result

model_discovery = ModelDiscoveryService()
