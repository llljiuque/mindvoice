# MindVoice 存储技术说明文档

**版本**: v1.4.1  
**日期**: 2026-01-05  
**作者**: 深圳王哥 & AI

---

## 📋 目录

- [存储架构概览](#存储架构概览)
- [数据库存储](#数据库存储)
  - [SQLite 历史记录数据库](#sqlite-历史记录数据库)
  - [ChromaDB 向量数据库](#chromadb-向量数据库)
- [文件系统存储](#文件系统存储)
  - [图片文件存储](#图片文件存储)
  - [知识库文件存储](#知识库文件存储)
- [应用保存方式](#应用保存方式)
  - [VoiceNote 保存方式](#voicenote-保存方式)
  - [VoiceChat 保存方式](#voicechat-保存方式)
  - [VoiceZen 保存方式](#voicezen-保存方式)
- [AutoSaveService 统一保存服务](#autosaveservice-统一保存服务)
- [存储提供商架构](#存储提供商架构)
- [性能优化与最佳实践](#性能优化与最佳实践)
- [数据备份与恢复](#数据备份与恢复)

---

## 存储架构概览

MindVoice 采用多层次的存储架构，包括数据库存储和文件系统存储：

```
┌─────────────────────────────────────────────────────────┐
│               MindVoice 应用层                           │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────┐ │
│  │  VoiceNote     │  │  VoiceChat     │  │  VoiceZen  │ │
│  └────────┬───────┘  └────────┬───────┘  └────────┬───┘ │
│           │                   │                    │     │
│           └───────────────────┼────────────────────┘     │
│                               ▼                          │
│                    ┌─────────────────────┐              │
│                    │ AutoSaveService     │              │
│                    │  统一自动保存服务   │              │
│                    └──────────┬──────────┘              │
│                               │                          │
├───────────────────────────────┼──────────────────────────┤
│                               ▼                          │
│              ┌────────────────────────────┐             │
│              │   存储层 (Storage Layer)   │             │
│              └─────────────┬──────────────┘             │
│                            │                             │
│       ┌────────────────────┼────────────────────┐       │
│       ▼                    ▼                    ▼       │
│  ┌─────────┐         ┌──────────┐        ┌──────────┐  │
│  │ SQLite  │         │ ChromaDB │        │文件系统  │  │
│  │ Database│         │ Vector DB│        │Storage   │  │
│  │         │         │          │        │          │  │
│  │历史记录 │         │知识库向量│        │图片文件  │  │
│  │元数据   │         │语义检索  │        │知识库文件│  │
│  └─────────┘         └──────────┘        └──────────┘  │
│                                                          │
└─────────────────────────────────────────────────────────┘

数据流向：
应用 → AutoSaveService → 存储提供商 → 持久化存储
```

### 存储类型

| 存储类型 | 技术方案 | 用途 | 位置 |
|---------|---------|------|------|
| **关系数据库** | SQLite | 历史记录、元数据 | `~/.voice_assistant/history.db` |
| **向量数据库** | ChromaDB | 知识库向量、语义检索 | `./data/knowledge/chroma/` |
| **文件存储** | 本地文件系统 | 图片、知识库文件 | `./data/images/`, `./data/knowledge/files/` |
| **临时存储** | localStorage | 临时数据、草稿 | 浏览器 localStorage |

---

## 数据库存储

### SQLite 历史记录数据库

#### 概述

SQLite 是一个轻量级、零配置的嵌入式关系数据库，用于存储所有应用的历史记录。

#### 配置

```yaml
# config.yml
storage:
  path: ~/.voice_assistant/history.db  # 数据库文件路径
```

**默认位置**: `~/.voice_assistant/history.db`

#### 表结构

##### records 表

存储所有应用的历史记录。

```sql
CREATE TABLE IF NOT EXISTS records (
    id TEXT PRIMARY KEY,                          -- UUID 格式的唯一标识符
    text TEXT NOT NULL,                           -- 记录的文本内容
    metadata TEXT,                                -- JSON 格式的元数据
    app_type TEXT DEFAULT 'voice-note',           -- 应用类型标识
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- 创建时间
);
```

**字段说明**:

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `id` | TEXT | 主键，UUID格式 | `550e8400-e29b-41d4-a716-446655440000` |
| `text` | TEXT | 记录文本内容（纯文本） | `今天学习了 Python...` |
| `metadata` | TEXT | JSON 格式元数据 | 见下方 |
| `app_type` | TEXT | 应用类型 | `voice-note`, `voice-chat`, `voice-zen` |
| `created_at` | TIMESTAMP | 创建时间 | `2026-01-05 14:30:00` |

**metadata 结构（VoiceNote）**:

```json
{
  "app_type": "voice-note",
  "trigger": "definite_utterance",
  "timestamp": 1704441600000,
  "block_count": 5,
  "noteInfo": {
    "title": "笔记标题",
    "startTime": "2026-01-05 14:00:00",
    "endTime": "2026-01-05 14:30:00",
    "duration": 1800
  },
  "blocks": [
    {
      "id": "block-1",
      "type": "paragraph",
      "content": "段落内容",
      "timestamp": 1704441600000
    },
    {
      "id": "block-2",
      "type": "image",
      "content": "",
      "imageUrl": "images/1704441600000-abc123.png",
      "imageCaption": "图片说明"
    }
  ]
}
```

**metadata 结构（VoiceChat）**:

```json
{
  "app_type": "voice-chat",
  "messages": [
    {
      "role": "user",
      "content": "用户问题"
    },
    {
      "role": "assistant",
      "content": "AI 回答"
    }
  ],
  "model": "qwen-plus",
  "messages_count": 2
}
```

#### 索引优化

```sql
-- 创建复合索引，优化按应用类型和时间查询
CREATE INDEX IF NOT EXISTS idx_records_app_type_created 
ON records(app_type, created_at DESC);

-- 创建应用类型索引
CREATE INDEX IF NOT EXISTS idx_records_app_type 
ON records(app_type);
```

#### 代码实现

**位置**: `src/providers/storage/sqlite.py`

```python
class SQLiteStorageProvider(BaseStorageProvider):
    """SQLite 存储提供商"""
    
    def save_record(self, text: str, metadata: Dict[str, Any]) -> str:
        """保存记录，返回记录ID"""
        record_id = str(uuid.uuid4())
        app_type = metadata.get('app_type', 'voice-note')
        
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO records (id, text, metadata, app_type)
            VALUES (?, ?, ?, ?)
        ''', (record_id, text, json.dumps(metadata, ensure_ascii=False), app_type))
        conn.commit()
        conn.close()
        
        return record_id
    
    def update_record(self, record_id: str, text: str, 
                      metadata: Dict[str, Any]) -> bool:
        """更新记录（用于增量保存）"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE records
            SET text = ?, metadata = ?
            WHERE id = ?
        ''', (text, json.dumps(metadata, ensure_ascii=False), record_id))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def list_records(self, limit: int = 100, offset: int = 0, 
                     app_type: Optional[str] = None) -> list[Dict[str, Any]]:
        """列出记录，支持分页和按应用类型筛选"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if app_type:
            cursor.execute('''
                SELECT id, text, metadata, app_type, created_at
                FROM records
                WHERE app_type = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (app_type, limit, offset))
        else:
            cursor.execute('''
                SELECT id, text, metadata, app_type, created_at
                FROM records
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (limit, offset))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_dict(row) for row in rows]
```

---

### ChromaDB 向量数据库

#### 概述

ChromaDB 是一个高性能的向量数据库，用于知识库的语义搜索和检索增强生成（RAG）。

#### 配置

```python
# 知识库服务配置
storage_path = "./data/knowledge"
embedding_model = "all-MiniLM-L6-v2"  # sentence-transformers 模型
collection_name = "mindvoice_knowledge"
```

**存储位置**:
- 向量数据库: `./data/knowledge/chroma/`
- 原始文件: `./data/knowledge/files/`

#### 数据模型

##### 集合（Collection）结构

```python
{
    "id": "file_id_chunk_0",                      # 文本块 ID
    "embedding": [0.123, -0.456, ...],            # 384 维向量
    "document": "文本块的实际内容...",            # 文本内容
    "metadata": {                                 # 元数据
        "file_id": "550e8400-e29b-41d4-a716-446655440000",
        "filename": "example.md",
        "chunk_index": 0,
        "total_chunks": 10
    }
}
```

#### 文本分块策略

```python
# 默认参数
chunk_size = 500      # 每块 500 字符
chunk_overlap = 50    # 块之间重叠 50 字符

# 分块算法：优先在句子边界分割
def _chunk_text(text: str, chunk_size: int = 500, 
                chunk_overlap: int = 50) -> List[str]:
    """
    文本分块，优先在句子边界（。！？\n\n）分割
    """
    chunks = []
    start = 0
    
    while start < len(text):
        end = min(start + chunk_size, len(text))
        
        # 优先在句子边界分割
        if end < len(text):
            for sep in ['。', '！', '？', '\n\n', '\n', '，']:
                pos = text.rfind(sep, start, end)
                if pos > start:
                    end = pos + 1
                    break
        
        chunks.append(text[start:end])
        start = end - chunk_overlap if end < len(text) else end
    
    return chunks
```

#### 向量化流程

```
1. 文档上传
   ↓
2. 文本分块（chunk_text）
   ↓
3. 生成向量（sentence-transformers）
   ↓
4. 存储到 ChromaDB
   ↓
5. 语义搜索（查询时）
```

#### 代码实现

**位置**: `src/services/knowledge_service.py`

```python
class KnowledgeService:
    """知识库服务"""
    
    async def upload_file(self, filename: str, content: str,
                          metadata: Optional[Dict[str, Any]] = None):
        """上传文件到知识库"""
        # 1. 生成文件 ID
        file_id = str(uuid.uuid4())
        
        # 2. 保存原始文件
        file_path = self.storage_path / "files" / f"{file_id}_{filename}"
        file_path.parent.mkdir(exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 3. 文本分块
        chunks = self._chunk_text(content)
        
        # 4. 生成向量
        embeddings = await loop.run_in_executor(
            None,
            lambda: self.embedding_model.encode(chunks).tolist()
        )
        
        # 5. 存储到 ChromaDB
        chunk_ids = [f"{file_id}_chunk_{i}" for i in range(len(chunks))]
        self.collection.add(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=[{"file_id": file_id, ...} for _ in chunks]
        )
        
        return {"file_id": file_id, "chunks": len(chunks)}
    
    async def search(self, query: str, top_k: int = 3):
        """语义搜索"""
        # 1. 生成查询向量
        query_embedding = self.embedding_model.encode([query])[0]
        
        # 2. 向量相似度搜索
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k
        )
        
        return results
```

---

## 文件系统存储

### 图片文件存储

#### 概述

用户粘贴到笔记中的图片会被保存到本地文件系统。

#### 存储位置

```
项目根目录/
└── data/
    └── images/                         # 图片存储目录
        ├── 1704441600000-abc123.png   # 时间戳-UUID.png
        ├── 1704441700000-def456.jpg
        └── ...
```

#### 文件命名规则

```
格式: {timestamp}-{uuid}.{ext}

示例: 1704441600000-abc123.png
说明:
  - timestamp: 毫秒级时间戳
  - uuid: 8位短 UUID
  - ext: 文件扩展名（png, jpg, gif, webp）
```

#### 支持的图片格式

- PNG (推荐)
- JPEG / JPG
- GIF
- WebP

#### 后端 API

**位置**: `src/api/server.py`

##### 保存图片

```python
@app.post("/api/images/save")
async def save_image(request: SaveImageRequest):
    """保存 Base64 编码的图片"""
    # 1. 解码 Base64
    if ',' in request.image_data:
        image_data = request.image_data.split(',', 1)[1]
    image_bytes = base64.b64decode(image_data)
    
    # 2. 创建目录
    images_dir = project_root / "data" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    
    # 3. 生成文件名
    timestamp = int(time.time() * 1000)
    unique_id = str(uuid.uuid4())[:8]
    filename = f"{timestamp}-{unique_id}.png"
    
    # 4. 保存文件
    image_path = images_dir / filename
    with open(image_path, 'wb') as f:
        f.write(image_bytes)
    
    # 5. 返回相对路径
    return {
        "success": True,
        "image_url": f"images/{filename}"
    }
```

##### 获取图片

```python
@app.get("/api/images/{filename}")
async def get_image(filename: str):
    """获取图片文件"""
    # 安全检查：防止路径遍历攻击
    if '..' in filename or '/' in filename or '\\' in filename:
        raise HTTPException(status_code=400, detail="无效的文件名")
    
    image_path = project_root / "data" / "images" / filename
    
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="图片不存在")
    
    return FileResponse(image_path)
```

#### 前端使用

```typescript
// 粘贴图片事件处理
const handlePaste = async (e: ClipboardEvent) => {
  const items = e.clipboardData?.items;
  
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      const blob = item.getAsFile();
      const reader = new FileReader();
      
      reader.onload = async (event) => {
        const base64 = event.target?.result as string;
        
        // 调用后端 API 保存图片
        const response = await fetch('http://127.0.0.1:8765/api/images/save', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image_data: base64 })
        });
        
        const data = await response.json();
        
        // 创建图片 block
        const imageBlock = {
          id: `block-${Date.now()}`,
          type: 'image',
          content: '',
          imageUrl: data.image_url  // "images/1704441600000-abc123.png"
        };
        
        // 添加到编辑器
        addBlock(imageBlock);
      };
      
      reader.readAsDataURL(blob);
    }
  }
};
```

#### 图片显示

```tsx
// 在 Block 中渲染图片
if (block.type === 'image' && block.imageUrl) {
  return (
    <div className="image-block">
      <img 
        src={`http://127.0.0.1:8765/api/${block.imageUrl}`}
        alt={block.imageCaption || '图片'}
        onError={(e) => {
          e.currentTarget.src = '/placeholder.png';
        }}
      />
      {block.imageCaption && (
        <p className="image-caption">{block.imageCaption}</p>
      )}
    </div>
  );
}
```

---

### 知识库文件存储

#### 概述

用户上传到知识库的文档文件会保存到本地文件系统，同时其向量表示存储在 ChromaDB 中。

#### 存储位置

```
项目根目录/
└── data/
    └── knowledge/
        ├── chroma/                           # ChromaDB 数据库文件
        │   └── chroma.sqlite3
        └── files/                            # 原始文件
            ├── {file_id}_{filename}.md
            ├── {file_id}_{filename}.txt
            └── ...
```

#### 文件命名规则

```
格式: {file_id}_{filename}

示例: 550e8400-e29b-41d4-a716-446655440000_example.md
说明:
  - file_id: UUID 格式的文件唯一标识符
  - filename: 原始文件名
```

#### 支持的文件格式

- Markdown (.md)
- 纯文本 (.txt)

#### 文件处理流程

```
1. 用户上传文件
   ↓
2. 生成 file_id (UUID)
   ↓
3. 保存原始文件到 data/knowledge/files/
   ↓
4. 读取文件内容
   ↓
5. 文本分块 (500字符/块)
   ↓
6. 向量化 (sentence-transformers)
   ↓
7. 存储向量到 ChromaDB
   ↓
8. 返回 file_id 和统计信息
```

---

## 应用保存方式

### VoiceNote 保存方式

#### 数据结构

VoiceNote 使用基于 Block 的数据结构：

```typescript
interface Block {
  id: string;                    // Block 唯一标识
  type: BlockType;               // Block 类型
  content: string;               // 文本内容
  timestamp?: number;            // 创建时间戳
  isAsrWriting?: boolean;        // 是否正在 ASR 写入
  isBufferBlock?: boolean;       // 是否是缓冲 Block
  isSummary?: boolean;           // 是否是摘要 Block
  imageUrl?: string;             // 图片 URL（type='image'）
  imageCaption?: string;         // 图片说明
}

type BlockType = 'paragraph' | 'note-info' | 'image' | 'summary';

interface NoteInfo {
  title: string;                 // 笔记标题
  startTime: string;             // 开始时间
  endTime?: string;              // 结束时间
  duration?: number;             // 持续时间（秒）
}
```

#### 保存策略

VoiceNote 使用 AutoSaveService 实现智能自动保存：

```typescript
// 1. localStorage 临时保存（每1秒）
// 保存正在编辑或 ASR 写入的 volatile blocks
localStorage.setItem('voice-note-volatile-blocks', JSON.stringify({
  blocks: [/* volatile blocks */],
  timestamp: Date.now()
}));

// 2. 数据库持久化保存
// 保存稳定的 stable blocks
```

#### 保存触发条件

| 触发器 | 条件 | 延迟 | 说明 |
|--------|------|------|------|
| `definite_utterance` | ASR 确认完整语句 | 立即 | 防止语音输入丢失 |
| `edit_complete` | Block 失焦 | 3秒防抖 | 编辑完成后保存 |
| `content_change` | 笔记信息变更 | 3秒防抖 | 标题、时间等变更 |
| `periodic` | 定时检查 | 60秒 | 定期保存兜底 |
| `backup` | 长时间编辑 | 30秒 | 持续编辑兜底保存 |
| `manual` | 用户点击保存 | 立即 | 手动触发保存 |

#### volatile 与 stable 判断

```typescript
// Volatile Block: 临时状态，只保存到 localStorage
function isVolatileBlock(block: Block): boolean {
  // 1. 正在 ASR 写入
  if (block.isAsrWriting) return true;
  
  // 2. 用户正在编辑
  if (block.id === currentEditingBlockId) return true;
  
  return false;
}

// Stable Block: 稳定状态，保存到数据库
function getStableBlocks(blocks: Block[]): Block[] {
  return blocks.filter(block => !isVolatileBlock(block));
}
```

#### 保存到数据库的数据格式

```json
{
  "text": "段落1内容\n段落2内容\n[SUMMARY_BLOCK_START]智能摘要内容[SUMMARY_BLOCK_END]",
  "app_type": "voice-note",
  "blocks": [
    {
      "id": "block-1",
      "type": "paragraph",
      "content": "段落1内容",
      "timestamp": 1704441600000
    },
    {
      "id": "block-2",
      "type": "paragraph",
      "content": "段落2内容",
      "timestamp": 1704441610000
    },
    {
      "id": "block-3",
      "type": "image",
      "content": "",
      "imageUrl": "images/1704441620000-abc123.png",
      "imageCaption": "图片说明"
    },
    {
      "id": "block-4",
      "type": "summary",
      "content": "智能摘要内容",
      "isSummary": true
    }
  ],
  "metadata": {
    "trigger": "definite_utterance",
    "timestamp": 1704441600000,
    "block_count": 4,
    "noteInfo": {
      "title": "笔记标题",
      "startTime": "2026-01-05 14:00:00",
      "endTime": "2026-01-05 14:30:00",
      "duration": 1800
    }
  }
}
```

#### 恢复流程

```typescript
// 应用启动时恢复
useEffect(() => {
  async function recover() {
    // 1. 尝试从数据库恢复最近的记录（1小时内）
    const dbRecord = await voiceNoteAutoSave.recoverFromDatabase();
    
    // 2. 检查 localStorage 中是否有更新的临时数据（5分钟内）
    const localData = voiceNoteAutoSave.recoverFromLocalStorage();
    
    // 3. 优先使用更新的数据
    if (localData && localData.timestamp > dbRecord.timestamp) {
      // 使用 localStorage 数据
      restoreBlocks(localData.blocks);
    } else if (dbRecord) {
      // 使用数据库数据
      restoreBlocks(dbRecord.blocks);
    }
  }
  
  recover();
}, []);
```

---

### VoiceChat 保存方式

#### 数据结构

VoiceChat 使用消息列表结构：

```typescript
interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  model?: string;  // 使用的 LLM 模型
}

interface ChatSession {
  messages: Message[];
  model: string;
  startTime: string;
  endTime?: string;
}
```

#### 保存到数据库的数据格式

```json
{
  "text": "用户: 问题1\n助手: 回答1\n用户: 问题2\n助手: 回答2",
  "app_type": "voice-chat",
  "metadata": {
    "messages": [
      {
        "role": "user",
        "content": "问题1",
        "timestamp": 1704441600000
      },
      {
        "role": "assistant",
        "content": "回答1",
        "timestamp": 1704441605000,
        "model": "qwen-plus"
      }
    ],
    "model": "qwen-plus",
    "messages_count": 4,
    "startTime": "2026-01-05 14:00:00",
    "endTime": "2026-01-05 14:10:00"
  }
}
```

#### 保存策略

```typescript
// VoiceChat 适配器
class VoiceChatAdapter implements IAutoSaveAdapter {
  isVolatileItem(message: Message): boolean {
    // 正在等待 AI 回复的消息是 volatile
    return message.role === 'user' && !message.hasResponse;
  }
  
  getStableItems(): Message[] {
    // 返回已完成的对话消息
    return this.messages.filter(msg => 
      msg.role === 'assistant' || msg.hasResponse
    );
  }
  
  convertToSaveData(messages: Message[]) {
    const text = messages.map(msg => 
      `${msg.role === 'user' ? '用户' : '助手'}: ${msg.content}`
    ).join('\n');
    
    return {
      text,
      metadata: {
        app_type: 'voice-chat',
        messages,
        model: this.currentModel,
        messages_count: messages.length
      }
    };
  }
}
```

---

### VoiceZen 保存方式

#### 数据结构

VoiceZen（禅应用）用于冥想、专注等场景：

```typescript
interface ZenSession {
  type: 'meditation' | 'focus' | 'breathe';
  duration: number;              // 持续时间（秒）
  notes: string;                 // 用户笔记
  startTime: string;
  endTime: string;
  completionRate: number;        // 完成率（0-100）
}
```

#### 保存到数据库的数据格式

```json
{
  "text": "冥想会话 - 持续时间: 20分钟\n笔记: 今天感觉很平静...",
  "app_type": "voice-zen",
  "metadata": {
    "type": "meditation",
    "duration": 1200,
    "notes": "今天感觉很平静...",
    "startTime": "2026-01-05 14:00:00",
    "endTime": "2026-01-05 14:20:00",
    "completionRate": 100
  }
}
```

---

## AutoSaveService 统一保存服务

### 架构设计

AutoSaveService 为所有应用提供统一的自动保存能力，通过适配器模式支持不同应用的数据结构。

```typescript
// 统一服务
class AutoSaveService {
  constructor(
    private appType: string,
    private adapter: IAutoSaveAdapter
  ) {}
  
  start() {
    // 启动自动保存定时器
    this.localStorageTimer = setInterval(() => {
      this.saveToLocalStorage();
    }, 1000);  // 每1秒保存临时数据
    
    this.periodicSaveTimer = setInterval(() => {
      this.saveToDatabase('periodic', false);
    }, 60000);  // 每60秒保存到数据库
  }
  
  stop() {
    // 停止所有定时器
    clearInterval(this.localStorageTimer);
    clearInterval(this.periodicSaveTimer);
  }
  
  saveToDatabase(trigger: SaveTrigger, immediate: boolean) {
    // 保存到数据库
  }
  
  saveToLocalStorage() {
    // 保存到 localStorage
  }
  
  recover() {
    // 数据恢复
  }
}

// 应用适配器接口
interface IAutoSaveAdapter {
  isVolatileItem(item: any): boolean;
  getStableItems(): any[];
  getVolatileItems(): any[];
  convertToSaveData(items: any[]): { text: string; metadata: any };
  convertToLocalStorageData(items: any[]): any;
  recoverFromDatabase(data: any): any;
  recoverFromLocalStorage(data: any): any;
}
```

### 工作流程

```
1. 应用启动
   ↓
2. 创建适配器 (VoiceNoteAdapter / VoiceChatAdapter / VoiceZenAdapter)
   ↓
3. 创建 AutoSaveService 实例
   ↓
4. 调用 service.start() 启动自动保存
   ↓
5. 定时器自动运行:
   - localStorage 保存 (1秒)
   - 数据库保存 (60秒)
   - 编辑兜底保存 (30秒)
   ↓
6. 应用切换或关闭时调用 service.stop()
```

### 使用示例

```typescript
// App.tsx
const voiceNoteAdapter = useMemo(() => {
  return new VoiceNoteAdapter(
    () => blockEditorRef.current?.getBlocks?.() || [],
    () => blockEditorRef.current?.getNoteInfo?.()
  );
}, []);

const voiceNoteAutoSave = useMemo(() => {
  return new AutoSaveService('voice-note', voiceNoteAdapter);
}, [voiceNoteAdapter]);

useEffect(() => {
  if (isWorkSessionActive && activeView === 'voice-note') {
    voiceNoteAutoSave.start();
    return () => voiceNoteAutoSave.stop();
  }
}, [isWorkSessionActive, activeView]);

// 在回调中触发保存
<VoiceNote
  onBlockBlur={() => voiceNoteAutoSave.saveToDatabase('edit_complete', false)}
  onContentChange={(_, isUtterance) => {
    if (isUtterance) {
      voiceNoteAutoSave.saveToDatabase('definite_utterance', true);
    }
  }}
/>
```

---

## 存储提供商架构

### 架构设计

```
StorageProvider (抽象接口)
    └── BaseStorageProvider (基类实现)
            └── SQLiteStorageProvider (SQLite 实现)
            └── PostgreSQLProvider (扩展：PostgreSQL)
            └── MySQLProvider (扩展：MySQL)
```

### 抽象接口

```python
# src/core/base.py
class StorageProvider(ABC):
    """存储提供商抽象基类"""
    
    @abstractmethod
    def save_record(self, text: str, metadata: Dict[str, Any]) -> str:
        """保存记录，返回记录ID"""
        pass
    
    @abstractmethod
    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """获取记录"""
        pass
    
    @abstractmethod
    def list_records(self, limit: int = 100, offset: int = 0) -> list[Dict[str, Any]]:
        """列出记录"""
        pass
    
    @abstractmethod
    def delete_record(self, record_id: str) -> bool:
        """删除记录"""
        pass
    
    @abstractmethod
    def update_record(self, record_id: str, text: str, 
                      metadata: Dict[str, Any]) -> bool:
        """更新记录"""
        pass
```

### 扩展新的存储提供商

```python
# 示例：实现 PostgreSQL 提供商
class PostgreSQLProvider(BaseStorageProvider):
    """PostgreSQL 存储提供商"""
    
    PROVIDER_NAME = "postgresql"
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化 PostgreSQL 连接"""
        self.conn = psycopg2.connect(
            host=config.get('host', 'localhost'),
            port=config.get('port', 5432),
            database=config.get('database', 'mindvoice'),
            user=config.get('user'),
            password=config.get('password')
        )
        self._create_table()
        return True
    
    def save_record(self, text: str, metadata: Dict[str, Any]) -> str:
        """实现保存方法"""
        # ... 实现代码
```

---

## 性能优化与最佳实践

### SQLite 优化

#### 1. 连接管理

```python
# ❌ 不好：连接泄漏
def bad_example():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM records")
    # 忘记关闭连接

# ✅ 好：使用上下文管理器
def good_example():
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM records")
        conn.commit()
    # 自动关闭连接
```

#### 2. PRAGMA 优化

```python
# 性能优化设置
conn.execute("PRAGMA journal_mode = WAL")      # WAL 模式提高并发
conn.execute("PRAGMA synchronous = NORMAL")    # 平衡性能和安全
conn.execute("PRAGMA cache_size = -64000")     # 64MB 缓存
conn.execute("PRAGMA temp_store = MEMORY")     # 临时表存储在内存
```

#### 3. 批量操作

```python
# ❌ 不好：逐条插入
for record in records:
    cursor.execute("INSERT INTO records VALUES (?, ?)", record)
    conn.commit()  # 每次提交很慢

# ✅ 好：批量插入
cursor.executemany("INSERT INTO records VALUES (?, ?)", records)
conn.commit()  # 一次提交
```

#### 4. 索引使用

```sql
-- 为常用查询创建索引
CREATE INDEX IF NOT EXISTS idx_records_app_type_created 
ON records(app_type, created_at DESC);

-- 查询时使用索引
SELECT * FROM records 
WHERE app_type = 'voice-note' 
ORDER BY created_at DESC 
LIMIT 20;
```

### ChromaDB 优化

#### 1. 延迟加载

```python
# 启动时不加载模型，加快启动速度
knowledge_service = KnowledgeService(
    storage_path="./data/knowledge",
    embedding_model="all-MiniLM-L6-v2",
    lazy_load=True  # 延迟加载
)
```

#### 2. 异步处理

```python
# 使用线程池执行向量生成，避免阻塞事件循环
loop = asyncio.get_event_loop()
embeddings = await loop.run_in_executor(
    None,
    lambda: self.embedding_model.encode(chunks).tolist()
)
```

#### 3. 批量插入

```python
# 批量插入向量，而不是逐个插入
self.collection.add(
    ids=chunk_ids,
    embeddings=embeddings,
    documents=chunks,
    metadatas=metadatas
)
```

### 文件系统优化

#### 1. 目录结构

```python
# 按日期分目录存储图片，避免单目录文件过多
images_dir = Path("data/images") / date.today().strftime("%Y%m%d")
images_dir.mkdir(parents=True, exist_ok=True)
```

#### 2. 文件清理

```python
# 定期清理旧文件
def cleanup_old_images(days=30):
    """删除30天前的图片"""
    cutoff_date = datetime.now() - timedelta(days=days)
    images_dir = Path("data/images")
    
    for image_file in images_dir.glob("*.png"):
        if image_file.stat().st_mtime < cutoff_date.timestamp():
            image_file.unlink()
```

### AutoSaveService 优化

#### 1. 防抖保存

```typescript
// 使用防抖避免频繁保存
let debounceTimer: NodeJS.Timeout | null = null;

function debounceSave(delay: number = 3000) {
  if (debounceTimer) clearTimeout(debounceTimer);
  
  debounceTimer = setTimeout(() => {
    performSave();
  }, delay);
}
```

#### 2. 差异检测

```typescript
// 只在内容变化时保存
let lastSavedContent = '';

function shouldSave(currentContent: string): boolean {
  if (currentContent === lastSavedContent) {
    return false;  // 内容未变化，跳过保存
  }
  lastSavedContent = currentContent;
  return true;
}
```

---

## 数据备份与恢复

### SQLite 备份

#### 自动备份

```bash
#!/bin/bash
# backup_db.sh

DB_PATH=~/.voice_assistant/history.db
BACKUP_DIR=~/.voice_assistant/backups
BACKUP_FILE=$BACKUP_DIR/history_$(date +%Y%m%d_%H%M%S).db

mkdir -p $BACKUP_DIR
sqlite3 $DB_PATH ".backup $BACKUP_FILE"

# 保留最近7天的备份
find $BACKUP_DIR -name "history_*.db" -mtime +7 -delete

echo "数据库备份完成: $BACKUP_FILE"
```

#### 手动备份

```bash
# 方法1: 文件复制
cp ~/.voice_assistant/history.db ~/.voice_assistant/history.db.backup

# 方法2: SQLite 备份命令（推荐）
sqlite3 ~/.voice_assistant/history.db ".backup ~/.voice_assistant/history.db.backup"

# 方法3: 导出为 SQL
sqlite3 ~/.voice_assistant/history.db .dump > backup.sql
```

#### 恢复

```bash
# 从备份恢复
cp ~/.voice_assistant/history.db.backup ~/.voice_assistant/history.db

# 从 SQL 文件恢复
sqlite3 ~/.voice_assistant/history.db < backup.sql
```

### ChromaDB 备份

```bash
# 备份整个知识库目录
tar -czf knowledge_backup_$(date +%Y%m%d).tar.gz ./data/knowledge/

# 恢复
tar -xzf knowledge_backup_20260105.tar.gz
```

### 图片文件备份

```bash
# 备份图片目录
tar -czf images_backup_$(date +%Y%m%d).tar.gz ./data/images/

# 或使用 rsync 增量备份
rsync -av --delete ./data/images/ /backup/images/
```

### 完整备份脚本

```bash
#!/bin/bash
# full_backup.sh

BACKUP_ROOT=~/mindvoice_backups
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=$BACKUP_ROOT/$TIMESTAMP

mkdir -p $BACKUP_DIR

# 1. 备份 SQLite 数据库
echo "备份数据库..."
sqlite3 ~/.voice_assistant/history.db ".backup $BACKUP_DIR/history.db"

# 2. 备份知识库
echo "备份知识库..."
tar -czf $BACKUP_DIR/knowledge.tar.gz ./data/knowledge/

# 3. 备份图片
echo "备份图片..."
tar -czf $BACKUP_DIR/images.tar.gz ./data/images/

# 4. 创建备份清单
echo "创建备份清单..."
cat > $BACKUP_DIR/manifest.txt <<EOF
备份时间: $(date)
数据库: history.db
知识库: knowledge.tar.gz
图片: images.tar.gz
EOF

echo "备份完成: $BACKUP_DIR"

# 5. 清理30天前的备份
find $BACKUP_ROOT -type d -mtime +30 -exec rm -rf {} +
```

---

## 总结

### 存储架构特点

| 特性 | 说明 |
|------|------|
| **多层次存储** | 数据库 + 文件系统 + 临时存储 |
| **统一接口** | AutoSaveService 统一自动保存 |
| **适配器模式** | 支持不同应用的数据结构 |
| **智能保存** | volatile/stable 区分，减少无效保存 |
| **可靠恢复** | localStorage + 数据库双重保障 |
| **性能优化** | 防抖、批量操作、索引优化 |
| **易于扩展** | 存储提供商接口，支持新数据库 |

### 数据流向

```
用户操作
  ↓
应用层 (VoiceNote/VoiceChat/VoiceZen)
  ↓
AutoSaveService (统一保存服务)
  ↓
适配器 (应用特定数据转换)
  ↓
存储提供商 (SQLite/ChromaDB/FileSystem)
  ↓
持久化存储
```

### 最佳实践

1. **数据分层**: 临时数据用 localStorage，持久化用数据库
2. **智能保存**: 区分 volatile 和 stable，减少不必要的保存
3. **防抖机制**: 避免频繁写入数据库
4. **定期备份**: 自动备份重要数据
5. **错误处理**: 保存失败时保留临时数据
6. **性能监控**: 记录保存耗时，优化慢查询

---

**文档版本**: 1.0  
**最后更新**: 2026-01-05  
**维护者**: MindVoice 开发团队  
**联系方式**: manwjh@126.com

