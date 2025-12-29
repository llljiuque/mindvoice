"""
ASR 提供商示例实现（用于测试和参考）
"""
from typing import Dict, Any
from .base_asr import BaseASRProvider


class ExampleASRProvider(BaseASRProvider):
    """示例 ASR 提供商（仅用于测试）"""
    
    PROVIDER_NAME = "example"
    
    @property
    def name(self) -> str:
        return "example"
    
    @property
    def supported_languages(self) -> list[str]:
        return ["zh-CN", "en-US"]
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化示例提供商"""
        return super().initialize(config)
    
    def recognize(self, audio_data: bytes, language: str = "zh-CN", **kwargs) -> str:
        """识别音频（示例实现，返回固定文本）"""
        # 这是一个示例实现，实际应该调用真实的 ASR API
        return f"[示例识别结果] 语言: {language}, 音频长度: {len(audio_data)} 字节"
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self._initialized
