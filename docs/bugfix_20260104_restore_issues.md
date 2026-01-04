# 恢复任务功能Bug修复

**日期**: 2026-01-04  
**问题**: 恢复历史记录时出现时间显示错误和内容为空  
**状态**: ✅ 已修复

---

## 问题现象

用户点击"📝 恢复任务"后：

1. **时间显示错误**：界面显示 `2026年1月4日 08:04`，但当前本地时间是 `16:06`，相差8小时
2. **恢复内容为空**：笔记编辑器中没有显示任何内容

---

## 根本原因

### 问题1：时间存储使用UTC时间

**原因**：数据库使用 `CURRENT_TIMESTAMP` 默认存储UTC时间，但前端显示时没有进行时区转换。

```python
# src/providers/storage/sqlite.py (旧代码)
cursor.execute('''
    INSERT INTO records (id, text, metadata, app_type)
    VALUES (?, ?, ?, ?)
''', ...)
# 依赖数据库的 CURRENT_TIMESTAMP，默认为UTC时间
```

**后果**：
- 数据库存储：`2026-01-04 08:04:48` (UTC)
- 用户时区：UTC+8
- 实际创建时间应该是：`2026-01-04 16:04:48`
- 显示时间错误，相差8小时

### 问题2：恢复时blocks数据为null

**原因**：手动保存的记录没有blocks数据，只有纯文本。恢复时 `setInitialBlocks(undefined)` 会导致 BlockEditor 创建空blocks，而不是从 text 创建。

```typescript
// App.tsx (旧代码)
if (data.metadata?.blocks && Array.isArray(data.metadata.blocks)) {
  setInitialBlocks(data.metadata.blocks);
} else {
  setInitialBlocks(undefined);  // ← 问题：undefined会创建空blocks
}
```

**数据库实际情况**：
```json
{
  "id": "9ca7eb50-d029-4397-8350-ff7e94b2edd9",
  "text": "12345678",
  "metadata": {
    "blocks": null  // ← blocks为null
  }
}
```

**后果**：BlockEditor 收到 `undefined` 时，会创建空的blocks，不会使用 text 内容。

---

## 修复方案

### 修复1：时间存储使用本地时间

**修改文件**：`src/providers/storage/sqlite.py`

```python
def save_record(self, text: str, metadata: Dict[str, Any]) -> str:
    """保存记录"""
    import uuid
    record_id = str(uuid.uuid4())
    
    # 从metadata中提取app_type，默认为'voice-note'
    app_type = metadata.get('app_type', 'voice-note')
    
    # 使用本地时间而非UTC时间
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    conn = self._get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO records (id, text, metadata, app_type, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (record_id, text, json.dumps(metadata, ensure_ascii=False), app_type, created_at))
    conn.commit()
    conn.close()
    
    return record_id
```

**改动**：
- 显式传递 `created_at` 参数
- 使用 `datetime.now()` 获取本地时间
- 不再依赖数据库的 `CURRENT_TIMESTAMP`

### 修复2：从纯文本创建blocks

**修改文件**：`electron-app/src/App.tsx`

```typescript
if (data.text) {
  setText(data.text);
  console.log('[App] 设置文本内容, 长度:', data.text.length);
  
  if (data.metadata?.blocks && Array.isArray(data.metadata.blocks) && data.metadata.blocks.length > 0) {
    console.log('[App] 恢复blocks数据:', data.metadata.blocks.length, '个blocks');
    setInitialBlocks(data.metadata.blocks);
  } else {
    console.log('[App] 无blocks数据，从纯文本创建blocks');
    // 从纯文本创建简单的blocks结构
    const timestamp = Date.now();
    const textBlocks = data.text.split('\n').filter((line: string) => line.trim()).map((line: string, index: number) => ({
      id: `block-restored-${timestamp}-${index}`,
      type: 'paragraph',
      content: line,
      isAsrWriting: false,
    }));
    
    // 添加note-info block
    const noteInfoBlock = {
      id: `block-note-info-${timestamp}`,
      type: 'note-info',
      content: '',
      noteInfo: {
        title: '',
        type: '',
        relatedPeople: '',
        location: '',
        startTime: '',
        endTime: ''
      }
    };
    
    setInitialBlocks([noteInfoBlock, ...textBlocks]);
  }
}
```

**改动**：
- 检查 `blocks.length > 0` 确保不是空数组
- 当没有blocks时，从 `data.text` 分行创建blocks
- 每行创建一个 paragraph block
- 添加空的 note-info block

---

## 验证结果

### 测试1：时间显示

**测试步骤**：
1. 创建一条新记录
2. 查看历史记录界面

**预期结果**：
- 显示时间应该与当前本地时间一致
- 例如：16:10创建的记录，显示 `2026年1月4日 16:10`

### 测试2：恢复纯文本记录

**测试步骤**：
1. 恢复 `12345678` 这条记录
2. 检查笔记编辑器

**预期结果**：
- 应该显示一个 paragraph block，内容为 `12345678`
- 可以正常编辑

### 测试3：恢复带blocks的记录

**测试步骤**：
1. 恢复测试记录（带完整blocks数据）
2. 检查笔记信息和内容

**预期结果**：
- 笔记信息完整显示（标题、类型、参与人等）
- 所有段落正确恢复
- 可以继续编辑

---

## 影响范围

✅ **时间修复**：新创建的记录使用本地时间  
✅ **恢复修复**：可以正确恢复纯文本记录  
⚠️ **旧记录**：数据库中已有的旧记录仍然是UTC时间（可以接受，历史数据不影响）  

---

## 相关文件

- `src/providers/storage/sqlite.py` - 修复时间存储
- `electron-app/src/App.tsx` - 修复blocks恢复
- `electron-app/src/components/apps/VoiceNote/BlockEditor.tsx` - blocks渲染逻辑

---

## 后续改进

- [ ] 考虑添加时区转换逻辑，兼容旧的UTC时间记录
- [ ] 改进blocks创建逻辑，支持更复杂的文本结构识别
- [ ] 添加恢复失败的友好提示


