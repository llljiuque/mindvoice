# 代码清理记录：移除老方法，使用Blocks架构

**日期**：2026-01-03  
**任务**：清理前端旧的text state架构，统一使用blocks管理内容

---

## 🎯 清理目标

**用户需求**：
> 按钮只是发送信息给AudioASRGateway，通知启动asr和停止asr输入信息。不应该参与到任务里去。
> 在启动asr输入信息时，语音笔记有合适的方式接收api发送过来的信息。

**核心原则**：
1. ASR按钮 → 只发送启停信号
2. ASR结果 → 通过WebSocket的`text_update`/`text_final` → 直接调用`blockEditorRef.appendAsrText()`
3. 内容管理 → 完全由`BlockEditor`内部的blocks管理
4. 删除所有旧的`text` state相关代码

---

## ✅ 已完成的清理

### 1. VoiceNote组件 (`VoiceNote.tsx`)

#### 删除的Props
```typescript
// ❌ 删除
text: string;
onTextChange: (text: string) => void;

// ✅ 保留（只用于控制）
asrState: 'idle' | 'recording' | 'stopping';
onAsrStart?: () => void;  // 只发送启动信号
onAsrStop?: () => void;   // 只发送停止信号
```

#### 新增方法
```typescript
// 检查是否有内容（从blockEditorRef获取）
const hasContent = () => {
  if (!blockEditorRef?.current) return false;
  const blocks = blockEditorRef.current.getBlocks();
  return blocks.some((b: any) => 
    b.type !== 'note-info' && 
    !b.isBufferBlock && 
    b.content.trim()
  );
};
```

#### 修改的功能
- **按钮禁用逻辑**：从`!text || !text.trim()`改为`!hasContent()`
- **内容变化处理**：从`handleTextChange(newText)`改为`handleContentChange()`

### 2. BlockEditor组件 (`BlockEditor.tsx`)

#### 删除的Props
```typescript
// ❌ 删除
initialContent?: string;

// ✅ 保留
initialBlocks?: Block[];
```

#### 简化的初始化逻辑
```typescript
// 旧代码：复杂的依赖管理
useEffect(() => {
  // 依赖: initialContent, initialBlocks, isAsrActive, ...
}, [initialContent, initialBlocks, isAsrActive, ensureBottomBufferBlock]);

// 新代码：只监听initialBlocks变化
useEffect(() => {
  // 只依赖: initialBlocks
  // 移除initialContent和isAsrActive的依赖
}, [initialBlocks, ensureBottomBufferBlock]);
```

### 3. App.tsx主应用

#### 删除的State
```typescript
// ❌ 删除
const [text, setText] = useState('');
```

#### 重构的功能

**3.1 草稿保存/恢复**
```typescript
// 旧代码：保存text
const draft = { text, app: activeView, timestamp: Date.now() };

// 新代码：保存blocks
const draft = { blocks, app: activeView, timestamp: Date.now() };
```

**3.2 WebSocket消息处理**
```typescript
// 旧代码
case 'initial_state':
  setAsrState(data.state);
  if (data.text) setText(data.text);  // ❌ 删除

// 新代码
case 'initial_state':
  setAsrState(data.state);
  // 注意：不再处理data.text，ASR结果通过text_update/text_final消息处理
```

**3.3 保存功能 (saveText)**
```typescript
// 旧代码：直接使用text
if (!text?.trim()) return;
const contentToSave = text.trim();

// 新代码：从blocks生成
const blocks = blockEditorRef.current?.getBlocks();
const hasContent = blocks.some(...);
if (!hasContent) return;
const contentToSave = blocks
  .filter(...)
  .map(b => b.content)
  .join('\n');
```

**3.4 复制功能 (copyText)**
```typescript
// 旧代码
if (!text) return;
await navigator.clipboard.writeText(text);

// 新代码
const blocks = blockEditorRef.current?.getBlocks();
const textContent = blocks
  .filter(...)
  .map(b => b.content)
  .join('\n');
await navigator.clipboard.writeText(textContent);
```

**3.5 创建新笔记 (createNewNote)**
```typescript
// 旧代码
if (text && text.trim()) { ... }
const contentToSave = text.trim();

// 新代码
const blocks = blockEditorRef.current?.getBlocks();
const hasContent = blocks && blocks.some(...);
if (hasContent) { ... }
const textContent = blocks
  .filter(...)
  .map(b => b.content)
  .join('\n');
```

**3.6 恢复历史记录 (loadRecord)**
```typescript
// 旧代码
if (isWorkSessionActive && text && text.trim()) {
  const confirmed = window.confirm(...);
}
setText(data.text);

// 新代码
const blocks = blockEditorRef.current?.getBlocks();
const hasContent = blocks && blocks.some(...);
if (isWorkSessionActive && hasContent) {
  const confirmed = window.confirm(...);
}
// 只设置initialBlocks，不再设置text
setInitialBlocks(data.metadata.blocks);
```

---

## 📊 清理统计

### 删除的代码
- 删除state: `text`和`setText`
- 删除props: `text`和`onTextChange`（VoiceNote）
- 删除props: `initialContent`（BlockEditor）
- 删除WebSocket处理: `setText(data.text)`
- 删除多处`text`引用：约15处

### 简化的逻辑
- 草稿保存/恢复：统一使用blocks
- 按钮禁用判断：统一使用`hasContent()`
- 内容获取：统一通过`blockEditorRef.current.getBlocks()`

---

## 🔄 数据流程（清理后）

### ASR输入流程
```
用户点击"启动ASR" 
  ↓
onAsrStart() 
  ↓
POST /api/recording/start（只发送启动信号）
  ↓
后端AudioASRGateway启动ASR
  ↓
WebSocket: text_update / text_final
  ↓
blockEditorRef.current.appendAsrText()
  ↓
BlockEditor内部更新blocks
```

### 内容保存流程
```
用户点击"保存"
  ↓
onSaveText()
  ↓
从blockEditorRef.current.getBlocks()获取blocks
  ↓
生成文本内容：blocks.filter(...).map(...).join('\n')
  ↓
POST /api/text/save { text, blocks }
```

### 历史记录恢复流程
```
用户点击历史记录
  ↓
loadRecord(recordId)
  ↓
GET /api/records/:id
  ↓
setInitialBlocks(data.metadata.blocks)
  ↓
BlockEditor检测到initialBlocks变化
  ↓
重新初始化blocks
```

---

## ✅ 清理后的优势

### 1. 架构更清晰
- **单一数据源**：blocks是唯一的内容管理方式
- **职责分离**：
  - ASR按钮 → 只负责控制
  - BlockEditor → 负责内容管理
  - App.tsx → 负责协调和持久化

### 2. 避免状态不一致
- ❌ 旧架构：`text` state和`blocks`可能不同步
- ✅ 新架构：只有`blocks`一个数据源

### 3. 简化props传递
```typescript
// 旧：需要传递text和onTextChange
<VoiceNote 
  text={text}
  onTextChange={setText}
  ...
/>

// 新：不需要传递这些props
<VoiceNote
  asrState={asrState}
  onAsrStart={handleAsrStart}
  onAsrStop={handleAsrStop}
  ...
/>
```

### 4. 更容易维护
- 内容相关逻辑集中在BlockEditor
- App.tsx只需通过ref访问blocks
- 减少了状态管理的复杂度

---

## 🧪 需要测试的功能

1. **ASR基本功能**
   - ✅ 启动ASR → 只发送信号
   - ✅ ASR识别结果 → 通过WebSocket更新blocks
   - ✅ 停止ASR → 保留所有内容

2. **内容管理**
   - ✅ 多个utterance累积显示
   - ✅ 按钮禁用状态正确（基于hasContent）
   - ✅ 内容保存包含所有blocks

3. **草稿功能**
   - ✅ 自动保存草稿（使用blocks）
   - ✅ 恢复草稿（使用blocks）
   - ✅ 草稿过期清理

4. **历史记录**
   - ✅ 保存记录（text + blocks）
   - ✅ 恢复记录（优先使用blocks）
   - ✅ 恢复前确认未保存内容

5. **创建新笔记**
   - ✅ 有内容时先保存
   - ✅ 无内容时直接清空
   - ✅ 清空后可以继续工作

6. **复制功能**
   - ✅ 复制所有blocks内容
   - ✅ 空内容时提示

---

## 📝 相关文档

- [Bug修复：ASR停止时内容丢失](./bugfix_20260103_asr_content_lost.md)
- [音频到ASR流程详解](./audio_to_asr_flow.md)

---

## 🏷️ 标签

`refactor` `cleanup` `blocks-architecture` `asr` `voice-note` `state-management`

