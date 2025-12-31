# 禅应用实施规划

> **项目状态**: 脚手架完成，待实现核心功能  
> **创建日期**: 2025-12-31  
> **最后更新**: 2025-12-31

## 概述

本文档是禅应用（VoiceZen）的详细实施规划，将整个开发过程分为 8 个阶段，每个阶段都有明确的目标、任务清单和技术方案。

---

## 阶段 1：基础对话功能（预计 3-5 天）

### 目标
实现基本的语音对话功能，让用户可以与一禅进行简单对话。

### 任务清单

#### 1.1 后端 API 开发

- [ ] **创建 ZenService 服务类**
  - 文件位置：`src/services/zen_service.py`
  - 功能：管理禅应用的核心业务逻辑
  - 依赖：LiteLLM Provider

```python
class ZenService:
    def __init__(self, llm_provider):
        self.llm = llm_provider
        self.system_prompt = get_zen_prompt()
        self.conversations = {}  # 会话管理
    
    async def chat(self, user_id: str, message: str):
        """处理用户消息，返回一禅的回复"""
        pass
```

- [ ] **添加 Zen API 路由**
  - 文件位置：`src/api/server.py`
  - 路由：
    - `POST /api/zen/chat` - 发送消息
    - `GET /api/zen/conversation/{user_id}` - 获取对话历史
    - `POST /api/zen/clear` - 清空对话

- [ ] **加载一禅提示词**
  - 在启动时加载 `src/prompts/zen_master_prompt.py`
  - 将系统提示词传递给 LLM

#### 1.2 前端集成

- [ ] **连接语音输入**
  - 在 `ZenChat.tsx` 中复用现有的 ASR 系统
  - 语音识别结果显示在用户消息气泡中

- [ ] **实现对话 API 调用**
  - 用户消息通过 API 发送到后端
  - 接收一禅的回复并显示

- [ ] **优化对话气泡样式**
  - 用户消息：右侧，白色背景
  - 一禅消息：左侧，半透明紫色背景，楷体字

- [ ] **添加加载状态**
  - 发送消息后显示"一禅正在思考..."
  - 使用动画效果（如三个点跳动）

#### 1.3 测试与优化

- [ ] **测试对话流程**
  - 测试语音输入 → 识别 → 发送 → 回复的完整流程
  - 测试多轮对话是否连贯

- [ ] **调试提示词**
  - 根据实际对话效果调整一禅的提示词
  - 确保回复风格符合角色设定

- [ ] **性能优化**
  - LLM 响应时间控制在 3-5 秒内
  - 考虑使用流式输出（Stream）

### 技术方案

```python
# API 路由示例
@router.post("/api/zen/chat")
async def zen_chat(request: ZenChatRequest):
    """
    请求体:
    {
        "user_id": "user_123",
        "message": "师父，我最近很焦虑"
    }
    
    响应:
    {
        "success": true,
        "zen_response": "阿弥陀佛，施主...",
        "emotion": "焦虑",
        "timestamp": "2025-12-31T10:00:00"
    }
    """
    zen_response = await zen_service.chat(
        user_id=request.user_id,
        message=request.message
    )
    return zen_response
```

### 预期成果

- ✅ 用户可以通过语音与一禅对话
- ✅ 一禅的回复符合角色设定
- ✅ 对话流畅，响应时间合理

---

## 阶段 2：对话历史与持久化（预计 2-3 天）

### 目标
保存对话历史，用户可以查看过去的对话记录。

### 任务清单

#### 2.1 数据库设计

- [ ] **创建对话表**
  - 表名：`zen_conversations`
  - 字段：
    - `id` - 对话ID
    - `user_id` - 用户ID
    - `session_id` - 会话ID（一次打开到关闭算一个会话）
    - `role` - 角色（user/zen）
    - `message` - 消息内容
    - `emotion` - 情绪标签（可选）
    - `created_at` - 创建时间

```sql
CREATE TABLE zen_conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    message TEXT NOT NULL,
    emotion TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_session ON zen_conversations(user_id, session_id);
```

#### 2.2 后端实现

- [ ] **创建数据访问层**
  - 文件：`src/providers/storage/zen_storage.py`
  - 功能：保存和查询对话记录

- [ ] **集成到 ZenService**
  - 每次对话自动保存到数据库
  - 加载历史对话用于上下文

- [ ] **添加历史记录 API**
  - `GET /api/zen/history/{user_id}` - 获取用户的对话历史
  - `GET /api/zen/sessions/{user_id}` - 获取用户的会话列表
  - `DELETE /api/zen/session/{session_id}` - 删除某个会话

#### 2.3 前端实现

- [ ] **添加历史记录查看**
  - 在对话界面添加"历史"按钮
  - 展示过去的对话会话列表
  - 点击会话可以查看详细内容

- [ ] **会话恢复**
  - 可以继续之前的对话（加载上下文）
  - 或者开始新的对话

### 预期成果

- ✅ 所有对话都被保存到数据库
- ✅ 用户可以查看历史对话
- ✅ 支持会话管理（查看、删除、恢复）

---

## 阶段 3：情绪分析系统（预计 3-4 天）

### 目标
实时分析用户情绪，为后续的图片、音乐选择提供依据。

### 任务清单

#### 3.1 情绪分析模型选型

- [ ] **评估方案**
  - 方案 A：使用 LLM 直接判断情绪（简单，但额外调用）
  - 方案 B：使用情感分析库（如 TextBlob、BERT 模型）
  - 方案 C：关键词匹配 + 规则（快速，但不够准确）
  - **推荐**：方案 A + 方案 C 结合（关键词快速判断，LLM 复杂情况）

#### 3.2 实现情绪分析

- [ ] **创建情绪分析器**
  - 文件：`src/services/emotion_analyzer.py`
  - 支持的情绪类型：喜悦、悲伤、愤怒、焦虑、困惑、平静

```python
class EmotionAnalyzer:
    def analyze(self, text: str) -> dict:
        """
        返回:
        {
            "primary_emotion": "焦虑",
            "intensity": "强烈",
            "emotions_scores": {
                "焦虑": 0.8,
                "悲伤": 0.3,
                "困惑": 0.5
            }
        }
        """
        pass
```

- [ ] **关键词情绪库**
  - 建立情绪关键词字典
  - 例如："焦虑" → ["压力大", "紧张", "担心", "睡不着"]

- [ ] **集成到对话流程**
  - 每次用户发言时分析情绪
  - 将情绪信息传递给 LLM（让一禅的回复更贴切）
  - 将情绪信息保存到数据库

#### 3.3 情绪可视化（可选）

- [ ] **在对话界面显示情绪**
  - 用颜色或图标表示当前情绪
  - 例如：😊 喜悦、😔 悲伤、😰 焦虑

- [ ] **情绪趋势图**
  - 在历史记录中显示情绪变化曲线
  - 帮助用户了解自己的情绪模式

### 技术方案

```python
# 情绪分析示例
emotion_keywords = {
    "焦虑": ["焦虑", "压力", "紧张", "担心", "睡不着", "不安"],
    "悲伤": ["难过", "伤心", "失落", "孤独", "痛苦"],
    "愤怒": ["生气", "愤怒", "气愤", "火大", "讨厌"],
    # ...更多
}

def quick_emotion_match(text):
    """快速关键词匹配"""
    scores = {}
    for emotion, keywords in emotion_keywords.items():
        score = sum(1 for kw in keywords if kw in text)
        scores[emotion] = score
    return max(scores, key=scores.get) if scores else "平静"
```

### 预期成果

- ✅ 自动识别用户的情绪状态
- ✅ 情绪信息用于个性化回复
- ✅ 情绪数据保存并可查询

---

## 阶段 4：图片库系统（预计 3-4 天）

### 目标
根据对话情绪和内容，动态切换背景图片，增强沉浸感。

### 任务清单

#### 4.1 图片资源准备

- [ ] **收集禅意图片**
  - 自然风景：山水、云海、日出日落（10-15张）
  - 禅宗元素：寺庙、佛像、禅房（5-10张）
  - 四季意象：春花、夏荷、秋叶、冬雪（各5张）
  - 生活禅意：茶道、书法、竹林（5-10张）

- [ ] **收集 GIF 动图**
  - 流水、飘雪、风吹、火焰（各2-3个）
  - 用于特定情绪场景

- [ ] **图片分类和标签**
  - 为每张图片打标签：情绪、主题、季节
  - 创建图片索引文件：`assets/zen/images/index.json`

```json
{
  "images": [
    {
      "filename": "mountain_sunrise.jpg",
      "emotions": ["平静", "喜悦"],
      "themes": ["自然", "希望"],
      "season": "all",
      "type": "static"
    },
    {
      "filename": "flowing_water.gif",
      "emotions": ["焦虑", "压力"],
      "themes": ["流动", "释放"],
      "season": "all",
      "type": "animated"
    }
  ]
}
```

#### 4.2 后端实现

- [ ] **创建图片库管理器**
  - 文件：`src/services/zen_image_library.py`
  - 功能：根据情绪、主题选择合适的图片

```python
class ZenImageLibrary:
    def __init__(self):
        self.images = self.load_image_index()
    
    def select_image(self, emotion: str, theme: str = None, season: str = None):
        """根据条件选择图片"""
        pass
    
    def get_random_image(self, category: str):
        """从类别中随机选择"""
        pass
```

- [ ] **添加图片 API**
  - `GET /api/zen/image?emotion=焦虑&season=spring`
  - 返回图片 URL 或 base64

#### 4.3 前端实现

- [ ] **动态背景切换**
  - 根据情绪分析结果请求图片
  - 使用 CSS transition 实现平滑切换
  - 预加载下一张图片避免闪烁

- [ ] **背景图片缓存**
  - 将常用图片缓存到本地
  - 减少网络请求

- [ ] **GIF 动图支持**
  - 根据情绪强度决定是否使用动图
  - 例如："强烈焦虑" 使用流水 GIF

### 技术方案

```typescript
// 前端图片切换
const switchBackground = async (emotion: string) => {
  const imageUrl = await fetchZenImage(emotion);
  
  // 预加载
  const img = new Image();
  img.src = imageUrl;
  img.onload = () => {
    setBackgroundImage(imageUrl);
  };
};

// CSS 过渡效果
.zen-chat {
  background-size: cover;
  background-position: center;
  transition: background-image 1.5s ease-in-out;
}
```

### 预期成果

- ✅ 50+ 张精选禅意图片
- ✅ 根据情绪自动切换背景
- ✅ 平滑的过渡动画
- ✅ GIF 动图增强表现力

---

## 阶段 5：音频库系统（预计 3-4 天）

### 目标
播放背景音乐和环境音效，根据情绪调整音乐。

### 任务清单

#### 5.1 音频资源准备

- [ ] **收集背景音乐**
  - 古琴曲（平静、深沉）3-5首
  - 箫曲（悲伤、思考）3-5首
  - 竹笛（喜悦、活泼）3-5首
  - 禅修音乐（冥想、放松）3-5首

- [ ] **收集环境音效**
  - 流水声（缓解焦虑）
  - 鸟鸣声（清晨、活力）
  - 风声（开阔、释放）
  - 雨声（沉思、平静）

- [ ] **收集特殊音效**
  - 木鱼敲击声（点击木鱼时）
  - 寺庙钟声（开始/结束对话）
  - 诵经声（低音量背景，可选）

- [ ] **音频分类和标签**
  - 创建音频索引：`assets/zen/audio/index.json`

```json
{
  "music": [
    {
      "filename": "guqin_flowing_water.mp3",
      "name": "古琴·流水",
      "emotions": ["平静", "思考"],
      "duration": 180,
      "volume": 0.3
    }
  ],
  "ambient": [
    {
      "filename": "water_stream.mp3",
      "name": "溪流",
      "emotions": ["焦虑", "压力"],
      "loop": true,
      "volume": 0.4
    }
  ]
}
```

#### 5.2 后端实现

- [ ] **创建音频库管理器**
  - 文件：`src/services/zen_audio_library.py`
  - 功能：根据情绪选择音乐

- [ ] **添加音频 API**
  - `GET /api/zen/audio?emotion=平静&type=music`
  - 返回音频 URL

#### 5.3 前端实现

- [ ] **音频播放器组件**
  - 支持背景音乐循环播放
  - 支持环境音效叠加
  - 音量控制（说话时自动降低）

```typescript
class ZenAudioPlayer {
  private musicPlayer: HTMLAudioElement;
  private ambientPlayer: HTMLAudioElement;
  
  playMusic(url: string, volume: number = 0.3) { }
  playAmbient(url: string, loop: boolean = true) { }
  fadeOut(duration: number = 2000) { }
  fadeIn(duration: number = 2000) { }
}
```

- [ ] **音乐切换逻辑**
  - 情绪变化时平滑切换音乐（淡出 → 淡入）
  - 避免突兀的音乐切换

- [ ] **用户控制**
  - 音乐开关按钮
  - 音量调节
  - 音乐选择（可选）

#### 5.4 特殊音效

- [ ] **木鱼敲击音效**
  - 点击木鱼时播放
  - 短促、清脆

- [ ] **钟声音效**
  - 进入对话界面时播放（可选）
  - 结束对话时播放（可选）

### 预期成果

- ✅ 20+ 首背景音乐和音效
- ✅ 根据情绪自动选择音乐
- ✅ 平滑的音乐切换
- ✅ 用户可控制播放

---

## 阶段 6：短期记忆系统（预计 2-3 天）

### 目标
让一禅记住当前会话的对话内容，保持对话连贯性。

### 任务清单

#### 6.1 会话上下文管理

- [ ] **实现会话状态**
  - 保存当前会话的所有对话
  - 限制上下文长度（最近 10-20 轮对话）
  - 超出长度时智能截断（保留重要信息）

```python
class SessionContext:
    def __init__(self, max_turns=20):
        self.messages = []
        self.max_turns = max_turns
        self.session_summary = ""
    
    def add_message(self, role, content):
        self.messages.append({"role": role, "content": content})
        if len(self.messages) > self.max_turns * 2:
            self.summarize_and_truncate()
    
    def summarize_and_truncate(self):
        """总结旧对话，保留最近对话"""
        pass
```

- [ ] **上下文注入**
  - 每次调用 LLM 时，将会话上下文作为历史消息
  - 格式：`[{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]`

#### 6.2 会话摘要

- [ ] **自动生成会话摘要**
  - 当会话结束时，生成本次对话的摘要
  - 摘要内容：用户提到的主要问题、情绪、一禅的建议
  - 保存到数据库，用于中期记忆

- [ ] **摘要展示**
  - 在历史记录中显示会话摘要
  - 用户可快速了解之前聊了什么

### 预期成果

- ✅ 一禅能记住当前会话的内容
- ✅ 对话连贯，不会重复问问题
- ✅ 会话结束后自动生成摘要

---

## 阶段 7：中长期记忆系统（预计 5-7 天）

### 目标
构建多层记忆系统，让一禅记住用户的历史对话和重要信息。

### 任务清单

#### 7.1 中期记忆（最近记忆）

- [ ] **数据库设计**
  - 表名：`zen_mid_term_memory`
  - 字段：
    - `id`, `user_id`, `session_id`
    - `summary` - 会话摘要
    - `topics` - 主要话题（JSON）
    - `emotions` - 主要情绪（JSON）
    - `created_at`

- [ ] **自动提取记忆**
  - 从会话摘要中提取关键信息
  - 保存最近 7-30 天的记忆

- [ ] **记忆检索**
  - 根据当前话题检索相关的历史记忆
  - 提醒一禅："施主上次提到过这个问题..."

#### 7.2 长期记忆（重要信息）

- [ ] **数据库设计**
  - 表名：`zen_long_term_memory`
  - 字段：
    - `id`, `user_id`
    - `memory_type` - 记忆类型（basic_info, event, concern）
    - `content` - 记忆内容
    - `importance` - 重要性评分
    - `created_at`, `last_referenced`

- [ ] **重要信息识别**
  - 使用 LLM 判断哪些信息值得长期记住
  - 例如：用户的职业、家庭情况、长期困扰

- [ ] **记忆向量化**
  - 使用 Embedding 模型将记忆转为向量
  - 使用向量数据库（Chroma 或 Faiss）存储
  - 支持语义搜索

```python
class LongTermMemory:
    def __init__(self):
        self.vector_store = ChromaDB()
        self.db = SQLiteDB()
    
    def add_memory(self, user_id, content, memory_type, importance):
        # 向量化
        embedding = self.embed(content)
        # 保存到向量库
        self.vector_store.add(embedding, metadata={...})
        # 保存到关系数据库
        self.db.insert(...)
    
    def retrieve_relevant(self, user_id, query):
        # 语义搜索
        results = self.vector_store.search(query, user_id)
        return results
```

#### 7.3 记忆整合

- [ ] **记忆注入 LLM**
  - 每次对话前，检索相关记忆
  - 将记忆作为系统提示的一部分

- [ ] **记忆更新机制**
  - 当用户更正信息时，更新记忆
  - 例如："我不是程序员，我是设计师"

- [ ] **记忆遗忘机制**
  - 长时间未被引用的记忆降低重要性
  - 可选：用户主动删除某些记忆

### 技术方案

```python
# 记忆检索示例
def prepare_context_with_memory(user_id, current_message):
    # 1. 获取短期记忆（当前会话）
    session_context = get_session_context(user_id)
    
    # 2. 检索中期记忆（最近话题）
    recent_memory = search_mid_term_memory(user_id, current_message)
    
    # 3. 检索长期记忆（重要信息）
    long_term_memory = vector_search_memory(user_id, current_message)
    
    # 4. 组装完整上下文
    full_context = {
        "system": ZEN_SYSTEM_PROMPT,
        "long_term_memory": long_term_memory,
        "recent_memory": recent_memory,
        "conversation_history": session_context
    }
    
    return full_context
```

### 预期成果

- ✅ 一禅记住用户的重要信息
- ✅ 能提及之前的对话内容
- ✅ 对话更有连续性和个性化

---

## 阶段 8：知识库与用户画像（预计 5-7 天）

### 目标
构建禅宗知识库，建立多维用户画像，提供深度个性化体验。

### 任务清单

#### 8.1 禅宗知识库

- [ ] **公案数据库**
  - 从 `zen_master_prompt.py` 中提取公案
  - 扩充到 50+ 个经典公案
  - 数据结构：

```json
{
  "id": "koan_001",
  "title": "赵州茶去",
  "characters": ["赵州禅师", "僧人"],
  "dialogue": "...",
  "insight": "...",
  "themes": ["日常修行", "当下"],
  "emotions": ["困惑", "顿悟"],
  "modern_application": "..."
}
```

- [ ] **知识库向量化**
  - 每个公案转为向量
  - 支持语义搜索："用户的问题 → 最相关的公案"

- [ ] **知识库 API**
  - `GET /api/zen/knowledge/search?query=如何放下执念`
  - 返回最相关的 3-5 个公案或故事

- [ ] **集成到对话**
  - 一禅在回复时自动引用相关公案
  - "施主这个问题，让小僧想起了一个故事..."

#### 8.2 多维用户画像

- [ ] **数据库设计**
  - 表名：`zen_user_profiles`
  - 字段：

```sql
CREATE TABLE zen_user_profiles (
    user_id TEXT PRIMARY KEY,
    
    -- 基本信息
    age_range TEXT,
    occupation TEXT,
    life_stage TEXT,
    
    -- 性格特征
    personality_traits JSON,  -- {"introvert": 0.7, "rational": 0.6, ...}
    
    -- 情绪模式
    emotion_patterns JSON,  -- {"frequent": ["焦虑", "压力"], "triggers": [...]}
    
    -- 关注主题
    topics_of_interest JSON,  -- [{"topic": "工作压力", "frequency": 15}, ...]
    
    -- 禅修进度
    zen_progress JSON,  -- {"understanding": 3, "practice": 2, "acceptance": 4}
    
    -- 互动偏好
    interaction_preference JSON,  -- {"story_vs_advice": 0.7, ...}
    
    updated_at TIMESTAMP
);
```

- [ ] **画像自动更新**
  - 从每次对话中提取信息更新画像
  - 使用 LLM 分析用户特征

```python
async def update_user_profile(user_id, conversation):
    """从对话中更新用户画像"""
    # 让 LLM 分析这次对话透露了哪些用户信息
    analysis = await llm.analyze_user_info(conversation)
    
    # 更新画像
    profile = get_profile(user_id)
    profile.update(analysis)
    save_profile(profile)
```

- [ ] **画像驱动对话**
  - 根据用户性格调整回复风格
  - 例如：理性型用户 → 多用逻辑和比喻；感性型用户 → 多共情和故事

- [ ] **画像可视化（可选）**
  - 用户可以查看自己的画像
  - 雷达图展示各维度特征

#### 8.3 个性化推荐

- [ ] **每日禅语**
  - 根据用户近期情绪推荐合适的禅语
  - 在欢迎页面显示

- [ ] **主题推荐**
  - 根据用户关注的话题推荐相关的禅宗智慧
  - "施主经常为人际关系烦恼，不妨看看这个故事..."

### 预期成果

- ✅ 50+ 个公案的知识库
- ✅ 智能引用相关的禅宗故事
- ✅ 全面的用户画像系统
- ✅ 深度个性化的对话体验

---

## 补充功能（可选，按需实现）

### 语音输出（TTS）

- [ ] 集成 TTS 引擎（如 Azure TTS、火山引擎 TTS）
- [ ] 为一禅选择合适的声音（温和、年轻）
- [ ] 用语音朗读一禅的回复
- [ ] 用户可选择开启/关闭语音输出

### 冥想引导

- [ ] 添加"冥想"模式
- [ ] 一禅引导用户进行简单的冥想练习
- [ ] "闭上眼睛，感受呼吸..."
- [ ] 配合舒缓的背景音乐

### 禅修打卡

- [ ] 记录用户与一禅对话的频率
- [ ] 连续对话打卡奖励
- [ ] 禅修进度可视化

### 情绪日记

- [ ] 自动生成用户的情绪日记
- [ ] 每周/每月情绪报告
- [ ] 帮助用户了解自己的情绪规律

### 社区分享（匿名）

- [ ] 用户可以分享从一禅那里得到的启发
- [ ] 匿名分享到社区
- [ ] 看到其他人的分享和感悟

---

## 技术栈总结

### 后端

| 组件 | 技术选型 | 说明 |
|------|---------|------|
| Web 框架 | FastAPI | 已有基础 |
| LLM | LiteLLM | 支持多种 LLM |
| 数据库 | SQLite | 轻量级，已有基础 |
| 向量数据库 | Chroma / Faiss | 语义搜索 |
| Embedding | OpenAI / HuggingFace | 文本向量化 |
| 情绪分析 | 关键词 + LLM | 混合方案 |

### 前端

| 组件 | 技术选型 | 说明 |
|------|---------|------|
| UI 框架 | React + TypeScript | 已有基础 |
| 音频播放 | HTMLAudioElement | 原生 API |
| 图片管理 | Image preloading | 预加载优化 |
| 状态管理 | React Hooks | 简单场景够用 |
| WebSocket | 原生 WebSocket | 实时通信（可选） |

### 资源

| 资源类型 | 数量 | 来源 |
|---------|------|------|
| 禅意图片 | 50+ | Unsplash, Pexels |
| GIF 动图 | 10+ | Giphy |
| 背景音乐 | 20+ | 版权音乐库 |
| 禅宗公案 | 50+ | 禅宗典籍整理 |

---

## 时间估算

| 阶段 | 预计时间 | 累计时间 |
|------|---------|---------|
| 阶段1: 基础对话 | 3-5 天 | 5 天 |
| 阶段2: 对话历史 | 2-3 天 | 8 天 |
| 阶段3: 情绪分析 | 3-4 天 | 12 天 |
| 阶段4: 图片库 | 3-4 天 | 16 天 |
| 阶段5: 音频库 | 3-4 天 | 20 天 |
| 阶段6: 短期记忆 | 2-3 天 | 23 天 |
| 阶段7: 中长期记忆 | 5-7 天 | 30 天 |
| 阶段8: 知识库与画像 | 5-7 天 | 37 天 |
| **测试与优化** | 5-7 天 | **45 天** |

**总计**: 约 1.5-2 个月完整开发

---

## 风险与注意事项

### 技术风险

1. **LLM 响应质量**
   - 风险：一禅的回复可能不够"禅"
   - 对策：反复调试提示词，收集真实对话优化

2. **响应速度**
   - 风险：LLM 调用可能较慢（3-10秒）
   - 对策：使用流式输出，显示打字动画

3. **记忆系统复杂度**
   - 风险：多层记忆系统可能过于复杂
   - 对策：MVP 先实现简单版本，逐步优化

### 资源风险

1. **图片版权**
   - 风险：使用的图片可能有版权问题
   - 对策：使用免费图库，或购买商用授权

2. **音乐版权**
   - 风险：背景音乐需要版权
   - 对策：使用免费音乐库，或自己制作

### 用户体验风险

1. **文化敏感性**
   - 风险：禅宗文化处理不当可能引起反感
   - 对策：谨慎对待，尊重传统，避免庸俗化

2. **心理边界**
   - 风险：用户可能将一禅当作心理咨询师
   - 对策：明确说明一禅不是心理医生，严重问题建议专业帮助

---

## 成功指标

### MVP（最小可行产品）

- ✅ 用户可以与一禅流畅对话
- ✅ 一禅的回复符合角色设定，有禅意
- ✅ 基础的情绪识别和背景切换
- ✅ 对话历史保存

### 完整版

- ✅ 一禅能记住用户的重要信息（记忆系统）
- ✅ 自动引用合适的禅宗公案（知识库）
- ✅ 根据用户特点个性化回复（用户画像）
- ✅ 沉浸式的多媒体体验（图片+音乐）
- ✅ 用户满意度高，愿意长期使用

---

## 参考文档

1. [禅应用设计文档](./ZEN_APP_DESIGN.md) - 详细的功能设计
2. [一禅提示词](../src/prompts/zen_master_prompt.py) - 角色系统提示词
3. [项目架构文档](./ARCHITECTURE.md) - 整体架构
4. [API 文档](./API.md) - API 接口规范

---

**制定日期**: 2025-12-31  
**制定人**: 深圳王哥 & AI  
**项目**: MindVoice - 禅应用  
**版本**: v1.0

---

## 后记

禅的本质是"当下"，是"直指人心"。我们开发这个应用，不是为了炫技，而是希望能真正帮助到一些人。

愿每个与一禅对话的人，都能找到内心的平静。

阿弥陀佛。🙏

