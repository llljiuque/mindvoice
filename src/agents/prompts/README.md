# Prompt Engineering - 提示词工程

## 📖 概述

本目录集中管理所有Agent的提示词，采用YAML格式存储，方便维护和版本控制。

## 📁 目录结构

```
prompts/
├── README.md              # 本文档
├── prompt_loader.py       # 提示词加载器
├── summary_agent.yml      # 会议小结Agent提示词
└── ...                    # 其他Agent提示词
```

## 📝 YAML格式规范

### 基本结构

```yaml
# 提示词元数据
metadata:
  name: "Agent名称"
  version: "1.0.0"
  author: "作者"
  updated: "2026-01-02"
  description: "提示词描述"

# 默认参数
parameters:
  temperature: 0.5
  max_tokens: 2000
  top_p: 0.9

# 系统提示词（核心内容）
system_prompt: |
  你的提示词内容...
  支持多行
  保持缩进和格式

# 可选：提示词变体（用于A/B测试）
variants:
  formal:
    system_prompt: |
      正式版本的提示词...
  
  casual:
    system_prompt: |
      轻松版本的提示词...

# 可选：示例输入输出
examples:
  - input: "示例输入1"
    output: "期望输出1"
  - input: "示例输入2"
    output: "期望输出2"
```

### 字段说明

#### metadata（必需）
- `name`: Agent名称
- `version`: 版本号（遵循语义化版本）
- `author`: 作者
- `updated`: 最后更新日期
- `description`: 简短描述

#### parameters（可选）
默认的生成参数，可以在调用时覆盖

#### system_prompt（必需）
核心提示词内容，使用 `|` 或 `>` 标记多行文本

#### variants（可选）
提示词的不同变体，用于：
- A/B测试
- 不同场景（正式/轻松）
- 多语言版本

#### examples（可选）
示例输入输出，用于：
- 文档说明
- 单元测试
- 质量评估

## 🔧 使用方法

### 在Agent中使用

```python
from .prompts.prompt_loader import PromptLoader

class YourAgent(BaseAgent):
    def __init__(self, llm_service, config=None):
        super().__init__(llm_service, config)
        # 加载提示词
        self.prompt_config = PromptLoader.load('your_agent')
    
    def get_system_prompt(self) -> str:
        # 返回默认提示词
        return self.prompt_config['system_prompt']
    
    def get_variant_prompt(self, variant: str) -> str:
        # 返回特定变体
        return self.prompt_config['variants'][variant]['system_prompt']
```

### 在代码外修改提示词

1. 直接编辑YAML文件
2. 无需重启程序（如果支持热加载）
3. 版本控制友好

## 📋 提示词开发流程

### 1. 创建新提示词

```bash
cd src/agents/prompts
cp template.yml new_agent.yml
# 编辑 new_agent.yml
```

### 2. 测试提示词

```python
# test_prompt.py
from prompt_loader import PromptLoader

config = PromptLoader.load('new_agent')
print(config['system_prompt'])
```

### 3. 版本管理

每次重大修改都应该：
- 更新 `version` 字段
- 更新 `updated` 日期
- 在git commit中说明修改原因

### 4. A/B测试

```python
# 使用不同变体进行测试
prompt_a = agent.get_variant_prompt('formal')
prompt_b = agent.get_variant_prompt('casual')

# 比较效果
```

## 🎨 提示词编写最佳实践

### 1. 结构清晰

```yaml
system_prompt: |
  # 使用注释标记结构（LLM看不到这些注释）
  
  你是[角色]。你的任务是[任务]。
  
  ## 输出要求
  
  1. [要求1]
     - 详细说明
  
  2. [要求2]
     - 详细说明
  
  ## 输出示例
  
  [具体示例]
  
  请直接输出结果。
```

### 2. 使用变量占位符

```yaml
system_prompt: |
  你是{role}。当前日期是{date}。
  
  任务：{task}
  
  要求：{requirements}
```

然后在代码中替换：

```python
prompt = config['system_prompt'].format(
    role="助手",
    date="2026-01-02",
    task="生成小结",
    requirements="简洁清晰"
)
```

### 3. 版本化迭代

```yaml
metadata:
  version: "1.2.0"
  changelog:
    - "v1.2.0: 优化输出格式，添加emoji支持"
    - "v1.1.0: 改进错误处理提示"
    - "v1.0.0: 初始版本"
```

## 🔍 调试和优化

### 查看加载的提示词

```python
config = PromptLoader.load('summary_agent')
print(config['system_prompt'])
```

### 验证提示词格式

```python
PromptLoader.validate('summary_agent')  # 检查YAML格式
```

### 比较不同版本

```bash
git diff prompts/summary_agent.yml
```

## 🚀 高级功能

### 1. 多语言支持

```yaml
system_prompt_i18n:
  zh: |
    你是中文助手...
  en: |
    You are an English assistant...
```

### 2. 条件提示词

```yaml
conditions:
  short_text:
    condition: "len(input) < 500"
    system_prompt: |
      针对短文本的提示词...
  
  long_text:
    condition: "len(input) >= 500"
    system_prompt: |
      针对长文本的提示词...
```

### 3. 提示词继承

```yaml
extends: "base_agent.yml"  # 继承基础提示词
overrides:
  system_prompt: |
    {{base_prompt}}
    
    # 添加额外要求
    额外的指令...
```

## 📊 提示词质量评估

### 评估维度

1. **准确性**: 输出是否符合预期
2. **一致性**: 多次运行结果是否稳定
3. **格式**: 输出格式是否正确
4. **长度**: 输出长度是否合适
5. **速度**: 生成速度（tokens/sec）

### 评估工具

```python
from prompt_loader import PromptEvaluator

evaluator = PromptEvaluator('summary_agent')
results = evaluator.evaluate(test_cases)
print(evaluator.report())
```

## 📚 参考资源

- [OpenAI Prompt Engineering](https://platform.openai.com/docs/guides/prompt-engineering)
- [Anthropic Prompt Library](https://docs.anthropic.com/claude/prompt-library)
- [LangChain Prompts](https://python.langchain.com/docs/modules/model_io/prompts/)

---

**维护者**: 深圳王哥 & AI  
**最后更新**: 2026-01-02

