from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
import importlib
import os
import sys

class PluginMetadata(BaseModel):
    """插件元数据"""
    name: str
    version: str
    description: str
    author: str
    enabled: bool = True

class BasePlugin(ABC):
    """插件基类 - 所有插件都需要继承这个类"""
    
    def __init__(self):
        self.metadata = PluginMetadata(
            name=self.__class__.__name__,
            version="1.0.0",
            description="",
            author=""
        )
    
    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行插件逻辑
        :param context: 上下文信息，包含用户消息、历史记录等
        :return: 处理后的结果
        """
        pass
    
    async def on_message_received(self, message: str, user_id: str) -> Optional[Dict[str, Any]]:
        """消息接收时触发"""
        return None
    
    async def on_message_sent(self, message: str, user_id: str) -> None:
        """消息发送时触发"""
        pass
    
    async def on_user_login(self, user_id: str) -> None:
        """用户登录时触发"""
        pass

class PluginManager:
    """插件管理器 - 负责加载、注册和管理插件"""
    
    def __init__(self):
        self.plugins: Dict[str, BasePlugin] = {}
    
    def register_plugin(self, plugin: BasePlugin) -> None:
        """注册一个插件"""
        self.plugins[plugin.metadata.name] = plugin
        print(f"✓ 插件已注册: {plugin.metadata.name} v{plugin.metadata.version}")
    
    def load_plugins_from_directory(self, directory: str) -> None:
        """从目录加载所有插件"""
        if not os.path.exists(directory):
            print(f"警告: 插件目录不存在 - {directory}")
            return
        
        for filename in os.listdir(directory):
            if filename.endswith('.py') and not filename.startswith('_'):
                plugin_path = os.path.join(directory, filename)
                self._load_single_plugin(plugin_path)
    
    def _load_single_plugin(self, file_path: str) -> None:
        """加载单个插件文件"""
        try:
            module_name = os.path.splitext(os.path.basename(file_path))[0]
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, BasePlugin) and 
                    attr != BasePlugin):
                    plugin_instance = attr()
                    if plugin_instance.metadata.enabled:
                        self.register_plugin(plugin_instance)
        except Exception as e:
            print(f"✗ 加载插件失败 {file_path}: {e}")
    
    async def execute_all(self, event: str, **kwargs) -> List[Dict[str, Any]]:
        """执行所有插件的某个事件"""
        results = []
        for name, plugin in self.plugins.items():
            if hasattr(plugin, event):
                try:
                    result = await getattr(plugin, event)(**kwargs)
                    if result:
                        results.append(result)
                except Exception as e:
                    print(f"✗ 插件执行失败 {name}: {e}")
        return results

plugin_manager = PluginManager()
