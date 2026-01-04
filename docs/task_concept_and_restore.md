# 语音笔记任务概念与恢复功能

## 更新日期：2026-01-03

---

## 一、任务概念说明

### 问题背景

您提出了一个重要的概念性问题：
> "语音笔记"有任务的概念吗？
> 启动和停止 ASR 不能成为终止一次记录的动作。
> "新笔记"或"退出"是结束本次记录任务的唯一触发条件。

### 当前实现分析

#### 现有的"工作会话"概念
系统中已经实现了 `isWorkSessionActive` 状态来追踪工作会话：

```typescript
// App.tsx
const [isWorkSessionActive, setIsWorkSessionActive] = useState(false);

const startWorkSession = (app: AppView): boolean => {
  setActiveWorkingApp(app);
  setIsWorkSessionActive(true);
  return true;
};

const endWorkSession = () => {
  setActiveWorkingApp(null);
  setIsWorkSessionActive(false);
  // 清空内容和状态
  setText('');
  setInitialBlocks(undefined);
  localStorage.removeItem('voiceNoteDraft');
};
```

#### 任务生命周期

**任务开始：**
- 点击"开始工作"按钮
- 或者自动触发（当用户开始输入时）

**任务进行中：**
- 可以多次启动/停止 ASR
- 可以手动编辑内容
- 可以生成小结
- 可以保存到历史记录（但不结束任务）
- 内容持续累积

**任务结束：** 只有两种方式
1. **"新笔记"按钮**：保存当前内容 → 清空编辑器 → **保持工作会话活跃**
2. **"退出"按钮**：可选择保存 → 结束会话 → 返回欢迎界面

### 正确的理解

✅ **启动/停止 ASR** = 控制语音输入的开关，**不影响任务状态**
✅ **保存按钮** = 保存快照到历史记录，**不结束任务**
✅ **新笔记按钮** = 结束当前笔记 + 开始新笔记，**工作会话继续**
✅ **退出按钮** = 唯一真正结束工作会话的方式

### 按钮状态表

| 当前状态 | 可用按钮 |
|---------|---------|
| 未开始任务 | [开始工作] |
| 任务中 + ASR 空闲 | [启动 ASR] [保存] [小结] [新笔记] [复制] [退出] |
| 任务中 + ASR 录音 | [停止 ASR] [复制] |
| 任务中 + ASR 停止中 | [复制] |

---

## 二、从历史记录恢复任务功能

### 新增特性

根据您的要求："再增加一个特性，从历史记录可以恢复一次历史任务。"

我们实现了完整的任务恢复功能。

### 核心改进

#### 1. 按钮文案优化
**历史记录界面：**
- **旧版本**：`查看` 按钮
- **新版本**：`📝 恢复任务` 按钮
- **提示文案**：鼠标悬停显示"恢复此任务并继续编辑"

#### 2. 安全确认机制
当用户尝试恢复历史任务时，如果当前有未保存的内容，会弹出确认对话框：

```
当前有未保存的内容，恢复历史任务将会覆盖当前内容。

是否继续恢复？

提示：您可以先点击"保存"或"新笔记"来保存当前内容。
```

#### 3. 完整的数据恢复
恢复时会还原：
- ✅ 完整的文本内容
- ✅ Blocks 结构数据（笔记信息、段落、时间戳、小结等）
- ✅ 工作会话状态（自动启动任务）

#### 4. 恢复后的操作自由
恢复任务后，用户可以：
- 继续启动 ASR 追加新内容
- 手动编辑现有内容
- 生成或重新生成小结
- 保存修改（创建新记录，不覆盖原记录）
- 创建新笔记
- 退出任务

### 技术实现细节

#### App.tsx - loadRecord 函数

```typescript
const loadRecord = async (recordId: string) => {
  if (!apiConnected) {
    setToast({ message: 'API未连接，无法恢复任务', type: 'error' });
    return;
  }
  
  // 安全确认
  if (isWorkSessionActive && text && text.trim()) {
    const confirmed = window.confirm('...');
    if (!confirmed) return;
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/records/${recordId}`);
    const data = await response.json();
    
    if (data.text) {
      // 恢复文本
      setText(data.text);
      
      // 恢复 blocks（如果存在）
      if (data.metadata?.blocks && Array.isArray(data.metadata.blocks)) {
        console.log('[App] 恢复blocks数据:', data.metadata.blocks.length, '个blocks');
        setInitialBlocks(data.metadata.blocks);
      } else {
        console.log('[App] 无blocks数据，使用纯文本模式');
        setInitialBlocks(undefined);
      }
      
      // 清除草稿、切换视图、启动会话
      localStorage.removeItem('voiceNoteDraft');
      setActiveView('voice-note');
      startWorkSession('voice-note');
      
      // 显示成功提示
      const appTypeLabel = data.app_type === 'voice-chat' ? '对话' : '笔记';
      setToast({ 
        message: `✅ 已恢复历史${appTypeLabel}，您可以继续编辑、生成小结或保存`, 
        type: 'success',
        duration: 5000
      });
    }
  } catch (e) {
    console.error('[App] 恢复记录失败:', e);
    setSystemError({...});
  }
};
```

#### endWorkSession 改进

```typescript
const endWorkSession = () => {
  setActiveWorkingApp(null);
  setIsWorkSessionActive(false);
  // 清空内容和 blocks
  setText('');
  setInitialBlocks(undefined);  // ← 新增：重置 blocks
  localStorage.removeItem('voiceNoteDraft');
};
```

#### createNewNote 改进

```typescript
const createNewNote = async () => {
  if (text && text.trim()) {
    // 保存逻辑...
    if (data.success) {
      setText('');
      setInitialBlocks(undefined);  // ← 新增：重置 blocks
      localStorage.removeItem('voiceNoteDraft');
      setToast({ message: '当前笔记已保存，可以开始新笔记了', type: 'success' });
    }
  } else {
    setText('');
    setInitialBlocks(undefined);  // ← 新增：重置 blocks
    localStorage.removeItem('voiceNoteDraft');
    setToast({ message: '准备好记录新笔记了', type: 'info' });
  }
};
```

### BlockEditor 的 Blocks 恢复

BlockEditor 组件通过 `useEffect` 监听 `initialBlocks` 变化：

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
    asrWritingBlockIdRef.current = null;
  }
}, [initialContent, initialBlocks, isAsrActive, ensureBottomBufferBlock]);
```

---

## 三、用户场景示例

### 场景 1：恢复并追加内容

**步骤：**
1. 用户在历史记录中找到昨天的"产品讨论会"笔记
2. 点击 `📝 恢复任务`
3. 系统恢复完整内容，包括笔记信息（标题、参与人、时间等）
4. 用户点击 `启动 ASR`，补充今天的跟进讨论
5. 点击 `小结`，AI 生成包含新旧内容的完整小结
6. 点击 `保存`，创建新的历史记录

**结果：**
- 原始历史记录不变
- 新创建一条更新的记录
- 用户可以继续编辑或结束任务

### 场景 2：恢复并生成小结

**步骤：**
1. 用户恢复一个较长的采访笔记（之前没有生成小结）
2. 系统恢复完整内容（包含时间戳信息）
3. 用户点击 `小结`，AI 分析整个采访生成摘要
4. 用户点击 `保存`，保存带小结的版本

**结果：**
- 创建包含 AI 小结的新记录
- 原始记录保持不变

### 场景 3：安全恢复（防止覆盖）

**步骤：**
1. 用户正在编辑当前笔记（未保存）
2. 用户切换到历史记录，尝试恢复旧笔记
3. 系统检测到有未保存内容，弹出确认对话框
4. 用户选择 `取消`，返回继续编辑当前内容
5. 用户点击 `保存` 或 `新笔记` 保存当前内容
6. 再次切换到历史记录，恢复旧笔记

**结果：**
- 未保存的内容得到保护
- 用户有机会保存当前工作
- 避免意外数据丢失

---

## 四、数据流图

### 保存流程

```
[语音笔记界面]
    ↓ 点击"保存"
[App.saveText()]
    ↓ POST /api/text/save
    ↓ 包含: { text, app_type, blocks }
[voice_service.save_record()]
    ↓
[SQLite 数据库]
    ↓ 存储: text, metadata.blocks
[历史记录表]
```

### 恢复流程

```
[历史记录界面]
    ↓ 点击"📝 恢复任务"
[App.loadRecord()]
    ↓ 安全检查（未保存内容？）
    ↓ GET /api/records/{id}
[voice_service.get_record()]
    ↓
[SQLite 数据库]
    ↓ 返回: { text, metadata: { blocks } }
[App 状态更新]
    ↓ setText(data.text)
    ↓ setInitialBlocks(data.metadata.blocks)
    ↓ startWorkSession('voice-note')
[BlockEditor]
    ↓ 监听 initialBlocks 变化
    ↓ setBlocks(initialBlocks)
[界面渲染完整笔记]
```

---

## 五、架构优势

### 1. 任务概念清晰
- **工作会话**：长期存在，支持多次保存
- **ASR 状态**：短期状态，可多次切换
- **保存操作**：创建快照，不影响会话
- **任务结束**：明确的触发条件（新笔记/退出）

### 2. 数据安全
- 恢复前有确认机制
- 保存不覆盖原记录（创建新记录）
- 支持草稿自动保存
- 防止意外数据丢失

### 3. 灵活性
- 支持多次保存同一任务的不同版本
- 可以从任意历史版本恢复继续编辑
- 保存的历史记录相互独立

### 4. 用户体验
- 明确的按钮文案（"恢复任务"）
- 清晰的操作提示
- 安全的确认对话框
- 友好的成功反馈

---

## 六、相关文件清单

### 前端
- ✅ `electron-app/src/App.tsx` - 主应用逻辑
- ✅ `electron-app/src/components/shared/HistoryView.tsx` - 历史记录界面
- ✅ `electron-app/src/components/shared/HistoryView.css` - 样式
- ✅ `electron-app/src/components/apps/VoiceNote/VoiceNote.tsx` - 语音笔记组件
- ✅ `electron-app/src/components/apps/VoiceNote/BlockEditor.tsx` - 编辑器

### 后端
- ✅ `src/api/server.py` - API 端点
- ✅ `src/services/voice_service.py` - 服务层
- ✅ `src/providers/storage/sqlite.py` - 数据存储

### 文档
- ✅ `docs/task_concept_and_restore.md` - 本文档
- ✅ `docs/restore_task_feature.md` - 恢复功能详细文档

---

## 七、测试检查清单

### 功能测试
- [ ] 创建笔记 → 保存 → 从历史恢复 → 验证内容完整
- [ ] 恢复笔记 → 启动 ASR → 追加内容 → 保存 → 验证新记录创建
- [ ] 恢复笔记 → 生成小结 → 保存 → 验证小结正确保存
- [ ] 有未保存内容 → 尝试恢复 → 验证确认对话框出现
- [ ] 确认对话框 → 点击取消 → 验证保持当前内容
- [ ] 新笔记 → 验证 initialBlocks 被重置
- [ ] 退出 → 验证 initialBlocks 被重置

### 边界测试
- [ ] 恢复没有 blocks 数据的旧记录 → 验证纯文本模式正常
- [ ] 恢复大量内容的笔记 → 验证性能正常
- [ ] API 连接断开 → 尝试恢复 → 验证错误提示
- [ ] 恢复不存在的记录 → 验证错误处理

### UI/UX 测试
- [ ] 验证"恢复任务"按钮文案正确
- [ ] 验证鼠标悬停提示显示
- [ ] 验证成功 Toast 提示友好
- [ ] 验证确认对话框文案清晰

---

## 八、未来改进建议

### 短期（1-2周）
1. **恢复预览**：在恢复前显示笔记预览窗口
2. **批量恢复**：支持合并多个历史记录
3. **恢复撤销**：提供"撤销恢复"功能

### 中期（1-2月）
1. **版本管理**：同一笔记的多个版本可视化
2. **差异对比**：显示历史版本之间的差异
3. **智能合并**：AI 辅助合并不同版本的内容

### 长期（3-6月）
1. **协作编辑**：多人同时编辑同一笔记
2. **云端同步**：跨设备同步历史记录
3. **智能推荐**：根据当前内容推荐相关历史笔记

---

## 九、更新日志

### 2026-01-03
- ✅ 明确任务概念和生命周期
- ✅ 实现从历史记录恢复任务功能
- ✅ 更新按钮文案："查看" → "📝 恢复任务"
- ✅ 添加安全确认对话框
- ✅ 修复 initialBlocks 重置问题
- ✅ 完善 blocks 数据恢复逻辑
- ✅ 改进用户提示和错误处理
- ✅ 编写完整文档

---

## 总结

通过本次更新，我们：

1. **明确了任务概念**：工作会话是长期状态，ASR 是短期操作，保存不结束任务
2. **实现了恢复功能**：用户可以从历史记录恢复任务，继续编辑和追加内容
3. **确保了数据安全**：恢复前确认，保存不覆盖，防止意外丢失
4. **优化了用户体验**：清晰的文案，友好的提示，流畅的交互

这些改进使"语音笔记"的任务管理更加清晰和强大，为用户提供了更灵活的笔记编辑和管理体验。

