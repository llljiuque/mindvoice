"""
LLM 提供商基类实现
"""
from typing import Dict, Any, AsyncIterator, Union
from ...core.base import LLMProvider


class BaseLLMProvider(LLMProvider):
    """LLM 提供商基类，提供通用功能"""
    
    def __init__(self):
        self._config: Dict[str, Any] = {}
        self._initialized = False
    
    @property
    def name(self) -> str:
        """提供商名称，子类应重写"""
        return "base"
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化提供商"""
        self._config = config
        self._initialized = True
        return True
    
    async def chat(self, messages: list[Dict[str, str]], stream: bool = False, **kwargs) -> Union[str, AsyncIterator[str]]:
        """对话接口，子类必须实现"""
        raise NotImplementedError("Subclass must implement chat method")
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self._initialized

