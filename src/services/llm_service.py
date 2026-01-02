"""
LLM 服务 - 提供大语言模型对话功能
"""
import logging
from typing import Optional, AsyncIterator, Union, Dict, Any
from ..core.config import Config
from ..core.logger import get_logger, get_system_logger
from ..core.error_codes import SystemError, SystemErrorInfo
from ..providers.llm.litellm_provider import LiteLLMProvider

logger = get_logger("LLM")


class LLMService:
    """LLM 服务主类"""
    
    def __init__(self, config: Config):
        """初始化 LLM 服务
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.llm_provider: Optional[LiteLLMProvider] = None
        self._initialize_provider()
    
    def _initialize_provider(self):
        """初始化 LLM 提供商"""
        sys_logger = get_system_logger()
        
        try:
            logger.info("[LLM服务] 初始化 LLM 提供商...")
            
            # 获取 LLM 配置
            llm_config = self.config.get('llm')
            if not llm_config:
                error_info = SystemErrorInfo(
                    SystemError.LLM_NOT_CONFIGURED,
                    details="配置文件中未找到 LLM 配置",
                    technical_info="config.yml: llm section missing"
                )
                sys_logger.log_error("LLM", error_info)
                logger.warning("[LLM服务] 未找到 LLM 配置，服务将不可用")
                return
            
            # 创建并初始化 LiteLLM 提供商
            self.llm_provider = LiteLLMProvider()
            success = self.llm_provider.initialize(llm_config)
            
            if success:
                logger.info("[LLM服务] LLM 提供商初始化成功")
                sys_logger.log_llm_event("LLM初始化成功", 
                                         provider=llm_config.get('provider'),
                                         model=llm_config.get('model'))
            else:
                error_info = SystemErrorInfo(
                    SystemError.LLM_SERVICE_UNAVAILABLE,
                    details="LLM 提供商初始化失败",
                    technical_info="Provider initialization returned False"
                )
                sys_logger.log_error("LLM", error_info)
                logger.error("[LLM服务] LLM 提供商初始化失败")
                self.llm_provider = None
                
        except Exception as e:
            error_info = SystemErrorInfo(
                SystemError.SYSTEM_INTERNAL_ERROR,
                details=f"初始化 LLM 提供商异常: {str(e)}",
                technical_info=f"{type(e).__name__}: {str(e)}"
            )
            sys_logger.log_error("LLM", error_info)
            logger.error(f"[LLM服务] 初始化 LLM 提供商异常: {e}")
            self.llm_provider = None
    
    def is_available(self) -> bool:
        """检查 LLM 服务是否可用"""
        return self.llm_provider is not None and self.llm_provider.is_available()
    
    async def chat(
        self,
        messages: list[Dict[str, str]],
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Union[str, AsyncIterator[str]]:
        """发送对话请求
        
        Args:
            messages: 消息列表，格式：
                [
                    {"role": "system", "content": "你是一个助手"},
                    {"role": "user", "content": "你好"},
                    {"role": "assistant", "content": "你好！有什么可以帮你的？"},
                    {"role": "user", "content": "..."}
                ]
            stream: 是否使用流式返回
            temperature: 温度参数（0-1），控制随机性
            max_tokens: 最大生成 token 数
            **kwargs: 其他参数
            
        Returns:
            如果 stream=True，返回 AsyncIterator[str]（流式生成）
            如果 stream=False，返回 str（完整响应）
            
        Raises:
            RuntimeError: 如果 LLM 服务不可用
        """
        sys_logger = get_system_logger()
        
        if not self.is_available():
            error_info = SystemErrorInfo(
                SystemError.LLM_SERVICE_UNAVAILABLE,
                details="LLM 服务不可用",
                technical_info="Service not initialized or provider unavailable"
            )
            sys_logger.log_error("LLM", error_info)
            raise RuntimeError("LLM 服务不可用，请检查配置")
        
        try:
            # 准备参数
            params = {
                'temperature': temperature,
                **kwargs
            }
            
            if max_tokens is not None:
                params['max_tokens'] = max_tokens
            
            # 调用 LLM 提供商
            logger.info(f"[LLM服务] 发送对话请求，消息数: {len(messages)}, 流式: {stream}")
            sys_logger.log_llm_event("发送对话请求", 
                                     messages_count=len(messages), 
                                     stream=stream,
                                     temperature=temperature)
            
            result = await self.llm_provider.chat(messages, stream=stream, **params)
            
            return result
            
        except Exception as e:
            # 根据异常类型确定错误码
            error_type = type(e).__name__
            error_msg = str(e)
            
            if "rate" in error_msg.lower() or "limit" in error_msg.lower():
                error_info = SystemErrorInfo(
                    SystemError.LLM_RATE_LIMIT,
                    details="请求频率超限",
                    technical_info=f"{error_type}: {error_msg}"
                )
            elif "auth" in error_msg.lower() or "401" in error_msg or "403" in error_msg:
                error_info = SystemErrorInfo(
                    SystemError.LLM_AUTH_FAILED,
                    details="认证失败",
                    technical_info=f"{error_type}: {error_msg}"
                )
            elif "timeout" in error_msg.lower():
                error_info = SystemErrorInfo(
                    SystemError.LLM_REQUEST_TIMEOUT,
                    details="请求超时",
                    technical_info=f"{error_type}: {error_msg}"
                )
            elif "quota" in error_msg.lower() or "balance" in error_msg.lower():
                error_info = SystemErrorInfo(
                    SystemError.LLM_QUOTA_EXCEEDED,
                    details="配额已用完",
                    technical_info=f"{error_type}: {error_msg}"
                )
            else:
                error_info = SystemErrorInfo(
                    SystemError.LLM_SERVICE_UNAVAILABLE,
                    details=f"对话请求失败: {error_msg}",
                    technical_info=f"{error_type}: {error_msg}"
                )
            
            sys_logger.log_error("LLM", error_info)
            logger.error(f"[LLM服务] 对话请求失败: {e}")
            raise
    
    async def simple_chat(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[str, AsyncIterator[str]]:
        """简化的单轮对话接口
        
        Args:
            user_message: 用户消息
            system_prompt: 系统提示（可选）
            stream: 是否使用流式返回
            **kwargs: 其他参数
            
        Returns:
            LLM 响应
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": user_message})
        
        return await self.chat(messages, stream=stream, **kwargs)
    
    def get_provider_info(self) -> Dict[str, Any]:
        """获取提供商信息
        
        Returns:
            包含提供商信息的字典
        """
        if not self.llm_provider:
            return {
                "available": False,
                "name": None,
                "model": None,
                "provider": None
            }
        
        llm_config = self.config.get('llm', {})
        return {
            "available": self.is_available(),
            "name": self.llm_provider.name,
            "model": llm_config.get('model'),
            "provider": llm_config.get('provider'),
            "max_context_tokens": llm_config.get('max_context_tokens')
        }

