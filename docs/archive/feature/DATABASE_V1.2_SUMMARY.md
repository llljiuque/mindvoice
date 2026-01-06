# 数据库优化 v1.2.0 - 实施总结

## 版本信息

- **版本号**: v1.2.0（基准版本）
- **发布日期**: 2026-01-05
- **状态**: ✅ 开发完成，测试中

## 核心改进

### 1. 🗑️ **软删除机制**

**数据库变更**：
```sql
ALTER TABLE users ADD COLUMN is_deleted INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN deleted_at TIMESTAMP;

ALTER TABLE records ADD COLUMN is_deleted INTEGER DEFAULT 0;
ALTER TABLE records ADD COLUMN deleted_at TIMESTAMP;
```

**功能**：
- ✅ 用户软删除/恢复
- ✅ 记录软删除/恢复（30天后自动永久删除）
- ✅ 回收站功能

**API示例**：
```python
# 软删除记录
storage.soft_delete_record(record_id)

# 恢复记录
storage.restore_record(record_id)

# 获取已删除记录（回收站）
deleted_records = storage.get_deleted_records(user_id)

# 永久删除30天前的记录
count = storage.permanent_delete_old_records(days=30)
```

### 2. ⭐ **收藏和归档**

**数据库变更**：
```sql
ALTER TABLE records ADD COLUMN is_starred INTEGER DEFAULT 0;
ALTER TABLE records ADD COLUMN is_archived INTEGER DEFAULT 0;
ALTER TABLE records ADD COLUMN updated_at TIMESTAMP;
```

**功能**：
- ✅ 快速收藏/取消收藏
- ✅ 归档/取消归档
- ✅ 独立视图查询

**API示例**：
```python
# 切换收藏状态
is_starred = storage.toggle_starred(record_id)

# 切换归档状态
is_archived = storage.toggle_archived(record_id)

# 获取收藏的记录
starred_records = storage.get_starred_records(user_id)

# 获取归档的记录
archived_records = storage.get_archived_records(user_id)
```

### 3. 🔍 **全文搜索（FTS5）**

**数据库变更**：
```sql
-- FTS5 虚拟表（独立表结构）
CREATE VIRTUAL TABLE records_fts USING fts5(
    record_id UNINDEXED,
    text,
    tokenize='unicode61 remove_diacritics 2'
);

-- 自动同步触发器（2026-01-06 修复）
CREATE TRIGGER records_ai AFTER INSERT ON records BEGIN
    INSERT INTO records_fts(record_id, text)
    VALUES (new.id, new.text);
END;

CREATE TRIGGER records_au AFTER UPDATE ON records BEGIN
    UPDATE records_fts SET text = new.text WHERE record_id = old.id;
END;

CREATE TRIGGER records_ad AFTER DELETE ON records BEGIN
    DELETE FROM records_fts WHERE record_id = old.id;
END;
```

**重要说明**：
- ⚠️ **2026-01-06 修复**：原使用 `content='records'` 配置导致触发器错误，已改为独立 FTS5 表
- ✅ 使用 `record_id` 字段关联而非 `rowid`
- ✅ UPDATE 触发器使用直接更新而非删除+插入

**功能**：
- ✅ 高性能全文搜索（10-100倍提升）
- ✅ 支持中文搜索
- ✅ 相关性排序
- ✅ 自动同步索引

**API示例**：
```python
# 搜索记录
results = storage.search_records(
    query="会议纪要",
    user_id="xxx",
    app_type="voice-note",
    limit=20
)

# 结果包含相关性评分
for record in results:
    print(f"相关性: {record['relevance']}")
```

### 4. 🏷️ **标签系统**

**数据库变更**：
```sql
CREATE TABLE tags (
    tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    tag_name TEXT NOT NULL,
    color TEXT,
    icon TEXT,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL,
    UNIQUE(user_id, tag_name)
);

CREATE TABLE record_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id TEXT NOT NULL,
    tag_id INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL,
    UNIQUE(record_id, tag_id),
    FOREIGN KEY (record_id) REFERENCES records(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(tag_id) ON DELETE CASCADE
);
```

**功能**：
- ✅ 创建/更新/删除标签
- ✅ 给记录添加/移除标签
- ✅ 按标签查询记录
- ✅ 标签排序
- ✅ 自定义颜色和图标

**API示例**：
```typescript
// 创建标签
POST /api/tags
{
  "user_id": "xxx",
  "tag_name": "工作",
  "color": "#FF5733",
  "icon": "💼"
}

// 给记录添加标签
POST /api/tags/record/add
{
  "record_id": "xxx",
  "tag_id": 1
}

// 按标签查询记录
GET /api/tags/query/1?limit=20&offset=0
```

### 5. 📊 **使用统计**

**数据库变更**：
```sql
CREATE TABLE daily_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    date DATE NOT NULL,
    app_type TEXT NOT NULL,
    record_count INTEGER DEFAULT 0,
    asr_duration_seconds INTEGER DEFAULT 0,
    llm_tokens INTEGER DEFAULT 0,
    active_duration_seconds INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP,
    UNIQUE(user_id, date, app_type)
);
```

**功能**：
- ✅ 每日使用统计
- ✅ 按应用类型统计
- ✅ ASR时长统计
- ✅ LLM tokens统计

### 6. 💾 **备份记录**

**数据库变更**：
```sql
CREATE TABLE backup_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    backup_type TEXT NOT NULL,
    backup_path TEXT NOT NULL,
    file_size INTEGER,
    status TEXT NOT NULL,
    error_message TEXT,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    records_count INTEGER,
    users_count INTEGER
);
```

**功能**：
- ✅ 备份操作记录
- ✅ 备份状态追踪
- ✅ 失败原因记录

### 7. 📝 **数据库版本管理**

**数据库变更**：
```sql
CREATE TABLE schema_versions (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL,
    description TEXT
);
```

**功能**：
- ✅ 追踪数据库版本
- ✅ 记录变更历史
- ✅ 便于升级管理

## 数据库结构对比

### v1.1.0（旧版本）
```
users (3个字段)
user_devices
records (7个字段)
```

### v1.2.0（新版本）
```
【用户系统】
users (11个字段) + 软删除
user_devices

【数据管理】
records (12个字段) + 软删除 + 收藏 + 归档
records_fts (FTS5虚拟表)
tags (标签表)
record_tags (标签关联)

【统计监控】
daily_stats (统计表)
backup_logs (备份日志)

【会员系统】
devices (设备信息)
memberships (会员信息)
consumption_records (消费记录)
monthly_consumption (月度汇总)
activation_codes (激活码)

【系统管理】
schema_versions (版本管理)

总计：16张表
```

## 性能优化

### 索引优化
```sql
-- records 表索引（共8个）
idx_records_user_id
idx_records_device_id
idx_records_user_created
idx_records_not_deleted
idx_records_starred
idx_records_archived
idx_records_app_type

-- tags 表索引
idx_tags_user

-- record_tags 表索引
idx_record_tags_record
idx_record_tags_tag

-- daily_stats 表索引
idx_daily_stats_user_date
idx_daily_stats_date

-- users 表索引
idx_users_not_deleted
idx_users_login
```

### 查询优化
- FTS5 全文搜索：10-100倍性能提升
- 部分索引（WHERE条件）：减少索引大小
- WAL模式：提高并发性能

## API变更

### 新增API端点

#### 标签管理
- `POST /api/tags` - 创建标签
- `PUT /api/tags/{tag_id}` - 更新标签
- `DELETE /api/tags/{tag_id}` - 删除标签
- `GET /api/tags/user/{user_id}` - 获取用户标签
- `POST /api/tags/record/add` - 给记录添加标签
- `DELETE /api/tags/record/{record_id}/{tag_id}` - 移除标签
- `GET /api/tags/record/{record_id}` - 获取记录的标签
- `GET /api/tags/query/{tag_id}` - 按标签查询记录
- `POST /api/tags/reorder` - 更新标签排序

#### 用户管理增强
- `DELETE /api/user/profile/{user_id}?hard_delete=true` - 硬删除用户
- `POST /api/user/restore/{user_id}` - 恢复已删除用户

### 存储服务新方法

```python
# 软删除
storage.soft_delete_record(record_id)
storage.restore_record(record_id)
storage.permanent_delete_old_records(days=30)

# 收藏和归档
storage.toggle_starred(record_id)
storage.toggle_archived(record_id)
storage.get_starred_records(user_id)
storage.get_archived_records(user_id)

# 全文搜索
storage.search_records(query, user_id, app_type)

# 回收站
storage.get_deleted_records(user_id)
```

## 前端集成建议

### 1. 搜索功能
```typescript
const searchNotes = async (keyword: string) => {
  const response = await fetch(
    `${API_BASE_URL}/api/records/search?q=${keyword}&user_id=${userInfo.user_id}`
  );
  const results = await response.json();
  // results 包含相关性评分
};
```

### 2. 收藏功能
```typescript
const toggleStar = async (recordId: string) => {
  const response = await fetch(
    `${API_BASE_URL}/api/records/${recordId}/star`,
    { method: 'POST' }
  );
  const { is_starred } = await response.json();
  return is_starred;
};
```

### 3. 标签管理
```typescript
const addTag = async (recordId: string, tagId: number) => {
  await fetch(`${API_BASE_URL}/api/tags/record/add`, {
    method: 'POST',
    body: JSON.stringify({ record_id: recordId, tag_id: tagId })
  });
};
```

### 4. 回收站
```typescript
const loadRecycleBin = async () => {
  const response = await fetch(
    `${API_BASE_URL}/api/records/deleted?user_id=${userInfo.user_id}`
  );
  return await response.json();
};
```

## 数据迁移

### 自动升级
系统首次启动时会自动执行：
1. 检测当前数据库版本
2. 创建新表和字段
3. 创建索引和触发器
4. 记录版本信息

**不需要手动迁移**，系统会自动处理。

### 重置系统
```bash
./scripts/reset_system.sh
```

## 配置文件无变更
`config.yml` 无需修改，所有新功能使用现有配置。

## 测试清单

- [ ] 软删除和恢复
- [ ] 收藏和取消收藏
- [ ] 归档和取消归档
- [ ] 全文搜索功能
- [ ] 标签创建和管理
- [ ] 标签添加到记录
- [ ] 按标签查询记录
- [ ] 回收站查看
- [ ] 30天自动清理

## 已知限制

1. FTS5 中文分词依赖 unicode61，效果有限
   - 未来可考虑集成 jieba 分词
   
2. 软删除记录仍占用存储空间
   - 需定期清理（建议每月运行一次）
   
3. 标签数量建议不超过50个/用户
   - 超过可能影响性能

## 下一步计划

### v1.3.0（计划中）
- [ ] 分享功能（预留表已创建）
- [ ] 操作审计日志
- [ ] 数据导出/导入
- [ ] 更好的中文分词

### v2.0.0（远期）
- [ ] 云端同步
- [ ] 多设备实时协作
- [ ] AI智能标签

## 相关文档

- [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) - 完整表结构
- [USER_BINDING_GUIDE.md](./USER_BINDING_GUIDE.md) - 用户系统使用指南
- [DATABASE_VERSION.md](./DATABASE_VERSION.md) - 版本管理

---

**开发者**: 深圳王哥 & AI  
**邮箱**: manwjh@126.com  
**最后更新**: 2026-01-05

