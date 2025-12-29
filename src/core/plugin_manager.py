"""
插件管理器 - 支持动态加载 ASR 和存储提供商
"""
import importlib
import inspect
from typing import Dict, Type, Optional
from pathlib import Path

from .base import ASRProvider, StorageProvider


class PluginManager:
    """插件管理器"""
    
    def __init__(self):
        self._asr_providers: Dict[str, Type[ASRProvider]] = {}
        self._storage_providers: Dict[str, Type[StorageProvider]] = {}
        self._loaded_modules = {}
    
    def register_asr_provider(self, name: str, provider_class: Type[ASRProvider]):
        """注册 ASR 提供商
        
        Args:
            name: 提供商名称
            provider_class: 提供商类
        """
        if not issubclass(provider_class, ASRProvider):
            raise ValueError(f"{provider_class} must be a subclass of ASRProvider")
        self._asr_providers[name] = provider_class
    
    def register_storage_provider(self, name: str, provider_class: Type[StorageProvider]):
        """注册存储提供商
        
        Args:
            name: 提供商名称
            provider_class: 提供商类
        """
        if not issubclass(provider_class, StorageProvider):
            raise ValueError(f"{provider_class} must be a subclass of StorageProvider")
        self._storage_providers[name] = provider_class
    
    def load_plugin_module(self, module_path: str):
        """动态加载插件模块
        
        Args:
            module_path: 模块路径（如 'src.providers.asr.baidu'）
        """
        if module_path in self._loaded_modules:
            return
        
        try:
            module = importlib.import_module(module_path)
            self._loaded_modules[module_path] = module
            
            # 自动发现并注册提供商
            for name, obj in inspect.getmembers(module):
                # 跳过基类和抽象类
                if (inspect.isclass(obj) and 
                    obj != ASRProvider and 
                    issubclass(obj, ASRProvider) and
                    not inspect.isabstract(obj) and
                    not name.startswith('Base')):
                    provider_name = getattr(obj, 'PROVIDER_NAME', name.lower())
                    self.register_asr_provider(provider_name, obj)
                elif (inspect.isclass(obj) and 
                      obj != StorageProvider and 
                      issubclass(obj, StorageProvider) and
                      not inspect.isabstract(obj) and
                      not name.startswith('Base')):
                    provider_name = getattr(obj, 'PROVIDER_NAME', name.lower())
                    self.register_storage_provider(provider_name, obj)
        except Exception as e:
            print(f"Failed to load plugin {module_path}: {e}")
    
    def get_asr_provider(self, name: str) -> Optional[Type[ASRProvider]]:
        """获取 ASR 提供商类"""
        return self._asr_providers.get(name)
    
    def get_storage_provider(self, name: str) -> Optional[Type[StorageProvider]]:
        """获取存储提供商类"""
        return self._storage_providers.get(name)
    
    def list_asr_providers(self) -> list[str]:
        """列出所有已注册的 ASR 提供商"""
        return list(self._asr_providers.keys())
    
    def list_storage_providers(self) -> list[str]:
        """列出所有已注册的存储提供商"""
        return list(self._storage_providers.keys())
    
    def create_asr_instance(self, name: str, config: Dict) -> Optional[ASRProvider]:
        """创建 ASR 提供商实例
        
        Args:
            name: 提供商名称
            config: 配置字典
            
        Returns:
            ASR 提供商实例
        """
        provider_class = self.get_asr_provider(name)
        if provider_class is None:
            return None
        
        try:
            instance = provider_class()
            if instance.initialize(config):
                return instance
        except Exception as e:
            print(f"Failed to create ASR provider {name}: {e}")
        
        return None
    
    def create_storage_instance(self, name: str, config: Dict) -> Optional[StorageProvider]:
        """创建存储提供商实例
        
        Args:
            name: 提供商名称
            config: 配置字典
            
        Returns:
            存储提供商实例
        """
        provider_class = self.get_storage_provider(name)
        if provider_class is None:
            return None
        
        try:
            instance = provider_class()
            if hasattr(instance, 'initialize'):
                if not instance.initialize(config):
                    return None
            return instance
        except Exception as e:
            print(f"Failed to create storage provider {name}: {e}")
        
        return None
