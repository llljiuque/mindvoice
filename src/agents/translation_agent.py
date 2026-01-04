"""
翻译Agent

专门用于语音笔记的多语言翻译
"""
from typing import AsyncIterator, Union, Optional, Dict, Any
from .base_agent import BaseAgent
from .prompts import PromptLoader


class TranslationAgent(BaseAgent):
    """翻译Agent
    
    功能：
    - 支持多语言对互译（中英日韩）
    - 保留原文的语气和风格
    - 针对ASR文本优化（处理口语化表达）
    - 支持流式和非流式输出
    """
    
    # 支持的语言对
    SUPPORTED_PAIRS = {
        'zh-en': ('中文', '英文'),
        'zh-ja': ('中文', '日文'),
        'zh-ko': ('中文', '韩文'),
        'en-zh': ('英文', '中文'),
        'ja-zh': ('日文', '中文'),
        'ko-zh': ('韩文', '中文'),
    }
    
    def __init__(self, llm_service, config: Optional[Dict[str, Any]] = None):
        """初始化TranslationAgent
        
        Args:
            llm_service: LLM服务实例
            config: Agent配置（可选）
        """
        super().__init__(llm_service, config)
        
        # 加载提示词配置
        self.prompt_config = PromptLoader.load('translation_agent')
        
        # 使用提示词配置中的默认参数
        prompt_params = self.prompt_config.get('parameters', {})
        self.config = {**prompt_params, **(config or {})}
    
    @property
    def name(self) -> str:
        return self.prompt_config['metadata']['name']
    
    @property
    def description(self) -> str:
        return self.prompt_config['metadata']['description']
    
    def get_system_prompt(self, source_lang: str, target_lang: str) -> str:
        """获取系统提示词（动态生成）
        
        Args:
            source_lang: 源语言
            target_lang: 目标语言
            
        Returns:
            系统提示词
        """
        base_prompt = self.prompt_config['system_prompt']
        
        # 获取语言名称
        pair_key = f"{source_lang}-{target_lang}"
        if pair_key not in self.SUPPORTED_PAIRS:
            raise ValueError(f"不支持的语言对: {pair_key}")
        
        source_name, target_name = self.SUPPORTED_PAIRS[pair_key]
        
        # 替换占位符
        return base_prompt.format(
            source_language=source_name,
            target_language=target_name
        )
    
    def preprocess_input(self, input_text: str) -> str:
        """预处理输入文本
        
        功能：
        1. 清理输入
        2. 检测空内容
        
        Args:
            input_text: 原始输入文本
            
        Returns:
            清理后的文本
        """
        cleaned = input_text.strip()
        
        if not cleaned:
            raise ValueError("输入内容为空")
        
        return cleaned
    
    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        stream: bool = False,
        **kwargs
    ) -> Union[str, AsyncIterator[str]]:
        """翻译文本
        
        Args:
            text: 待翻译文本
            source_lang: 源语言代码（zh/en/ja/ko）
            target_lang: 目标语言代码（zh/en/ja/ko）
            stream: 是否使用流式输出
            **kwargs: 其他参数
            
        Returns:
            翻译结果（字符串或流式迭代器）
        """
        # 预处理输入
        text = self.preprocess_input(text)
        
        # 获取针对该语言对的系统提示词
        system_prompt = self.get_system_prompt(source_lang, target_lang)
        
        # 调用LLM生成翻译
        self.logger.info(f"[{self.name}] 开始翻译: {source_lang} -> {target_lang}, 长度={len(text)}")
        
        # 临时覆盖系统提示词
        original_prompt = self.prompt_config.get('system_prompt')
        self.prompt_config['system_prompt'] = system_prompt
        
        try:
            result = await self.generate(text, stream=stream, **kwargs)
            return result
        finally:
            # 恢复原始提示词
            self.prompt_config['system_prompt'] = original_prompt
    
    async def batch_translate(
        self,
        texts: list[str],
        source_lang: str,
        target_lang: str,
        **kwargs
    ) -> list[str]:
        """批量翻译
        
        Args:
            texts: 待翻译文本列表
            source_lang: 源语言
            target_lang: 目标语言
            **kwargs: 其他参数
            
        Returns:
            翻译结果列表
        """
        results = []
        for text in texts:
            if not text.strip():
                results.append("")
                continue
            
            result = await self.translate(
                text, source_lang, target_lang, 
                stream=False, **kwargs
            )
            results.append(result)
        
        self.logger.info(f"[{self.name}] 批量翻译完成: {len(texts)} 条")
        return results

