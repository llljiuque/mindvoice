# 从历史记录恢复任务功能

## 功能概述

"从历史记录恢复任务"允许用户从历史记录中恢复之前保存的笔记，继续编辑、生成小结或进行其他操作。

## 功能特性

### 1. 恢复任务按钮
- **位置**：历史记录列表中每条记录的右侧
- **文案**：`📝 恢复任务`（原来是"查看"）
- **提示**：鼠标悬停时显示"恢复此任务并继续编辑"

### 2. 恢复逻辑

#### 安全确认
- 如果当前有工作会话且有未保存内容，会弹出确认对话框：
  ```
  当前有未保存的内容，恢复历史任务将会覆盖当前内容。
  
  是否继续恢复？
  
  提示：您可以先点击"保存"或"新笔记"来保存当前内容。
  ```
- 用户可以选择：
  - **确定**：继续恢复，当前内容将被覆盖
  - **取消**：保持当前状态，不恢复

#### 恢复内容
恢复时会还原以下内容：
1. **文本内容**：完整的笔记文本
2. **Blocks 数据**：
   - 如果历史记录中有 blocks 数据（包含笔记信息、段落结构、小结等），完整恢复
   - 如果没有 blocks 数据，则以纯文本模式恢复
3. **工作会话**：自动启动工作会话，进入"记录中"状态

#### 恢复后状态
- 切换到"语音笔记"视图
- 启动工作会话（`isWorkSessionActive = true`）
- 清除任何草稿缓存
- 显示成功提示：
  ```
  ✅ 已恢复历史笔记，您可以继续编辑、生成小结或保存
  ```

### 3. 恢复后可用操作

恢复任务后，用户可以：
- **启动/停止 ASR**：继续进行语音识别，追加新内容
- **手动编辑**：直接编辑文本内容
- **生成小结**：对整个笔记内容生成 AI 小结
- **保存**：保存修改后的内容（会创建新记录，不覆盖原记录）
- **新笔记**：保存当前内容并开始新笔记
- **复制**：复制内容到剪贴板
- **退出**：退出工作会话，返回欢迎界面

## 技术实现

### 前端实现

#### HistoryView.tsx
```typescript
// 更新按钮文案和图标
<button
  className="history-btn history-btn-load"
  onClick={() => onLoadRecord(record.id)}
  title="恢复此任务并继续编辑"
  aria-label={`恢复记录 ${record.id}`}
>
  📝 恢复任务
</button>
```

#### App.tsx - loadRecord 函数
```typescript
const loadRecord = async (recordId: string) => {
  // 1. 检查 API 连接
  if (!apiConnected) {
    setToast({ message: 'API未连接，无法恢复任务', type: 'error' });
    return;
  }
  
  // 2. 安全确认（如果有未保存内容）
  if (isWorkSessionActive && text && text.trim()) {
    const confirmed = window.confirm('...');
    if (!confirmed) return;
  }
  
  // 3. 从后端获取记录
  const response = await fetch(`${API_BASE_URL}/api/records/${recordId}`);
  const data = await response.json();
  
  // 4. 恢复文本和 blocks
  setText(data.text);
  if (data.metadata?.blocks) {
    setInitialBlocks(data.metadata.blocks);
  } else {
    setInitialBlocks(undefined);
  }
  
  // 5. 清除草稿、切换视图、启动会话
  localStorage.removeItem('voiceNoteDraft');
  setActiveView('voice-note');
  startWorkSession('voice-note');
  
  // 6. 显示成功提示
  setToast({ message: '✅ 已恢复历史笔记...', type: 'success' });
};
```

### 后端实现

#### API 端点
```
GET /api/records/{record_id}
```

#### 返回数据结构
```json
{
  "id": "record_id",
  "text": "笔记内容...",
  "metadata": {
    "blocks": [
      {
        "id": "block-xxx",
        "type": "note-info",
        "content": "",
        "noteInfo": {
          "title": "会议纪要",
          "type": "会议",
          "relatedPeople": "张三, 李四",
          "location": "会议室A",
          "startTime": "2026-01-03 10:00:00",
          "endTime": "2026-01-03 11:30:00"
        }
      },
      {
        "id": "block-yyy",
        "type": "paragraph",
        "content": "段落内容...",
        "startTime": 1704254400000,
        "endTime": 1704254410000
      }
    ],
    "language": "zh-CN",
    "provider": "volcano",
    "app_type": "voice-note"
  },
  "app_type": "voice-note",
  "created_at": "2026-01-03T10:00:00"
}
```

### BlockEditor 处理

BlockEditor 组件通过 `initialBlocks` prop 接收恢复的数据：

```typescript
useEffect(() => {
  if (!isAsrActive) {
    if (initialBlocks && initialBlocks.length > 0) {
      // 恢复 blocks 结构
      const blocksWithBuffer = ensureBottomBufferBlock(initialBlocks);
      setBlocks(blocksWithBuffer);
    } else {
      // 使用纯文本创建 blocks
      const newBlocks = ensureBottomBufferBlock(createBlocksFromContent(initialContent));
      setBlocks(newBlocks);
    }
  }
}, [initialContent, initialBlocks, isAsrActive, ensureBottomBufferBlock]);
```

## 用户场景示例

### 场景 1：恢复并继续编辑
1. 用户在历史记录中找到昨天的会议纪要
2. 点击"📝 恢复任务"
3. 系统恢复笔记内容和结构
4. 用户启动 ASR，补充今天的跟进内容
5. 点击"小结"生成完整的会议小结
6. 点击"保存"保存更新后的内容

### 场景 2：恢复并生成小结
1. 用户恢复一个较长的采访记录
2. 系统恢复完整的采访内容（包含时间戳）
3. 用户点击"小结"，AI 生成采访摘要
4. 用户点击"保存"保存带小结的完整版本

### 场景 3：安全恢复（有未保存内容）
1. 用户正在编辑当前笔记（未保存）
2. 用户切换到历史记录，尝试恢复旧笔记
3. 系统弹出确认对话框，提醒有未保存内容
4. 用户选择"取消"，返回保存当前内容
5. 保存后再次恢复历史笔记

## 注意事项

### 数据安全
- 恢复操作不会修改原始历史记录
- 恢复后的修改会创建新的历史记录
- 提供安全确认，防止意外覆盖未保存内容

### Blocks 数据兼容性
- 新版本保存的记录包含完整的 blocks 数据
- 旧版本保存的记录只有纯文本，恢复时自动转换为 blocks
- 转换逻辑：`createBlocksFromContent(text)`

### 状态管理
- 恢复时清除草稿缓存，避免冲突
- 恢复时清除 `initialBlocks`，确保下次操作正常
- "新笔记"和"退出"时重置 `initialBlocks`

## 未来改进方向

1. **版本历史**：支持查看同一笔记的多个历史版本
2. **差异对比**：显示恢复的笔记与当前编辑的差异
3. **选择性恢复**：允许只恢复笔记的某些部分
4. **恢复预览**：在恢复前预览笔记内容
5. **撤销恢复**：提供"撤销恢复"功能，快速回到恢复前的状态

## 相关文件

### 前端
- `electron-app/src/App.tsx` - 恢复逻辑主入口
- `electron-app/src/components/shared/HistoryView.tsx` - 历史记录界面
- `electron-app/src/components/apps/VoiceNote/BlockEditor.tsx` - Blocks 恢复处理
- `electron-app/src/components/shared/HistoryView.css` - 样式定义

### 后端
- `src/api/server.py` - API 端点实现
- `src/providers/storage/sqlite.py` - 数据库查询
- `src/services/voice_service.py` - 服务层逻辑

## 更新日志

### 2026-01-03
- ✅ 更新按钮文案：从"查看"改为"📝 恢复任务"
- ✅ 添加安全确认对话框（有未保存内容时）
- ✅ 完善 blocks 数据恢复逻辑
- ✅ 改进成功提示消息
- ✅ 修复 initialBlocks 重置问题
- ✅ 更新文档和代码注释

