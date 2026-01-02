"""
基础Agent类

所有Agent的基类，定义统一的接口和行为
"""
from abc import ABC, abstractmethod
from typing import AsyncIterator, Union, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """基础Agent抽象类
    
    所有Agent都应该继承此类并实现必要的方法
    """
    
    def __init__(self, llm_service, config: Optional[Dict[str, Any]] = None):
        """初始化Agent
        
        Args:
            llm_service: LLM服务实例
            config: Agent配置（可选）
        """
        self.llm_service = llm_service
        self.config = config or {}
        self.logger = logger
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Agent名称"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Agent描述"""
        pass
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """获取系统提示词
        
        Returns:
            系统提示词文本
        """
        pass
    
    def preprocess_input(self, input_text: str) -> str:
        """预处理输入文本
        
        子类可以重写此方法来实现自定义的输入预处理
        
        Args:
            input_text: 原始输入文本
            
        Returns:
            预处理后的文本
        """
        return input_text
    
    def postprocess_output(self, output_text: str) -> str:
        """后处理输出文本
        
        子类可以重写此方法来实现自定义的输出后处理
        
        Args:
            output_text: 原始输出文本
            
        Returns:
            后处理后的文本
        """
        return output_text
    
    async def generate(
        self, 
        input_text: str, 
        stream: bool = False,
        **kwargs
    ) -> Union[str, AsyncIterator[str]]:
        """生成响应
        
        Args:
            input_text: 输入文本
            stream: 是否使用流式输出
            **kwargs: 其他参数（如temperature, max_tokens等）
            
        Returns:
            如果stream=False，返回完整响应文本
            如果stream=True，返回AsyncIterator[str]
        """
        if not self.llm_service or not self.llm_service.is_available():
            raise RuntimeError(f"{self.name} 不可用：LLM服务未初始化")
        
        # 预处理输入
        processed_input = self.preprocess_input(input_text)
        
        # 获取系统提示词
        system_prompt = self.get_system_prompt()
        
        # 合并配置
        generation_config = {
            'temperature': self.config.get('temperature', 0.5),
            'max_tokens': self.config.get('max_tokens', 2000),
            **kwargs  # 允许调用时覆盖配置
        }
        
        self.logger.info(f"[{self.name}] 开始生成，流式={stream}")
        
        try:
            if stream:
                # 流式生成
                async def stream_with_postprocess():
                    accumulated = ""
                    # 注意：需要 await 来获取 AsyncIterator
                    result = await self.llm_service.simple_chat(
                        user_message=processed_input,
                        system_prompt=system_prompt,
                        stream=True,
                        **generation_config
                    )
                    
                    async for chunk in result:
                        accumulated += chunk
                        yield chunk
                    
                    # 记录完整输出
                    self.logger.info(f"[{self.name}] 流式生成完成，总长度={len(accumulated)}")
                
                return stream_with_postprocess()
            else:
                # 非流式生成
                response = await self.llm_service.simple_chat(
                    user_message=processed_input,
                    system_prompt=system_prompt,
                    stream=False,
                    **generation_config
                )
                
                # 后处理输出
                processed_output = self.postprocess_output(response)
                
                self.logger.info(f"[{self.name}] 生成完成，长度={len(processed_output)}")
                return processed_output
                
        except Exception as e:
            self.logger.error(f"[{self.name}] 生成失败: {e}", exc_info=True)
            raise
    
    def is_available(self) -> bool:
        """检查Agent是否可用
        
        Returns:
            是否可用
        """
        return self.llm_service and self.llm_service.is_available()

