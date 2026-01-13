"""
TTS 提供商模块
支持动态发现和加载TTS提供商
"""
from typing import Dict, Type, Optional
from ...core.base import TTSProvider
from .base_tts import BaseTTSProvider

# 导入所有可用的TTS提供商
try:
    from .cosyvoice3 import CosyVoice3Provider
    _AVAILABLE_PROVIDERS = {
        'cosyvoice3': CosyVoice3Provider,
    }
except ImportError:
    _AVAILABLE_PROVIDERS = {}

# 可以在这里添加更多提供商
# try:
#     from .openai_tts import OpenAITTSProvider
#     _AVAILABLE_PROVIDERS['openai'] = OpenAITTSProvider
# except ImportError:
#     pass

__all__ = ['BaseTTSProvider', 'CosyVoice3Provider', 'get_tts_provider_class', 'list_available_tts_providers']


def get_tts_provider_class(provider_name: str) -> Optional[Type[TTSProvider]]:
    """获取TTS提供商类
    
    Args:
        provider_name: 提供商名称（如 'cosyvoice3', 'openai'）
        
    Returns:
        TTS提供商类，如果不存在则返回None
    """
    return _AVAILABLE_PROVIDERS.get(provider_name.lower())


def list_available_tts_providers() -> list[str]:
    """列出所有可用的TTS提供商名称
    
    Returns:
        提供商名称列表
    """
    return list(_AVAILABLE_PROVIDERS.keys())


def register_tts_provider(name: str, provider_class: Type[TTSProvider]):
    """注册TTS提供商（用于动态加载）
    
    Args:
        name: 提供商名称
        provider_class: 提供商类
    """
    if not issubclass(provider_class, TTSProvider):
        raise ValueError(f"{provider_class} must be a subclass of TTSProvider")
    _AVAILABLE_PROVIDERS[name.lower()] = provider_class
