# 数据库表结构文档

## 数据库技术选型

- **数据库**: SQLite 3
- **位置**: 由 `config.yml` 中的 `storage.data_dir` + `storage.database` 配置决定
- **共享机制**: 3个应用（voice-note, smart-chat, voice-zen）共享同一数据库，通过 `app_type` 字段区分

## records 表（用户绑定版本）

```sql
CREATE TABLE IF NOT EXISTS records (
    id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    metadata TEXT,
    app_type TEXT NOT NULL DEFAULT 'voice-note',
    user_id TEXT,
    device_id TEXT,
    created_at TIMESTAMP NOT NULL
);

-- 索引
CREATE INDEX idx_records_user_id ON records(user_id);
CREATE INDEX idx_records_device_id ON records(device_id);
CREATE INDEX idx_records_user_created ON records(user_id, created_at DESC);
```

### 字段说明

| 字段 | 类型 | 说明 |
|-----|------|------|
| `id` | TEXT | 记录ID，UUID v4 格式 |
| `text` | TEXT | 纯文本内容，用于搜索和预览 |
| `metadata` | TEXT | JSON 格式元数据（blocks、noteInfo 等）|
| `app_type` | TEXT | 应用类型（voice-note/smart-chat/voice-zen）|
| `user_id` | TEXT | ⭐ 用户ID（关联 users 表），可选 |
| `device_id` | TEXT | ⭐ 设备ID（关联 user_devices 表），可选 |
| `created_at` | TIMESTAMP | 创建时间，本地时间格式 `YYYY-MM-DD HH:MM:SS` |

## metadata 字段结构

```json
{
  "blocks": [
    {
      "id": "block-xxx",
      "type": "paragraph",
      "content": "段落内容",
      "startTime": 1704254400000,
      "endTime": 1704254410000,
      "isAsrWriting": false
    }
  ],
  "noteInfo": {
    "title": "会议纪要",
    "type": "会议",
    "relatedPeople": "张三, 李四",
    "location": "会议室A",
    "startTime": "2026-01-04 10:00:00",
    "endTime": "2026-01-04 11:30:00"
  },
  "language": "zh-CN",
  "provider": "volcano",
  "app_type": "voice-note"
}
```

## 数据库操作示例

### 创建记录

```python
import uuid
from datetime import datetime
import json

record_id = str(uuid.uuid4())
created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

cursor.execute('''
    INSERT INTO records (id, text, metadata, app_type, created_at)
    VALUES (?, ?, ?, ?, ?)
''', (record_id, text, json.dumps(metadata, ensure_ascii=False), app_type, created_at))
```

### 更新记录

```python
cursor.execute('''
    UPDATE records
    SET text = ?, metadata = ?
    WHERE id = ?
''', (text, json.dumps(metadata, ensure_ascii=False), record_id))
```

### 查询记录

```python
cursor.execute('''
    SELECT id, text, metadata, app_type, created_at
    FROM records
    WHERE id = ?
''', (record_id,))
```

### 列表查询

```python
cursor.execute('''
    SELECT id, text, metadata, app_type, created_at
    FROM records
    WHERE app_type = ?
    ORDER BY created_at DESC
    LIMIT ? OFFSET ?
''', (app_type, limit, offset))
```

## records_fts 表（全文搜索）

### FTS5 虚拟表

```sql
CREATE VIRTUAL TABLE records_fts USING fts5(
    record_id UNINDEXED,
    text,
    tokenize='unicode61 remove_diacritics 2'
);
```

### 自动同步触发器

```sql
-- 插入触发器
CREATE TRIGGER records_ai AFTER INSERT ON records BEGIN
    INSERT INTO records_fts(record_id, text)
    VALUES (new.id, new.text);
END;

-- 更新触发器
CREATE TRIGGER records_au AFTER UPDATE ON records BEGIN
    UPDATE records_fts SET text = new.text WHERE record_id = old.id;
END;

-- 删除触发器
CREATE TRIGGER records_ad AFTER DELETE ON records BEGIN
    DELETE FROM records_fts WHERE record_id = old.id;
END;
```

### 全文搜索示例

```python
# 搜索记录
cursor.execute('''
    SELECT r.id, r.text, r.metadata, r.app_type, r.created_at, f.rank
    FROM records r
    INNER JOIN records_fts f ON r.id = f.record_id
    WHERE records_fts MATCH ? AND r.is_deleted = 0
    ORDER BY f.rank
    LIMIT ?
''', (query, limit))
```

### 重要说明

- **独立表结构**: FTS5 表是独立的，不使用 `content='records'` 配置
- **record_id 关联**: 使用 `record_id` 字段与 `records.id` 关联
- **自动同步**: 触发器确保 FTS 索引与主表数据保持同步
- **性能提升**: 相比 LIKE 查询，FTS5 性能提升 10-100 倍

## 性能优化

### 推荐索引

```sql
-- 按创建时间倒序查询
CREATE INDEX idx_created_at ON records(created_at DESC);

-- 按应用类型筛选
CREATE INDEX idx_app_type ON records(app_type);

-- 组合索引
CREATE INDEX idx_app_type_created_at ON records(app_type, created_at DESC);

-- 用户相关索引
CREATE INDEX idx_records_user_created ON records(user_id, created_at DESC);
CREATE INDEX idx_records_not_deleted ON records(is_deleted, user_id);
```

## 数据备份

```bash
# 获取数据库路径（从config.yml读取）
DB_PATH=$(grep 'database:' config.yml | awk '{print $2}')

# 手动备份
cp "$DB_PATH" "${DB_PATH}.backup"

# 查看记录数
sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM records;"
```

## users 表（用户管理）

```sql
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    nickname TEXT,
    email TEXT,
    bio TEXT,
    avatar_url TEXT,
    login_count INTEGER DEFAULT 0,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- 索引
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active_login ON users(last_login_at DESC);
```

### 字段说明

| 字段 | 类型 | 说明 |
|-----|------|------|
| `user_id` | TEXT | 用户ID，UUID v4 格式 |
| `nickname` | TEXT | 昵称（可选，最长50字符） |
| `email` | TEXT | 邮箱（可选） |
| `bio` | TEXT | 个人简介（可选，最长500字符） |
| `avatar_url` | TEXT | 头像URL，相对路径（如 `images/xxx.png`） |
| `login_count` | INTEGER | 登录次数 |
| `last_login_at` | TIMESTAMP | 最后登录时间 |
| `created_at` | TIMESTAMP | 注册时间 |
| `updated_at` | TIMESTAMP | 最后更新时间 |

## user_devices 表（设备绑定）

```sql
CREATE TABLE IF NOT EXISTS user_devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    device_id TEXT NOT NULL UNIQUE,
    device_name TEXT,
    bound_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 索引
CREATE INDEX idx_user_devices_user_id ON user_devices(user_id);
CREATE INDEX idx_user_devices_device_id ON user_devices(device_id);
```

### 字段说明

| 字段 | 类型 | 说明 |
|-----|------|------|
| `id` | INTEGER | 自增主键 |
| `user_id` | TEXT | 用户ID（外键） |
| `device_id` | TEXT | 设备ID（唯一） |
| `device_name` | TEXT | 设备名称（可选） |
| `bound_at` | TIMESTAMP | 绑定时间 |

## 数据关系

```
users (1) ←─── (N) user_devices (N) ←─── (N) records
  ↓                                           ↑
  └─────────────── (1:N) ─────────────────────┘
```

- 一个用户可以绑定多个设备
- 一个设备只能绑定一个用户（UNIQUE约束）
- 一个用户可以创建多条记录
- 一条记录属于一个用户和一个设备

## 数据库初始化

数据库表和索引会在首次启动应用时自动创建：

1. 应用启动时调用 `_create_table()` 方法
2. 检查表是否存在，不存在则创建
3. 检查字段是否存在，不存在则添加（兼容性处理）
4. 创建所有必需的索引

**特性**：
- ✅ 自动创建表结构
- ✅ 自动添加缺失字段
- ✅ 自动创建索引
- ✅ 向后兼容（旧数据库自动升级）

## 数据库维护

### 重建数据库

```bash
./scripts/rebuild_database.sh
```

### 查看数据库信息

```bash
sqlite3 "$DB_PATH" ".schema records"
sqlite3 "$DB_PATH" ".schema users"
sqlite3 "$DB_PATH" ".schema user_devices"
sqlite3 "$DB_PATH" ".tables"
```

### 按用户统计记录数

```sql
SELECT u.user_id, u.nickname, COUNT(r.id) as record_count
FROM users u
LEFT JOIN records r ON u.user_id = r.user_id
GROUP BY u.user_id
ORDER BY record_count DESC;
```

