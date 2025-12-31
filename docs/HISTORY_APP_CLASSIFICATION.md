# 历史记录应用分类功能

## 概述

历史记录现在支持按应用分类显示，用户可以筛选查看不同应用保存的记录。

## 功能特点

### 🎯 核心功能

1. **自动分类** - 记录保存时自动标记应用类型
2. **筛选查看** - 支持按应用类型筛选历史记录
3. **视觉标识** - 每条记录显示应用标签
4. **独立统计** - 各应用记录数独立统计

### 📊 支持的应用类型

| 应用类型 | 标识 | 颜色 | 说明 |
|---------|------|------|------|
| `voice-note` | 📝 语音笔记 | 蓝色 | 语音转文字记录 |
| `voice-chat` | 💬 语音助手 | 紫色 | 语音对话记录 |

## 使用指南

### 查看历史记录

1. 点击侧边栏的"历史记录"
2. 使用顶部筛选器切换应用：
   - **📚 全部** - 显示所有应用的记录
   - **📝 语音笔记** - 只显示语音笔记的记录
   - **💬 语音助手** - 只显示语音助手的记录

### 记录标识

每条历史记录都会显示：
- **应用标签** - 彩色标签，标识记录来源
- **创建时间** - 记录保存的时间
- **内容预览** - 记录的文本内容（最多150字）

### 示例界面

```
┌─────────────────────────────────────────┐
│  历史记录                50 条记录       │
├─────────────────────────────────────────┤
│  [📚 全部] [📝 语音笔记] [💬 语音助手]  │← 筛选器
├─────────────────────────────────────────┤
│  ☑ [📝 语音笔记] 2024年12月31日 15:30   │
│     这是一条语音笔记的内容...          │
│                                         │
│  ☐ [💬 语音助手] 2024年12月31日 14:20   │
│     用户：你好 AI：您好，有什么...     │
└─────────────────────────────────────────┘
```

## 技术实现

### 数据库Schema

```sql
CREATE TABLE records (
    id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    metadata TEXT,
    app_type TEXT DEFAULT 'voice-note',  -- 新增字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**自动迁移：**
- 系统会自动为旧记录添加 `app_type` 字段
- 默认值为 `'voice-note'`
- 无需手动数据迁移

### API接口

#### 查询历史记录（支持筛选）

```http
GET /api/records?limit=20&offset=0&app_type=voice-note

参数:
- limit: 返回记录数量（默认50）
- offset: 偏移量（默认0）
- app_type: 应用类型筛选（可选）
  - 'voice-note': 只返回语音笔记
  - 'voice-chat': 只返回语音助手
  - 'all' 或 不传: 返回所有记录

响应:
{
  "success": true,
  "records": [
    {
      "id": "xxx",
      "text": "...",
      "app_type": "voice-note",
      "created_at": "2024-12-31T15:30:00"
    }
  ],
  "total": 50,
  "limit": 20,
  "offset": 0
}
```

#### 保存记录（自动标记应用类型）

```http
POST /api/text/save

请求体:
{
  "text": "记录内容",
  "app_type": "voice-note"  // 应用类型
}

响应:
{
  "success": true,
  "record_id": "xxx",
  "message": "文本已保存"
}
```

### 前端组件

#### HistoryView 更新

```tsx
<HistoryView
  records={records}
  loading={loading}
  total={total}
  currentPage={currentPage}
  recordsPerPage={20}
  appFilter="all"  // 新增：当前筛选器
  onLoadRecord={handleLoad}
  onDeleteRecords={handleDelete}
  onPageChange={handlePageChange}  // 支持传入筛选参数
/>
```

**新增Props：**
- `appFilter?: 'all' | 'voice-note' | 'voice-chat'` - 当前筛选状态
- `onPageChange: (page: number, filter?: AppFilter) => void` - 支持筛选参数

#### 自动保存时标记应用

```typescript
// 在 VoiceNote 中保存
const saveText = async () => {
  await fetch('/api/text/save', {
    method: 'POST',
    body: JSON.stringify({ 
      text: content,
      app_type: 'voice-note'  // 自动标记
    })
  });
};

// 在 VoiceChat 中保存
const saveText = async () => {
  await fetch('/api/text/save', {
    method: 'POST',
    body: JSON.stringify({ 
      text: content,
      app_type: 'voice-chat'  // 自动标记
    })
  });
};
```

## 样式定制

### 应用标签

```css
.app-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 600;
  border: 1px solid;
}

/* 不同应用的颜色 */
.app-badge[style*="color: #3b82f6"] {  /* 语音笔记：蓝色 */
  background: rgba(59, 130, 246, 0.1);
  border-color: rgba(59, 130, 246, 0.3);
}

.app-badge[style*="color: #8b5cf6"] {  /* 语音助手：紫色 */
  background: rgba(139, 92, 246, 0.1);
  border-color: rgba(139, 92, 246, 0.3);
}
```

### 筛选器按钮

```css
.filter-btn {
  padding: 8px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: all var(--transition-base);
}

.filter-btn-active {
  background: var(--color-primary);
  color: var(--color-text-inverse);
  border-color: var(--color-primary);
}
```

## 扩展新应用

### 步骤 1: 定义应用类型

在 `HistoryView.tsx` 中添加新的应用类型：

```typescript
const APP_TYPE_CONFIG = {
  'voice-note': { label: '语音笔记', icon: '📝', color: '#3b82f6' },
  'voice-chat': { label: '语音助手', icon: '💬', color: '#8b5cf6' },
  'your-new-app': { label: '新应用', icon: '🎨', color: '#10b981' },  // 新增
};

const APP_FILTERS = [
  { value: 'all', label: '全部', icon: '📚' },
  { value: 'voice-note', label: '语音笔记', icon: '📝' },
  { value: 'voice-chat', label: '语音助手', icon: '💬' },
  { value: 'your-new-app', label: '新应用', icon: '🎨' },  // 新增
];
```

### 步骤 2: 保存时传入应用类型

在新应用中保存记录时：

```typescript
await fetch('/api/text/save', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ 
    text: content,
    app_type: 'your-new-app'  // 使用新的应用类型
  })
});
```

### 步骤 3: 更新类型定义

```typescript
type AppFilter = 'all' | 'voice-note' | 'voice-chat' | 'your-new-app';
```

## 数据统计

### 按应用统计记录数

```typescript
// 获取各应用的记录总数
const getAppStats = async () => {
  const voiceNoteCount = await fetch('/api/records?limit=0&app_type=voice-note');
  const voiceChatCount = await fetch('/api/records?limit=0&app_type=voice-chat');
  
  return {
    'voice-note': voiceNoteCount.total,
    'voice-chat': voiceChatCount.total,
  };
};
```

## 常见问题

### Q: 旧记录会自动分类吗？

A: 旧记录会自动标记为 `voice-note`（默认值）。如需修改，可以手动更新数据库：

```sql
UPDATE records SET app_type = 'voice-chat' WHERE id = 'xxx';
```

### Q: 如何批量修改记录的应用类型？

A: 可以通过SQL批量更新：

```sql
-- 将特定时间段的记录标记为voice-chat
UPDATE records 
SET app_type = 'voice-chat' 
WHERE created_at BETWEEN '2024-12-01' AND '2024-12-31';
```

### Q: 删除记录会受应用筛选影响吗？

A: 不会。删除操作与筛选器无关，只要记录被选中就能删除。

### Q: 筛选器状态会保存吗？

A: 当前版本不保存筛选器状态，刷新后会重置为"全部"。未来版本可能支持保存偏好设置。

## 性能优化

### 数据库索引

建议为 `app_type` 字段添加索引：

```sql
CREATE INDEX idx_app_type ON records(app_type);
CREATE INDEX idx_app_type_created_at ON records(app_type, created_at DESC);
```

### 查询优化

```python
# 使用参数化查询，避免SQL注入
if app_type:
    cursor.execute('''
        SELECT * FROM records 
        WHERE app_type = ?
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    ''', (app_type, limit, offset))
```

## 测试清单

- [ ] 保存记录时正确标记应用类型
- [ ] 筛选器正确显示各应用记录
- [ ] 应用标签正确显示
- [ ] 切换筛选器时记录正确更新
- [ ] 旧记录正确显示为默认类型
- [ ] 批量删除在不同筛选器下正常工作
- [ ] 分页在不同筛选器下正常工作
- [ ] 记录总数统计准确

## 更新日志

**v1.0.0 (2025-12-31)**
- ✅ 初始发布
- ✅ 支持voice-note和voice-chat分类
- ✅ 添加筛选器UI
- ✅ 自动数据库迁移
- ✅ 应用标签显示

---

**维护者:** 开发团队  
**最后更新:** 2025-12-31

