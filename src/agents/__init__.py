"""
AI Agents 模块

提供各种专业的AI代理服务，如：
- SummaryAgent: 会议小结生成
- SmartChatAgent: 智能对话助手（支持知识库RAG）
- 未来可以添加更多agent...
"""

from .summary_agent import SummaryAgent
from .smart_chat_agent import SmartChatAgent

__all__ = ['SummaryAgent', 'SmartChatAgent']

