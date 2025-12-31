# LLM 集成文档

本文档介绍如何使用语音桌面助手的 LLM（大语言模型）功能。

## 概述

语音桌面助手已集成 [LiteLLM](https://github.com/BerriAI/litellm)，支持统一调用多种 LLM 服务，包括：

- OpenAI、Azure OpenAI
- Anthropic (Claude)
- Google (Gemini)
- 国内厂商：通义千问、文心一言、智谱 ChatGLM 等
- 任何兼容 OpenAI API 的服务

## 配置

### 1. 安装依赖

```bash
# 激活虚拟环境
source venv/bin/activate

# 安装 LiteLLM
pip install litellm
```

### 2. 配置 LLM

编辑项目根目录的 `config.yml` 文件，添加 LLM 配置：

```yaml
llm:
  provider: perfxcloud-专线  # 服务提供商
  api_key: your-api-key-here  # API 密钥
  base_url: https://deepseek.perfxlab.cn/v1  # API 端点
  model: Qwen3-Next-80B-Instruct  # 模型名称
  max_context_tokens: 128000  # 最大上下文长度
```

**配置说明：**

- `provider`: 提供商标识（用于日志和管理）
- `api_key`: API 访问密钥
- `base_url`: API 端点地址（可选，用于自定义服务）
- `model`: 要使用的模型名称
- `max_context_tokens`: 模型的最大上下文长度

### 3. 配置示例

#### 使用 OpenAI

```yaml
llm:
  provider: openai
  api_key: sk-xxx
  model: gpt-4
  max_context_tokens: 8192
```

#### 使用通义千问

```yaml
llm:
  provider: alibaba
  api_key: your-key
  base_url: https://dashscope.aliyuncs.com/api/v1
  model: qwen-turbo
  max_context_tokens: 8192
```

#### 使用自定义端点（兼容 OpenAI API）

```yaml
llm:
  provider: custom
  api_key: your-key
  base_url: https://your-endpoint.com/v1
  model: your-model-name
  max_context_tokens: 128000
```

## 使用方法

### 方式一：通过 API 调用

启动 API 服务器：

```bash
python -m src.api.server
```

#### 1. 检查 LLM 服务状态

```bash
curl http://localhost:8765/api/llm/info
```

响应示例：
```json
{
  "available": true,
  "name": "litellm",
  "model": "Qwen3-Next-80B-Instruct",
  "provider": "perfxcloud-专线",
  "max_context_tokens": 128000
}
```

#### 2. 简单对话（单轮）

```bash
curl -X POST http://localhost:8765/api/llm/simple-chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你好，请介绍一下你自己",
    "system_prompt": "你是一个友好的AI助手",
    "temperature": 0.7
  }'
```

响应示例：
```json
{
  "success": true,
  "message": "你好！我是一个AI助手，很高兴为您服务...",
  "error": null
}
```

#### 3. 多轮对话

```bash
curl -X POST http://localhost:8765/api/llm/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "system", "content": "你是一个数学老师"},
      {"role": "user", "content": "1+1等于几？"},
      {"role": "assistant", "content": "1+1等于2"},
      {"role": "user", "content": "那2+2呢？"}
    ],
    "temperature": 0.3,
    "max_tokens": 1000
  }'
```

### 方式二：通过 Python 代码调用

```python
import asyncio
from src.core.config import Config
from src.services.llm_service import LLMService

async def main():
    # 初始化服务
    config = Config()
    llm_service = LLMService(config)
    
    # 检查服务是否可用
    if not llm_service.is_available():
        print("LLM 服务不可用")
        return
    
    # 简单对话
    response = await llm_service.simple_chat(
        user_message="你好！",
        system_prompt="你是一个友好的助手"
    )
    print(f"助手: {response}")
    
    # 多轮对话
    messages = [
        {"role": "system", "content": "你是一个助手"},
        {"role": "user", "content": "你好"}
    ]
    response = await llm_service.chat(messages=messages)
    print(f"助手: {response}")
    
    # 流式输出
    stream = await llm_service.simple_chat(
        user_message="讲一个故事",
        stream=True
    )
    async for chunk in stream:
        print(chunk, end="", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
```

### 方式三：运行测试脚本

项目提供了一个测试脚本，可以快速验证 LLM 集成是否正常：

```bash
# 激活虚拟环境
source venv/bin/activate

# 运行测试
python test_llm.py
```

测试脚本会：
1. 检查配置
2. 初始化 LLM 服务
3. 测试简单对话
4. 测试多轮对话
5. 测试流式输出

## API 参考

### GET /api/llm/info

获取 LLM 服务信息。

**响应：**
```typescript
{
  available: boolean;
  name?: string;
  model?: string;
  provider?: string;
  max_context_tokens?: number;
}
```

### POST /api/llm/simple-chat

简单的单轮对话接口。

**请求：**
```typescript
{
  message: string;              // 用户消息
  system_prompt?: string;       // 系统提示（可选）
  temperature?: number;         // 温度参数 0-2，默认 0.7
  max_tokens?: number;          // 最大生成 token 数（可选）
}
```

**响应：**
```typescript
{
  success: boolean;
  message?: string;   // LLM 响应（成功时）
  error?: string;     // 错误信息（失败时）
}
```

### POST /api/llm/chat

多轮对话接口。

**请求：**
```typescript
{
  messages: Array<{
    role: "system" | "user" | "assistant";
    content: string;
  }>;
  stream?: boolean;        // 是否流式返回，默认 false
  temperature?: number;    // 温度参数 0-2，默认 0.7
  max_tokens?: number;     // 最大生成 token 数（可选）
}
```

**响应：**
```typescript
{
  success: boolean;
  message?: string;   // LLM 响应（成功时）
  error?: string;     // 错误信息（失败时）
}
```

## 参数说明

### temperature（温度）

控制输出的随机性：
- `0.0`: 确定性输出，每次结果相同
- `0.3-0.5`: 较为保守，适合事实性任务
- `0.7-0.9`: 平衡创造性和准确性（推荐）
- `1.0-2.0`: 更有创造性，但可能不够准确

### max_tokens（最大 token 数）

限制生成的最大长度。如果不设置，模型会根据上下文自动决定。

## 故障排除

### 1. LLM 服务不可用

**问题：** API 返回 "LLM 服务不可用"

**解决方案：**
- 检查 `config.yml` 中是否配置了 `llm` 部分
- 确认已安装 `litellm`：`pip install litellm`
- 检查 API key 是否正确
- 查看服务器日志了解详细错误信息

### 2. API 连接失败

**问题：** 无法连接到 LLM 服务

**解决方案：**
- 检查 `base_url` 配置是否正确
- 确认网络连接正常
- 检查防火墙设置
- 验证 API key 是否有效

### 3. 模型不支持

**问题：** 收到 "模型不支持" 错误

**解决方案：**
- 确认模型名称正确（参考 LiteLLM 文档）
- 检查 API key 是否有权访问该模型
- 尝试使用其他模型

## 高级用法

### 自定义系统提示

通过设置系统提示，可以让 LLM 扮演特定角色：

```python
# 代码助手
response = await llm_service.simple_chat(
    user_message="如何在 Python 中读取文件？",
    system_prompt="你是一个专业的 Python 程序员，擅长用简洁的代码示例解释问题。"
)

# 翻译助手
response = await llm_service.simple_chat(
    user_message="Hello, how are you?",
    system_prompt="你是一个专业的翻译，将英文翻译成中文。只返回翻译结果，不要解释。"
)
```

### 维护对话上下文

```python
conversation = [
    {"role": "system", "content": "你是一个助手"}
]

# 第一轮
user_input = "我叫张三"
conversation.append({"role": "user", "content": user_input})
response = await llm_service.chat(messages=conversation)
conversation.append({"role": "assistant", "content": response})

# 第二轮
user_input = "我叫什么名字？"
conversation.append({"role": "user", "content": user_input})
response = await llm_service.chat(messages=conversation)
# LLM 应该回答：你叫张三
```

## 相关文档

- [LiteLLM 官方文档](https://docs.litellm.ai/)
- [支持的模型列表](https://docs.litellm.ai/docs/providers)
- [项目架构文档](./ARCHITECTURE.md)

## 更新日志

- **2025-12-31**: 初始版本，集成 LiteLLM 支持

