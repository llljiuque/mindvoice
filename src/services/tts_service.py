"""
TTS 服务 - 提供文本转语音功能
作为MindVoice的独立服务模块，支持通过配置切换不同的TTS提供商
"""
import logging
from typing import Optional, AsyncIterator, Dict, Any, Type
from ..core.config import Config
from ..core.logger import get_logger, get_system_logger
from ..core.error_codes import SystemError, SystemErrorInfo
from ..core.base import TTSProvider
from ..providers.tts import get_tts_provider_class, list_available_tts_providers

logger = get_logger("TTS")


class TTSService:
    """TTS 服务主类"""
    
    def __init__(self, config: Config):
        """初始化 TTS 服务
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.tts_provider: Optional[TTSProvider] = None
        self._provider_name: Optional[str] = None
        self._initialize_provider()
    
    def _initialize_provider(self):
        """初始化 TTS 提供商"""
        sys_logger = get_system_logger()
        
        try:
            logger.info("[TTS服务] 初始化 TTS 提供商...")
            
            # 获取 TTS 配置
            tts_config = self.config.get('tts')
            if not tts_config:
                error_info = SystemErrorInfo(
                    SystemError.SYSTEM_INTERNAL_ERROR,
                    details="配置文件中未找到 TTS 配置",
                    technical_info="config.yml: tts section missing"
                )
                sys_logger.log_error("TTS", error_info)
                logger.warning("[TTS服务] 未找到 TTS 配置，服务将不可用")
                return
            
            # 检查是否启用 TTS
            if not tts_config.get('enabled', True):
                logger.info("[TTS服务] TTS 功能已禁用")
                return
            
            # 获取提供商名称
            provider_name = tts_config.get('provider', 'cosyvoice3')
            self._provider_name = provider_name
            
            # 动态加载TTS提供商类
            provider_class = get_tts_provider_class(provider_name)
            if not provider_class:
                error_info = SystemErrorInfo(
                    SystemError.SYSTEM_INTERNAL_ERROR,
                    details=f"不支持的 TTS 提供商: {provider_name}",
                    technical_info=f"Provider '{provider_name}' not found"
                )
                sys_logger.log_error("TTS", error_info)
                logger.warning(f"[TTS服务] 不支持的 TTS 提供商: {provider_name}")
                logger.info(f"[TTS服务] 可用的提供商: {', '.join(list_available_tts_providers())}")
                return
            
            # 创建提供商实例
            try:
                self.tts_provider = provider_class()
                logger.info(f"[TTS服务] 已创建 {provider_name} 提供商实例")
            except Exception as e:
                error_info = SystemErrorInfo(
                    SystemError.SYSTEM_INTERNAL_ERROR,
                    details=f"创建 TTS 提供商实例失败: {str(e)}",
                    technical_info=f"{type(e).__name__}: {str(e)}"
                )
                sys_logger.log_error("TTS", error_info)
                logger.error(f"[TTS服务] 创建 {provider_name} 提供商实例失败: {e}", exc_info=True)
                return
            
            # 获取提供商特定配置（使用提供商名称作为键）
            provider_config = tts_config.get(provider_name, {})
            
            # 初始化提供商
            success = self.tts_provider.initialize(provider_config)
            
            if success:
                logger.info(f"[TTS服务] TTS 提供商 ({provider_name}) 初始化成功")
                sys_logger.log_error("TTS", SystemErrorInfo(
                    SystemError.SYSTEM_INTERNAL_ERROR,
                    details=f"TTS提供商初始化成功",
                    technical_info=f"Provider: {provider_name}"
                ))
            else:
                error_info = SystemErrorInfo(
                    SystemError.SYSTEM_INTERNAL_ERROR,
                    details="TTS 提供商初始化失败",
                    technical_info="Provider initialization returned False"
                )
                sys_logger.log_error("TTS", error_info)
                logger.error("[TTS服务] TTS 提供商初始化失败")
                self.tts_provider = None
                
        except Exception as e:
            error_info = SystemErrorInfo(
                SystemError.SYSTEM_INTERNAL_ERROR,
                details=f"初始化 TTS 提供商异常: {str(e)}",
                technical_info=f"{type(e).__name__}: {str(e)}"
            )
            sys_logger.log_error("TTS", error_info)
            logger.error(f"[TTS服务] 初始化 TTS 提供商异常: {e}", exc_info=True)
            self.tts_provider = None
    
    def is_available(self) -> bool:
        """检查 TTS 服务是否可用"""
        return self.tts_provider is not None and self.tts_provider.is_available()
    
    async def synthesize(
        self,
        text: str,
        language: str = "zh-CN",
        voice: Optional[str] = None,
        speed: float = 1.0,
        **kwargs
    ) -> bytes:
        """合成语音
        
        Args:
            text: 要合成的文本
            language: 语言代码（默认: zh-CN）
            voice: 音色ID（可选）
            speed: 语速（默认: 1.0，范围: 0.5-2.0）
            **kwargs: 其他参数
            
        Returns:
            音频数据（WAV 格式字节流）
        """
        if not self.is_available():
            raise RuntimeError("TTS service is not available")
        
        # 文本预处理
        text = self._preprocess_text(text)
        
        # 参数验证和默认值设置
        # 使用当前提供商名称获取默认配置
        provider_name = self._provider_name or 'cosyvoice3'
        language = language or self.config.get(f'tts.{provider_name}.default_language', 'zh-CN')
        voice = voice or self.config.get(f'tts.{provider_name}.default_voice')
        speed = max(0.5, min(2.0, speed))  # 限制在 0.5-2.0 范围内
        
        # 调用提供商合成语音
        try:
            audio_data = await self.tts_provider.synthesize(
                text=text,
                language=language,
                voice=voice,
                speed=speed,
                **kwargs
            )
            logger.debug(f"[TTS服务] 成功合成 {len(text)} 个字符的语音")
            return audio_data
        except Exception as e:
            logger.error(f"[TTS服务] 语音合成失败: {e}", exc_info=True)
            raise
    
    async def synthesize_stream(
        self,
        text: str,
        language: str = "zh-CN",
        voice: Optional[str] = None,
        speed: float = 1.0,
        **kwargs
    ) -> AsyncIterator[bytes]:
        """流式合成语音
        
        Args:
            text: 要合成的文本
            language: 语言代码（默认: zh-CN）
            voice: 音色ID（可选）
            speed: 语速（默认: 1.0）
            **kwargs: 其他参数
            
        Yields:
            音频数据块（字节流）
        """
        if not self.is_available():
            raise RuntimeError("TTS service is not available")
        
        # 文本预处理
        text = self._preprocess_text(text)
        
        # 参数验证和默认值设置
        # 使用当前提供商名称获取默认配置
        provider_name = self._provider_name or 'cosyvoice3'
        language = language or self.config.get(f'tts.{provider_name}.default_language', 'zh-CN')
        voice = voice or self.config.get(f'tts.{provider_name}.default_voice')
        speed = max(0.5, min(2.0, speed))
        
        # 获取流式合成配置
        stream_config = self.config.get(f'tts.{provider_name}.stream', {})
        chunk_size = stream_config.get('chunk_size', 50)
        kwargs['chunk_size'] = chunk_size
        
        # 调用提供商流式合成
        try:
            async for chunk in self.tts_provider.synthesize_stream(
                text=text,
                language=language,
                voice=voice,
                speed=speed,
                **kwargs
            ):
                yield chunk
        except Exception as e:
            logger.error(f"[TTS服务] 流式语音合成失败: {e}", exc_info=True)
            raise
    
    async def list_voices(self, language: Optional[str] = None) -> list[Dict[str, Any]]:
        """列出可用的音色
        
        Args:
            language: 语言代码（可选，过滤特定语言的音色）
            
        Returns:
            音色列表
        """
        if not self.is_available():
            return []
        
        try:
            voices = await self.tts_provider.list_voices(language=language)
            return voices
        except Exception as e:
            logger.error(f"[TTS服务] 获取音色列表失败: {e}", exc_info=True)
            return []
    
    def _preprocess_text(self, text: str) -> str:
        """文本预处理
        
        Args:
            text: 原始文本
            
        Returns:
            处理后的文本
        """
        if not text:
            return ""
        
        # 去除首尾空白
        text = text.strip()
        
        # 统一换行符
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # 清理多余空白
        import re
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    def get_provider_name(self) -> Optional[str]:
        """获取当前使用的TTS提供商名称"""
        return self._provider_name
    
    def reload_provider(self):
        """重新加载TTS提供商（用于配置更改后）"""
        logger.info("[TTS服务] 重新加载TTS提供商...")
        self.tts_provider = None
        self._provider_name = None
        self._initialize_provider()
