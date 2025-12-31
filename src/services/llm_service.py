"""
LLM 服务 - 提供大语言模型对话功能
"""
import logging
from typing import Optional, AsyncIterator, Union, Dict, Any
from ..core.config import Config
from ..providers.llm.litellm_provider import LiteLLMProvider

logger = logging.getLogger(__name__)


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
        try:
            logger.info("[LLM服务] 初始化 LLM 提供商...")
            
            # 获取 LLM 配置
            llm_config = self.config.get('llm')
            if not llm_config:
                logger.warning("[LLM服务] 未找到 LLM 配置，服务将不可用")
                return
            
            # 创建并初始化 LiteLLM 提供商
            self.llm_provider = LiteLLMProvider()
            success = self.llm_provider.initialize(llm_config)
            
            if success:
                logger.info("[LLM服务] LLM 提供商初始化成功")
            else:
                logger.error("[LLM服务] LLM 提供商初始化失败")
                self.llm_provider = None
                
        except Exception as e:
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
        if not self.is_available():
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
            result = await self.llm_provider.chat(messages, stream=stream, **params)
            
            return result
            
        except Exception as e:
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

