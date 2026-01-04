# 数据库技术说明文档

本文档详细说明 MindVoice 项目中使用的数据库系统，包括 SQLite 关系数据库和 ChromaDB 向量数据库的架构、设计和使用方法。

## 📋 目录

- [数据库概览](#数据库概览)
- [SQLite 历史记录数据库](#sqlite-历史记录数据库)
- [ChromaDB 向量数据库](#chromadb-向量数据库)
- [数据模型设计](#数据模型设计)
- [存储提供商架构](#存储提供商架构)
- [API 接口](#api-接口)
- [数据迁移与维护](#数据迁移与维护)
- [性能优化](#性能优化)
- [故障排查](#故障排查)

---

## 数据库概览

MindVoice 项目使用两种类型的数据库：

1. **SQLite** - 轻量级关系数据库，用于存储历史记录（语音笔记、对话记录等）
2. **ChromaDB** - 向量数据库，用于知识库的语义搜索和检索增强（RAG）

两种数据库各司其职，互不干扰：

```
┌─────────────────────────────────────┐
│         MindVoice 应用              │
├─────────────────────────────────────┤
│                                     │
│  ┌──────────────┐  ┌─────────────┐ │
│  │  SQLite DB   │  │ ChromaDB    │ │
│  │              │  │             │ │
│  │ 历史记录存储 │  │ 知识库向量  │ │
│  │ - 语音笔记   │  │ - 文档向量  │ │
│  │ - 对话记录   │  │ - 语义检索  │ │
│  │ - 元数据     │  │ - RAG增强   │ │
│  └──────────────┘  └─────────────┘ │
│                                     │
└─────────────────────────────────────┘
```

---

## SQLite 历史记录数据库

### 概述

SQLite 数据库用于存储应用的历史记录，包括语音笔记、智能对话、禅应用等所有应用的记录数据。

### 数据库配置

**配置文件**: `config.yml`

```yaml
storage:
  path: ~/.voice_assistant/history.db  # 数据库路径
```

**默认路径**: `~/.voice_assistant/history.db`

数据库文件会在首次使用时自动创建，如果路径中的目录不存在，系统会自动创建。

### 数据表结构

#### records 表

存储所有应用的历史记录。

```sql
CREATE TABLE IF NOT EXISTS records (
    id TEXT PRIMARY KEY,                    -- 记录ID（UUID格式）
    text TEXT NOT NULL,                     -- 记录文本内容
    metadata TEXT,                          -- 元数据（JSON格式）
    app_type TEXT DEFAULT 'voice-note',     -- 应用类型标识
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- 创建时间
);
```

**字段说明**:

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `id` | TEXT | 主键，UUID格式的唯一标识符 | `550e8400-e29b-41d4-a716-446655440000` |
| `text` | TEXT | 记录的文本内容 | `今天学习了Python的异步编程...` |
| `metadata` | TEXT | JSON格式的元数据 | `{"language": "zh-CN", "duration": 120}` |
| `app_type` | TEXT | 应用类型标识 | `voice-note`, `voice-chat`, `voice-zen` |
| `created_at` | TIMESTAMP | 记录创建时间 | `2026-01-03 14:30:00` |

**应用类型 (app_type)**:

- `voice-note`: 语音笔记应用
- `voice-chat`: 智能助手应用
- `voice-zen`: 禅应用

**元数据 (metadata) 结构**:

元数据字段存储为 JSON 字符串，常见字段包括：

```json
{
  "language": "zh-CN",           // 语言
  "duration": 120,                // 时长（秒）
  "summary": "摘要文本",          // 智能摘要（如果有）
  "asr_provider": "volcano",      // ASR提供商
  "model": "gpt-4",               // LLM模型（对话记录）
  "messages_count": 5             // 消息数量（对话记录）
}
```

### 索引设计

SQLite 会自动为主键创建索引。为提高查询性能，建议为常用查询字段创建索引：

```sql
-- 按应用类型和创建时间查询（已通过ORDER BY优化）
-- 如需进一步优化，可创建组合索引：
CREATE INDEX IF NOT EXISTS idx_records_app_type_created 
ON records(app_type, created_at DESC);
```

### 代码实现

**位置**: `src/providers/storage/sqlite.py`

**核心类**: `SQLiteStorageProvider`

**关键方法**:

```python
class SQLiteStorageProvider(BaseStorageProvider):
    """SQLite 存储提供商"""
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化数据库连接和表结构"""
        
    def save_record(self, text: str, metadata: Dict[str, Any]) -> str:
        """保存记录，返回记录ID"""
        
    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取记录"""
        
    def list_records(self, limit: int = 100, offset: int = 0, 
                     app_type: Optional[str] = None) -> list[Dict[str, Any]]:
        """列出记录，支持分页和应用类型筛选"""
        
    def update_record(self, record_id: str, text: str, 
                      metadata: Dict[str, Any]) -> bool:
        """更新记录（用于增量保存）"""
        
    def delete_record(self, record_id: str) -> bool:
        """删除单条记录"""
        
    def delete_records(self, record_ids: list[str]) -> int:
        """批量删除记录"""
        
    def count_records(self, app_type: Optional[str] = None) -> int:
        """获取记录总数"""
```

### 数据迁移

系统支持自动迁移，当检测到表结构变化时会自动添加新字段：

```python
# 检查是否需要迁移：为旧记录添加app_type字段
cursor.execute("PRAGMA table_info(records)")
columns = [col[1] for col in cursor.fetchall()]
if 'app_type' not in columns:
    cursor.execute('ALTER TABLE records ADD COLUMN app_type TEXT DEFAULT "voice-note"')
```

---

## ChromaDB 向量数据库

### 概述

ChromaDB 是用于知识库服务的向量数据库，存储文档的向量表示，支持语义搜索和检索增强生成（RAG）。

### 存储配置

**存储路径**: `./data/knowledge/chroma/`

**集合名称**: `mindvoice_knowledge`

**Embedding 模型**: `all-MiniLM-L6-v2` (sentence-transformers)

### 数据模型

#### 集合结构

ChromaDB 使用集合（Collection）来组织数据。每个文档会被分割成多个文本块（chunks），每个块对应一个向量。

**集合字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | TEXT | 文本块ID | `{file_id}_chunk_{index}` |
| `embedding` | VECTOR | 文本向量（384维） | `[0.123, -0.456, ...]` |
| `document` | TEXT | 文本块内容 | `文档的实际文本内容` |
| `metadata` | JSON | 元数据 | 见下方说明 |

**元数据 (metadata) 结构**:

```json
{
  "file_id": "550e8400-e29b-41d4-a716-446655440000",  // 文件唯一ID
  "filename": "example.md",                            // 原始文件名
  "chunk_index": 0,                                    // 块索引
  "total_chunks": 10                                   // 文件总块数
}
```

#### 文本分块策略

文档上传时会自动分块，默认参数：

- **块大小 (chunk_size)**: 500 字符
- **重叠大小 (chunk_overlap)**: 50 字符
- **分块策略**: 优先在句子边界分割（。！？\n\n 等）

**分块算法**:

```python
def _chunk_text(text: str, chunk_size: int = 500, 
                chunk_overlap: int = 50) -> List[str]:
    """文本分块，优先在句子边界分割"""
```

### 文件存储

原始文件存储在：`./data/knowledge/files/{file_id}_{filename}`

文件ID格式：`{file_id}_{filename}`，例如：`550e8400-...-0000_example.md`

### 代码实现

**位置**: `src/services/knowledge_service.py`

**核心类**: `KnowledgeService`

**关键方法**:

```python
class KnowledgeService:
    """知识库服务"""
    
    def __init__(self, storage_path: str = "./data/knowledge",
                 embedding_model: str = "all-MiniLM-L6-v2",
                 collection_name: str = "mindvoice_knowledge",
                 lazy_load: bool = True):
        """初始化知识库服务"""
        
    async def upload_file(self, filename: str, content: str,
                          metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """上传文件到知识库（自动分块和向量化）"""
        
    async def search(self, query: str, top_k: int = 3,
                     filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """语义搜索知识库"""
        
    async def list_files(self) -> List[Dict[str, Any]]:
        """列出所有文件"""
        
    async def get_file_content(self, file_id: str) -> Optional[str]:
        """获取文件原始内容"""
        
    async def delete_file(self, file_id: str) -> bool:
        """删除文件及其所有文本块"""
```

### 向量化流程

1. **文本分块**: 将文档分割成固定大小的文本块
2. **向量生成**: 使用 sentence-transformers 模型生成向量
3. **存储**: 将向量、文本和元数据存储到 ChromaDB
4. **检索**: 查询时生成查询向量，进行相似度搜索

---

## 数据模型设计

### SQLite 记录模型

```python
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "text": "记录文本内容",
    "metadata": {
        "language": "zh-CN",
        "duration": 120,
        "summary": "智能摘要",
        "app_type": "voice-note"
    },
    "app_type": "voice-note",
    "created_at": "2026-01-03 14:30:00"
}
```

### ChromaDB 向量记录模型

```python
{
    "id": "550e8400-...-0000_chunk_0",
    "embedding": [0.123, -0.456, ...],  # 384维向量
    "document": "文本块内容",
    "metadata": {
        "file_id": "550e8400-...-0000",
        "filename": "example.md",
        "chunk_index": 0,
        "total_chunks": 10
    }
}
```

---

## 存储提供商架构

### 抽象基类

**位置**: `src/core/base.py`

```python
class StorageProvider(ABC):
    """存储提供商抽象基类"""
    
    @abstractmethod
    def save_record(self, text: str, metadata: Dict[str, Any]) -> str:
        """保存记录"""
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
```

### 实现类层次

```
StorageProvider (抽象基类)
    └── BaseStorageProvider (基类实现)
            └── SQLiteStorageProvider (SQLite实现)
```

### 初始化流程

**位置**: `src/services/voice_service.py`

```python
def _initialize_providers(self):
    """初始化存储提供商"""
    storage_config = {
        'path': self.config.get('storage.path', '~/.voice_assistant/history.db')
    }
    self.storage_provider = SQLiteStorageProvider()
    self.storage_provider.initialize(storage_config)
```

### 扩展新的存储提供商

要实现新的存储提供商（如 PostgreSQL、MySQL 等），需要：

1. 继承 `BaseStorageProvider` 或直接实现 `StorageProvider`
2. 实现所有抽象方法
3. 在 `src/providers/storage/__init__.py` 中注册
4. 在配置文件中指定使用的提供商

---

## API 接口

### 历史记录 API

**位置**: `src/api/server.py`

#### 保存记录

```http
POST /api/records
Content-Type: application/json

{
  "text": "记录内容",
  "metadata": {
    "app_type": "voice-note",
    "language": "zh-CN"
  }
}
```

**响应**:

```json
{
  "success": true,
  "record_id": "550e8400-...-0000",
  "message": "记录已保存"
}
```

#### 获取记录

```http
GET /api/records/{record_id}
```

**响应**:

```json
{
  "success": true,
  "record": {
    "id": "550e8400-...-0000",
    "text": "记录内容",
    "metadata": {},
    "app_type": "voice-note",
    "created_at": "2026-01-03 14:30:00"
  }
}
```

#### 列出记录

```http
GET /api/records?limit=20&offset=0&app_type=voice-note
```

**查询参数**:

- `limit`: 返回记录数量（默认 20）
- `offset`: 偏移量（默认 0）
- `app_type`: 应用类型筛选（可选）

**响应**:

```json
{
  "success": true,
  "records": [...],
  "total": 100,
  "limit": 20,
  "offset": 0
}
```

#### 删除记录

```http
DELETE /api/records/{record_id}
```

**响应**:

```json
{
  "success": true,
  "message": "记录已删除"
}
```

#### 批量删除记录

```http
POST /api/records/batch-delete
Content-Type: application/json

{
  "record_ids": ["id1", "id2", "id3"]
}
```

### 知识库 API

#### 上传文件

```http
POST /api/knowledge/upload
Content-Type: multipart/form-data

file: (文件)
```

**响应**:

```json
{
  "success": true,
  "file_id": "550e8400-...-0000",
  "filename": "example.md",
  "chunks": 10,
  "size": 5000
}
```

#### 搜索

```http
POST /api/knowledge/search
Content-Type: application/json

{
  "query": "搜索内容",
  "top_k": 3
}
```

**响应**:

```json
{
  "success": true,
  "results": [
    {
      "id": "file_id_chunk_0",
      "content": "匹配的文本内容",
      "metadata": {...},
      "score": 0.95,
      "source": "example.md"
    }
  ]
}
```

#### 列出文件

```http
GET /api/knowledge/files
```

#### 删除文件

```http
DELETE /api/knowledge/files/{file_id}
```

---

## 数据迁移与维护

### SQLite 数据库迁移

系统支持自动迁移，当表结构发生变化时会自动检测并添加新字段。

**手动迁移示例**:

```python
# 连接数据库
conn = sqlite3.connect('history.db')
cursor = conn.cursor()

# 添加新字段
cursor.execute('ALTER TABLE records ADD COLUMN new_field TEXT')

# 提交更改
conn.commit()
conn.close()
```

### 数据库备份

#### SQLite 备份

```bash
# 简单备份（复制文件）
cp ~/.voice_assistant/history.db ~/.voice_assistant/history.db.backup

# 使用 SQLite 备份命令（推荐）
sqlite3 ~/.voice_assistant/history.db ".backup ~/.voice_assistant/history.db.backup"
```

#### ChromaDB 备份

```bash
# 备份整个知识库目录
tar -czf knowledge_backup.tar.gz ./data/knowledge/
```

### 数据库清理

#### 清理旧记录

```python
# 删除30天前的记录
DELETE FROM records 
WHERE created_at < datetime('now', '-30 days');
```

#### 清理知识库

通过 API 删除文件，系统会自动清理相关的向量数据。

### 数据导出

#### 导出 SQLite 数据

```bash
# 导出为 CSV
sqlite3 -header -csv history.db "SELECT * FROM records;" > records.csv

# 导出为 SQL
sqlite3 history.db .dump > backup.sql
```

---

## 性能优化

### SQLite 优化

1. **连接管理**: 每次操作后及时关闭连接，避免连接泄漏
2. **批量操作**: 使用事务批量插入/删除
3. **索引优化**: 为常用查询字段创建索引
4. **PRAGMA 设置**: 调整 SQLite 性能参数

```python
# 性能优化 PRAGMA
conn.execute("PRAGMA journal_mode = WAL")  # WAL模式提高并发性能
conn.execute("PRAGMA synchronous = NORMAL")  # 平衡性能和数据安全
conn.execute("PRAGMA cache_size = -64000")  # 64MB缓存
```

### ChromaDB 优化

1. **延迟加载**: 使用 `lazy_load=True` 避免启动时加载模型
2. **异步处理**: 向量生成使用线程池执行，不阻塞事件循环
3. **批量插入**: 文档上传时批量插入向量
4. **查询优化**: 合理设置 `top_k` 参数，避免返回过多结果

---

## 故障排查

### SQLite 常见问题

#### 1. 数据库文件锁定

**症状**: 出现 `database is locked` 错误

**原因**: 连接未正确关闭

**解决**:
- 确保每次操作后调用 `conn.close()`
- 使用上下文管理器确保连接关闭

```python
with sqlite3.connect(db_path) as conn:
    cursor = conn.cursor()
    cursor.execute(...)
    conn.commit()
```

#### 2. 数据库文件不存在

**症状**: `no such file or directory`

**解决**: 系统会自动创建目录和文件，如果仍有问题，检查权限

#### 3. 字符编码问题

**症状**: 中文字符显示乱码

**解决**: 确保使用 UTF-8 编码

```python
# 写入时使用 ensure_ascii=False
json.dumps(metadata, ensure_ascii=False)

# 读取时使用 UTF-8
with open(file, 'r', encoding='utf-8') as f:
    content = f.read()
```

### ChromaDB 常见问题

#### 1. 模型加载失败

**症状**: `ImportError: sentence-transformers 未安装`

**解决**: 安装依赖

```bash
pip install sentence-transformers chromadb
```

#### 2. 向量维度不匹配

**症状**: 查询时出现维度错误

**解决**: 确保使用相同的 Embedding 模型

#### 3. 磁盘空间不足

**症状**: 文件上传失败

**解决**: 检查磁盘空间，清理不需要的文件

### 调试技巧

1. **查看数据库内容**:

```bash
# SQLite
sqlite3 ~/.voice_assistant/history.db
.tables
SELECT * FROM records LIMIT 10;
```

2. **查看日志**: 检查日志文件了解详细错误信息

3. **测试连接**:

```python
# 测试 SQLite 连接
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM records")
print(cursor.fetchone())
conn.close()
```

---

## 总结

MindVoice 项目使用两种数据库系统：

- **SQLite**: 轻量级、零配置的关系数据库，用于历史记录存储
- **ChromaDB**: 高性能向量数据库，用于知识库的语义搜索

两种数据库各司其职，通过统一的存储提供商接口进行抽象，便于扩展和维护。

**关键特性**:

- ✅ 自动表结构迁移
- ✅ 支持按应用类型筛选
- ✅ 分页查询支持
- ✅ 批量操作支持
- ✅ 向量语义搜索
- ✅ 延迟加载优化

---

**文档版本**: 1.0  
**最后更新**: 2026-01-03  
**维护者**: MindVoice 开发团队


