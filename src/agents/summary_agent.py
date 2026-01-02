"""
会议小结Agent

专门用于生成会议记录和笔记的结构化小结
"""
from typing import AsyncIterator, Union, Optional, Dict, Any
import re
from .base_agent import BaseAgent
from .prompts import PromptLoader


class SummaryAgent(BaseAgent):
    """会议小结生成Agent
    
    功能：
    - 从会议记录中提取核心信息
    - 生成结构化、易读的小结
    - 使用emoji作为视觉标记
    - 支持流式和非流式输出
    """
    
    # 小结块的标记（用于识别和过滤）
    SUMMARY_MARKER_START = "[SUMMARY_BLOCK_START]"
    SUMMARY_MARKER_END = "[SUMMARY_BLOCK_END]"
    
    def __init__(self, llm_service, config: Optional[Dict[str, Any]] = None):
        """初始化SummaryAgent
        
        Args:
            llm_service: LLM服务实例
            config: Agent配置（可选）
        """
        super().__init__(llm_service, config)
        
        # 加载提示词配置
        self.prompt_config = PromptLoader.load('summary_agent')
        
        # 如果config中指定了variant，使用对应的变体
        variant = config.get('prompt_variant') if config else None
        if variant:
            self.prompt_config = PromptLoader.load('summary_agent', variant=variant)
            self.logger.info(f"[{self.name}] 使用提示词变体: {variant}")
        
        # 使用提示词配置中的默认参数（可被config覆盖）
        prompt_params = self.prompt_config.get('parameters', {})
        self.config = {**prompt_params, **(config or {})}
    
    @property
    def name(self) -> str:
        return self.prompt_config['metadata']['name']
    
    @property
    def description(self) -> str:
        return self.prompt_config['metadata']['description']
    
    def get_system_prompt(self) -> str:
        """获取系统提示词
        
        从YAML配置文件加载，而不是硬编码
        """
        return self.prompt_config['system_prompt']
    
    def preprocess_input(self, input_text: str) -> str:
        """预处理输入文本
        
        功能：
        1. 移除已有的小结块（避免递归引用）
        2. 清理多余的空白字符
        3. 保持原始内容的结构
        
        Args:
            input_text: 原始输入文本
            
        Returns:
            清理后的文本
        """
        # 移除小结块标记及其内容
        pattern = re.escape(self.SUMMARY_MARKER_START) + r'[\s\S]*?' + re.escape(self.SUMMARY_MARKER_END)
        cleaned = re.sub(pattern, '', input_text)
        
        # 清理多余的空行（保留段落结构）
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        # 去除首尾空白
        cleaned = cleaned.strip()
        
        if not cleaned:
            raise ValueError("输入内容为空或仅包含小结块")
        
        self.logger.info(f"[{self.name}] 预处理完成，原始长度={len(input_text)}, 清理后长度={len(cleaned)}")
        return cleaned
    
    def postprocess_output(self, output_text: str) -> str:
        """后处理输出文本
        
        功能：
        1. 清理可能的格式问题
        2. 确保段落结构清晰
        
        Args:
            output_text: 原始输出文本
            
        Returns:
            优化后的文本
        """
        # 去除可能的markdown标记（以防LLM不遵守指令）
        cleaned = output_text.strip()
        
        # 移除可能的开场白和结束语
        prefixes_to_remove = [
            "好的，", "明白了，", "根据会议记录，", "以下是", "这是",
            "会议小结如下", "小结内容", "内容如下"
        ]
        for prefix in prefixes_to_remove:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].lstrip('：:,，')
        
        # 移除可能的结束语
        suffixes_to_remove = [
            "希望这个小结对您有帮助", "以上就是", "如有需要", "祝好"
        ]
        for suffix in suffixes_to_remove:
            if suffix in cleaned:
                cleaned = cleaned.split(suffix)[0]
        
        return cleaned.strip()
    
    async def generate_summary(
        self,
        content: str,
        stream: bool = False,
        **kwargs
    ) -> Union[str, AsyncIterator[str]]:
        """生成会议小结
        
        这是一个语义化的别名方法，内部调用generate()
        
        Args:
            content: 会议记录内容
            stream: 是否使用流式输出
            **kwargs: 其他参数
            
        Returns:
            小结内容（字符串或流式迭代器）
        """
        return await self.generate(content, stream=stream, **kwargs)
    
    @staticmethod
    def wrap_summary_for_storage(summary: str) -> str:
        """为小结添加存储标记
        
        用于在保存到数据库时标识这是一个小结块，
        这样在加载时可以保持完整性，不被拆分
        
        Args:
            summary: 小结内容
            
        Returns:
            添加标记后的文本
        """
        return f"{SummaryAgent.SUMMARY_MARKER_START}{summary}{SummaryAgent.SUMMARY_MARKER_END}"
    
    @staticmethod
    def is_summary_block(text: str) -> bool:
        """判断文本是否是小结块
        
        Args:
            text: 待判断的文本
            
        Returns:
            是否是小结块
        """
        return (SummaryAgent.SUMMARY_MARKER_START in text and 
                SummaryAgent.SUMMARY_MARKER_END in text)

