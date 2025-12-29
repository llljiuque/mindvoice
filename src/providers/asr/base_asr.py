"""
ASR 提供商基类实现示例
"""
from typing import Dict, Any
from ...core.base import ASRProvider


class BaseASRProvider(ASRProvider):
    """ASR 提供商基类，提供通用功能"""
    
    def __init__(self):
        self._config: Dict[str, Any] = {}
        self._initialized = False
    
    @property
    def name(self) -> str:
        """提供商名称，子类应重写"""
        return "base"
    
    @property
    def supported_languages(self) -> list[str]:
        """支持的语言列表，子类应重写"""
        return []
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化提供商"""
        self._config = config
        self._initialized = True
        return True
    
    def recognize(self, audio_data: bytes, language: str = "zh-CN", **kwargs) -> str:
        """识别音频，子类必须实现"""
        raise NotImplementedError("Subclass must implement recognize method")
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self._initialized
