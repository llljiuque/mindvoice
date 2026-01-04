"""
SmartChat Agent

智能对话助手，支持上下文记忆和知识库检索增强(RAG)
"""
from typing import AsyncIterator, Union, Optional, Dict, Any, List
from .base_agent import BaseAgent
from .prompts import PromptLoader


class SmartChatAgent(BaseAgent):
    """SmartChat 智能对话 Agent
    
    功能：
    - 多轮对话管理（上下文记忆）
    - 知识库检索增强（RAG）
    - 多种对话模式（简洁/专业/创意）
    - 支持流式和非流式输出
    """
    
    def __init__(
        self, 
        llm_service, 
        knowledge_service=None,
        config: Optional[Dict[str, Any]] = None
    ):
        """初始化 SmartChatAgent
        
        Args:
            llm_service: LLM服务实例
            knowledge_service: 知识库服务实例（可选）
            config: Agent配置（可选）
        """
        super().__init__(llm_service, config)
        
        # 知识库服务
        self.knowledge_service = knowledge_service
        
        # 加载提示词配置
        self.prompt_config = PromptLoader.load('smart_chat_agent')
        
        # 如果config中指定了variant，使用对应的变体
        variant = config.get('prompt_variant') if config else None
        if variant and variant in self.prompt_config.get('variants', {}):
            variant_config = self.prompt_config['variants'][variant]
            # 合并变体配置
            self.prompt_config = {
                **self.prompt_config,
                'system_prompt': variant_config['system_prompt'],
                'parameters': {
                    **self.prompt_config['parameters'],
                    **variant_config['parameters']
                }
            }
            self.logger.info(f"[{self.name}] 使用提示词变体: {variant}")
        
        # 使用提示词配置中的默认参数（可被config覆盖）
        prompt_params = self.prompt_config.get('parameters', {})
        self.config = {**prompt_params, **(config or {})}
        
        # 对话历史管理
        self.conversation_history: List[Dict[str, str]] = []
        self.max_history_turns = config.get('max_history_turns', 10) if config else 10
    
    @property
    def name(self) -> str:
        return self.prompt_config['metadata']['name']
    
    @property
    def description(self) -> str:
        return self.prompt_config['metadata']['description']
    
    def get_system_prompt(self) -> str:
        """获取系统提示词
        
        从YAML配置文件加载
        """
        return self.prompt_config['system_prompt']
    
    def add_to_history(self, role: str, content: str):
        """添加消息到对话历史
        
        Args:
            role: 角色（user/assistant）
            content: 消息内容
        """
        self.conversation_history.append({
            'role': role,
            'content': content
        })
        
        # 限制历史长度（保留最近的N轮对话）
        if len(self.conversation_history) > self.max_history_turns * 2:
            # 每轮对话包含 user + assistant 两条消息
            self.conversation_history = self.conversation_history[-(self.max_history_turns * 2):]
            self.logger.info(f"[{self.name}] 对话历史已截断，保留最近 {self.max_history_turns} 轮")
    
    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []
        self.logger.info(f"[{self.name}] 对话历史已清空")
    
    def get_history_text(self) -> str:
        """获取格式化的对话历史文本
        
        Returns:
            格式化的历史文本
        """
        if not self.conversation_history:
            return ""
        
        history_lines = []
        for msg in self.conversation_history:
            role_name = "用户" if msg['role'] == 'user' else "助手"
            history_lines.append(f"{role_name}: {msg['content']}")
        
        history_text = "\n".join(history_lines)
        
        # 使用模板格式化
        template = self.prompt_config.get('conversation_history_template', "\n## 对话历史\n\n{history}\n---\n")
        return template.format(history=history_text)
    
    async def search_knowledge(
        self, 
        query: str, 
        top_k: int = 3
    ) -> Optional[str]:
        """从知识库检索相关内容
        
        Args:
            query: 查询文本
            top_k: 返回前K个结果
            
        Returns:
            格式化的知识库内容，如果没有结果返回None
        """
        if not self.knowledge_service:
            return None
        
        try:
            results = await self.knowledge_service.search(query, top_k=top_k)
            
            if not results:
                return None
            
            # 格式化知识库内容
            knowledge_lines = []
            for i, result in enumerate(results, 1):
                source = result.get('source', '未知来源')
                content = result.get('content', '')
                score = result.get('score', 0.0)
                
                knowledge_lines.append(f"### {i}. 来源: {source} (相关度: {score:.2f})")
                knowledge_lines.append(f"{content}")
                knowledge_lines.append("")  # 空行
            
            knowledge_content = "\n".join(knowledge_lines)
            
            # 使用模板格式化
            template = self.prompt_config.get('knowledge_context_template', 
                                             "\n## 相关知识库内容\n\n{knowledge_content}\n---\n")
            return template.format(knowledge_content=knowledge_content)
            
        except Exception as e:
            self.logger.error(f"[{self.name}] 知识库检索失败: {e}")
            return None
    
    def preprocess_input(self, input_text: str) -> str:
        """预处理输入文本
        
        功能：
        1. 清理输入
        2. 添加对话历史（如果有）
        3. 添加知识库内容（如果有）
        
        Args:
            input_text: 原始输入文本
            
        Returns:
            增强后的输入文本
        """
        # 基础清理
        cleaned = input_text.strip()
        
        if not cleaned:
            raise ValueError("输入内容为空")
        
        return cleaned
    
    async def chat(
        self,
        user_message: str,
        stream: bool = False,
        use_history: bool = True,
        use_knowledge: bool = True,
        knowledge_top_k: int = 3,
        **kwargs
    ) -> Union[str, AsyncIterator[str]]:
        """智能对话主方法
        
        Args:
            user_message: 用户消息
            stream: 是否流式输出
            use_history: 是否使用对话历史
            use_knowledge: 是否检索知识库
            knowledge_top_k: 知识库检索数量
            **kwargs: 其他参数
            
        Returns:
            助手回复（字符串或流式迭代器）
        """
        # 1. 预处理用户输入
        user_message = self.preprocess_input(user_message)
        
        # 2. 构建完整的输入
        enhanced_input = user_message
        
        # 2.1 添加对话历史
        if use_history and self.conversation_history:
            history_text = self.get_history_text()
            enhanced_input = history_text + "\n" + enhanced_input
        
        # 2.2 检索并添加知识库内容
        knowledge_text = None
        if use_knowledge and self.knowledge_service:
            knowledge_text = await self.search_knowledge(user_message, top_k=knowledge_top_k)
            if knowledge_text:
                enhanced_input = knowledge_text + "\n" + enhanced_input
                self.logger.info(f"[{self.name}] 已添加知识库上下文")
        
        # 3. 调用LLM生成回复
        self.logger.info(f"[{self.name}] 开始生成回复，历史={len(self.conversation_history)//2}轮，知识库={'有' if knowledge_text else '无'}")
        
        if stream:
            # 流式生成
            async def stream_chat():
                accumulated = ""
                result = await self.generate(enhanced_input, stream=True, **kwargs)
                
                async for chunk in result:
                    accumulated += chunk
                    yield chunk
                
                # 生成完成后，更新对话历史
                if use_history:
                    self.add_to_history('user', user_message)
                    self.add_to_history('assistant', accumulated)
                
                self.logger.info(f"[{self.name}] 流式对话完成，回复长度={len(accumulated)}")
            
            return stream_chat()
        else:
            # 非流式生成
            response = await self.generate(enhanced_input, stream=False, **kwargs)
            
            # 更新对话历史
            if use_history:
                self.add_to_history('user', user_message)
                self.add_to_history('assistant', response)
            
            self.logger.info(f"[{self.name}] 对话完成，回复长度={len(response)}")
            return response
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """获取当前对话状态摘要
        
        Returns:
            对话状态信息
        """
        return {
            'total_turns': len(self.conversation_history) // 2,
            'total_messages': len(self.conversation_history),
            'has_knowledge_service': self.knowledge_service is not None,
            'max_history_turns': self.max_history_turns
        }

