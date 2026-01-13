"""
TTS 提供商基类实现
"""
from typing import Dict, Any, Optional, AsyncIterator
from ...core.base import TTSProvider


class BaseTTSProvider(TTSProvider):
    """TTS 提供商基类，提供通用功能"""
    
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
    
    async def synthesize(self, text: str, language: str = "zh-CN", voice: Optional[str] = None,
                        speed: float = 1.0, **kwargs) -> bytes:
        """合成语音，子类必须实现"""
        raise NotImplementedError("Subclass must implement synthesize method")
    
    async def synthesize_stream(self, text: str, language: str = "zh-CN", voice: Optional[str] = None,
                               speed: float = 1.0, **kwargs) -> AsyncIterator[bytes]:
        """流式合成语音，子类必须实现"""
        raise NotImplementedError("Subclass must implement synthesize_stream method")
    
    async def list_voices(self, language: Optional[str] = None) -> list[Dict[str, Any]]:
        """列出可用的音色，子类必须实现"""
        raise NotImplementedError("Subclass must implement list_voices method")
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self._initialized
