# AI Agents 模块

## 📖 概述

`agents` 模块提供了一套专业的AI代理服务，每个Agent专注于特定的任务，拥有独立的提示词工程和业务逻辑。

## 🏗️ 架构设计

### 设计原则

1. **单一职责**：每个Agent专注一个特定任务
2. **统一接口**：所有Agent继承自 `BaseAgent`，提供一致的API
3. **独立封装**：Agent内部封装提示词工程和业务逻辑
4. **易于扩展**：添加新Agent只需继承BaseAgent并实现必要方法

### 目录结构

```
src/agents/
├── __init__.py          # 模块导出
├── README.md            # 本文档
├── base_agent.py        # 基础Agent抽象类
├── summary_agent.py     # 会议小结Agent
├── prompts/             # 提示词工程目录 ⭐
│   ├── __init__.py
│   ├── README.md        # 提示词工程文档
│   ├── prompt_loader.py # 提示词加载器
│   ├── summary_agent.yml # 会议小结提示词
│   └── template.yml     # 提示词模板
└── ...                  # 未来的其他Agent
```

## 🎯 现有 Agents

### 1. SummaryAgent - 会议小结生成

**功能**: 从会议记录中生成结构化、易读的小结

**特点**:
- 自动过滤已有的小结块（避免递归引用）
- 使用emoji作为视觉标记
- 支持流式和非流式输出
- **提示词从YAML文件加载**（位于 `prompts/summary_agent.yml`）
- 支持多个提示词变体（简洁版、详细版、英文版）

**使用示例**:

```python
from src.agents import SummaryAgent
from src.services.llm_service import LLMService

# 初始化
llm_service = LLMService(config)
summary_agent = SummaryAgent(llm_service)

# 非流式生成
summary = await summary_agent.generate_summary(
    content="会议记录内容...",
    stream=False
)

# 流式生成
async for chunk in summary_agent.generate_summary(
    content="会议记录内容...",
    stream=True
):
    print(chunk, end='', flush=True)
```

**API端点**: `/api/summary/generate`

## 🔧 创建新的 Agent

### 步骤1: 创建Agent类

创建新文件 `src/agents/your_agent.py`:

```python
from typing import AsyncIterator, Union
from .base_agent import BaseAgent


class YourAgent(BaseAgent):
    """你的Agent描述"""
    
    @property
    def name(self) -> str:
        return "YourAgent"
    
    @property
    def description(self) -> str:
        return "Agent的功能描述"
    
    def get_system_prompt(self) -> str:
        """返回精心设计的系统提示词"""
        return """你的提示词内容..."""
    
    def preprocess_input(self, input_text: str) -> str:
        """可选：预处理输入"""
        # 在这里清理、过滤、格式化输入
        return input_text
    
    def postprocess_output(self, output_text: str) -> str:
        """可选：后处理输出"""
        # 在这里清理、验证、格式化输出
        return output_text
    
    # 添加自定义方法
    async def your_custom_method(self, ...):
        """自定义的业务方法"""
        return await self.generate(...)
```

### 步骤2: 注册Agent

在 `src/agents/__init__.py` 中导出:

```python
from .your_agent import YourAgent

__all__ = ['SummaryAgent', 'YourAgent']
```

### 步骤3: 在API中使用

在 `src/api/server.py` 中:

```python
# 1. 导入
from src.agents import YourAgent

# 2. 添加全局变量
your_agent: Optional[YourAgent] = None

# 3. 在 setup_llm_service() 中初始化
def setup_llm_service():
    global llm_service, your_agent
    # ...
    if llm_service.is_available():
        your_agent = YourAgent(llm_service)
        logger.info(f"[API] {your_agent.name} 初始化完成")

# 4. 创建API端点
@app.post("/api/your-endpoint")
async def your_endpoint(request: YourRequest):
    if not your_agent or not your_agent.is_available():
        raise HTTPException(status_code=503, detail="服务不可用")
    
    result = await your_agent.generate(
        input_text=request.input,
        stream=request.stream
    )
    
    return {"result": result}
```

## 📋 BaseAgent API

### 核心方法

#### `generate(input_text, stream=False, **kwargs)`

生成响应的核心方法

**参数**:
- `input_text` (str): 输入文本
- `stream` (bool): 是否流式输出，默认False
- `**kwargs`: 其他参数（temperature, max_tokens等）

**返回**:
- 非流式: `str` - 完整响应文本
- 流式: `AsyncIterator[str]` - 文本片段流

### 需要实现的方法

#### `name` (property)

Agent的名称，用于日志和标识

#### `description` (property)

Agent的功能描述

#### `get_system_prompt()`

返回系统提示词文本。这是Agent的核心，定义了Agent的行为和输出格式。

### 可选重写的方法

#### `preprocess_input(input_text)`

预处理输入文本，可以用于：
- 清理和验证输入
- 过滤不需要的内容
- 格式化输入

#### `postprocess_output(output_text)`

后处理输出文本，可以用于：
- 清理LLM输出
- 验证格式
- 添加额外信息

## 🎨 提示词工程最佳实践

### 1. 结构清晰

```python
def get_system_prompt(self) -> str:
    return """你是[角色定位]。你的任务是[任务描述]。

输出格式和要求：

1. [要求1]
   - 具体说明
   - 举例

2. [要求2]
   - 具体说明
   - 举例

输出示例：

[具体的示例]

请直接输出结果，不要有其他说明。"""
```

### 2. 正向引导

✅ **好**: "使用emoji图标作为视觉标记"
❌ **差**: "不要使用markdown格式"

正向说明要做什么，比否定式更有效。

### 3. 具体示例

提供清晰的输出示例，让LLM理解期望的格式。

### 4. 明确约束

如果有特定要求（如字数限制、格式要求），明确说明。

## 🚀 未来扩展

可以考虑添加的Agent:

1. **TranslationAgent** - 多语言翻译
2. **AnalysisAgent** - 数据分析和洞察
3. **ActionItemAgent** - 待办事项提取
4. **QuestionAnswerAgent** - 问答系统
5. **CodeReviewAgent** - 代码审查
6. **EmailDraftAgent** - 邮件草稿生成

## 📝 开发规范

1. **命名规范**: Agent类名使用PascalCase，以Agent结尾
2. **文档字符串**: 所有方法都要有清晰的docstring
3. **日志记录**: 使用self.logger记录关键操作
4. **错误处理**: 明确的异常类型和错误信息
5. **测试**: 为每个Agent编写单元测试（推荐）

## 🔍 调试技巧

### 查看Agent生成的提示词

```python
agent = SummaryAgent(llm_service)
print(agent.get_system_prompt())
```

### 测试预处理和后处理

```python
processed_input = agent.preprocess_input("原始输入")
print(f"处理后: {processed_input}")

processed_output = agent.postprocess_output("原始输出")
print(f"处理后: {processed_output}")
```

### 启用详细日志

```python
import logging
logging.getLogger('src.agents').setLevel(logging.DEBUG)
```

## 📚 参考资料

- [LangChain Agents](https://python.langchain.com/docs/modules/agents/)
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)
- [Prompt Engineering Guide](https://www.promptingguide.ai/)

---

**维护者**: 深圳王哥 & AI  
**最后更新**: 2026-01-02

