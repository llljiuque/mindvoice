# 共享编辑模式实现说明

## 概述

本文档详细说明了语音桌面助手中ASR（语音识别）输入与用户手动输入/编辑的共享编辑模式的实现方式。该模式允许ASR和用户同时编辑文档，通过操作转换（Operational Transform, OT）系统实现实时协调，确保两种输入源不会互相覆盖或产生冲突。

## 核心特性

- ✅ **实时合并**：ASR更新立即应用，无需等待用户停止编辑
- ✅ **双向编辑**：ASR和用户可以同时编辑文档
- ✅ **冲突解决**：通过操作转换系统自动协调冲突
- ✅ **光标保护**：ASR文本插入时保护用户光标位置
- ✅ **智能同步**：用户编辑自动同步到后端

## 架构设计

### 1. 数据流架构

```
┌─────────────────┐
│  ASR Provider   │ (后端)
│  (火山引擎)      │
└────────┬────────┘
         │ WebSocket
         │ text_update
         ▼
┌─────────────────┐
│  FastAPI Server │ (后端)
│  /ws endpoint   │
└────────┬────────┘
         │ WebSocket
         │ {type: "text_update", text: "..."}
         ▼
┌─────────────────┐
│   App.tsx       │ (前端)
│  handleAsrText  │
│   Update()      │
└────────┬────────┘
         │
         ├─────────────────┐
         │                 │
         ▼                 ▼
┌─────────────────┐  ┌─────────────────┐
│ Operation       │  │  BlockEditor     │
│ Transformer     │  │  insertAsrText() │
│ (OT System)     │  │  appendAsrText() │
└────────┬────────┘  └────────┬────────┘
         │                    │
         └────────┬───────────┘
                  │
                  ▼
         ┌─────────────────┐
         │  Block Component │
         │  (保护光标位置)   │
         └─────────────────┘
```

### 2. 核心组件

#### 2.1 App.tsx - 主控制器

**职责**：
- 管理ASR和用户编辑的双缓冲机制
- 协调操作转换系统
- 处理WebSocket消息
- 同步用户编辑到后端

**关键状态**：
```typescript
// 双缓冲机制
const asrBufferRef = useRef<string>('');        // ASR缓冲区
const userEditBufferRef = useRef<string>('');  // 用户编辑缓冲区
const lastMergedAsrRef = useRef<string>('');    // 上次合并的ASR文本

// 操作转换系统
const operationHistoryRef = useRef<Operation[]>([]);  // 操作历史
const pendingAsrOperationsRef = useRef<Operation[]>([]); // 待应用的ASR操作（已废弃）

// 编辑状态跟踪
const isEditingRef = useRef(false);  // 用户是否正在编辑
```

#### 2.2 OperationTransformer - 操作转换系统

**位置**：`electron-app/src/utils/operationTransform.ts`

**核心方法**：

1. **`diffToOperations(oldText, newText, author)`**
   - 将文本差异转换为操作序列
   - 支持 `insert`、`delete`、`replace` 三种操作类型
   - 每个操作包含位置、内容、时间戳和作者信息

2. **`transform(op1, op2)`**
   - 将操作 `op1` 转换为相对于已应用操作 `op2` 之后的状态
   - 处理操作之间的位置偏移和冲突

3. **`transformOperations(op1s, op2s)`**
   - 批量转换操作序列
   - 将待应用的操作转换为相对于已应用操作序列之后的状态

4. **`applyOperation(document, operation)`**
   - 将操作应用到文档
   - 返回应用后的新文档

#### 2.3 BlockEditor - 块编辑器

**位置**：`electron-app/src/components/BlockEditor.tsx`

**核心方法**：

1. **`appendAsrText(text)`**
   - 追加ASR文本到最后一个块
   - 用于文档末尾追加场景

2. **`insertAsrText(text, position)`** ⭐ **新增**
   - 在指定位置插入ASR文本
   - 支持跨块插入
   - 计算目标块和插入偏移量

#### 2.4 Block - 块组件

**位置**：`electron-app/src/components/Block.tsx`

**核心功能**：
- 光标位置保护机制
- 智能合并ASR文本更新
- 检测用户编辑状态

## 实现细节

### 1. ASR更新处理流程

```typescript
handleAsrTextUpdate(asrText: string) {
  // 1. 更新ASR缓冲区
  const oldAsr = asrBufferRef.current;
  asrBufferRef.current = asrText;

  // 2. 将ASR文本变化转换为操作
  const asrOperations = OperationTransformer.diffToOperations(oldAsr, asrText, 'asr');

  // 3. 转换ASR操作，使其相对于已应用的用户操作之后的状态
  const userOperations = operationHistoryRef.current.filter(op => op.author === 'user');
  const transformedAsrOps = OperationTransformer.transformOperations(asrOperations, userOperations);

  // 4. 过滤空操作
  const validOps = transformedAsrOps.filter(op => /* 验证操作有效性 */);

  // 5. 实时应用转换后的ASR操作
  let currentDoc = userEditBufferRef.current || text;
  for (const op of validOps) {
    currentDoc = OperationTransformer.applyOperation(currentDoc, op);
    operationHistoryRef.current.push(op);
  }

  // 6. 更新显示和缓冲区
  setText(currentDoc);
  userEditBufferRef.current = currentDoc;

  // 7. 通过BlockEditor插入文本（保持光标位置）
  if (validOps[0].type === 'insert') {
    blockEditorRef.current.insertAsrText(op.text, op.position);
  }
}
```

**关键改进**：
- ✅ 移除了 `isEditingRef.current` 检查，ASR更新始终实时应用
- ✅ 使用操作转换系统确保ASR操作相对于用户操作正确应用
- ✅ 支持在任意位置插入，不仅仅是文档末尾

### 2. 用户编辑处理流程

```typescript
handleTextChange(newText: string) {
  const oldText = userEditBufferRef.current || text;
  const currentAsr = asrBufferRef.current;
  const isUserEdit = newText !== currentAsr;

  if (isUserEdit) {
    // 1. 将用户编辑转换为操作
    const userOperations = OperationTransformer.diffToOperations(oldText, newText, 'user');

    // 2. 转换用户操作，使其相对于已应用的ASR操作之后的状态
    const asrOps = operationHistoryRef.current.filter(op => op.author === 'asr');
    const transformedUserOps = OperationTransformer.transformOperations(userOperations, asrOps);

    // 3. 应用用户操作
    let currentDoc = oldText;
    for (const op of transformedUserOps) {
      currentDoc = OperationTransformer.applyOperation(currentDoc, op);
      operationHistoryRef.current.push(op);
    }

    // 4. 更新状态
    isEditingRef.current = true;
    setText(currentDoc);
    userEditBufferRef.current = currentDoc;

    // 5. 延迟同步到后端（防抖）
    syncTimeoutRef.current = setTimeout(() => {
      syncUserEditToBackend(currentDoc);
    }, 1000);
  }
}
```

### 3. 操作转换算法

#### 3.1 位置调整规则

当两个操作不相交时：
- 如果 `op1` 在 `op2` 之前：`op1` 位置不变
- 如果 `op2` 在 `op1` 之前：`op1` 位置需要调整

```typescript
// op2 在 op1 之前，调整 op1 的位置
const op2Length = op2.type === 'delete' 
  ? -(op2.length || 0)
  : (op2.text?.length || op2.oldText?.length || 0);

return {
  ...op1,
  position: Math.max(0, op1.position + op2Length),
};
```

#### 3.2 冲突解决策略

**用户操作优先原则**：
- 如果用户正在编辑某个区域，ASR操作会被调整或跳过
- ASR追加操作（在文档末尾）总是可以应用
- 重叠区域：用户编辑优先，ASR操作调整位置或跳过

```typescript
// ASR操作 vs 用户操作
if (op1.author === 'asr' && op2.author === 'user') {
  // 如果ASR操作在用户编辑之后，可以应用但需要调整位置
  if (op1.position >= docLength) {
    return {
      ...op1,
      position: op1.position + op2Length,
    };
  }
  
  // 完全重叠：跳过ASR操作（用户编辑优先）
  return {
    ...op1,
    type: 'insert',
    text: '',  // 空操作，不应用
  };
}
```

### 4. 光标保护机制

**Block组件中的实现**：

```typescript
useEffect(() => {
  if (block.content !== content && contentRef.current) {
    // 检查用户是否正在编辑
    const isUserEditing = isFocused && 
                         contentRef.current === document.activeElement &&
                         range &&
                         contentRef.current.contains(range.commonAncestorContainer);

    if (isUserEditing) {
      // 保存光标位置
      saveCursorPosition();
      
      const currentText = contentRef.current.textContent || '';
      const newText = block.content;
      
      // 如果新文本是当前文本的扩展（ASR追加）
      if (newText.startsWith(currentText)) {
        const cursorPos = cursorPositionRef.current ?? currentText.length;
        
        // 只在光标在末尾时才追加
        if (cursorPos >= currentText.length - 1) {
          const appendedText = newText.slice(currentText.length);
          // 在光标位置插入
          const before = currentText.slice(0, cursorPos);
          const after = currentText.slice(cursorPos);
          const updatedText = before + appendedText + after;
          
          contentRef.current.textContent = updatedText;
          restoreCursorPosition();
        }
      }
    }
  }
}, [block.content, isFocused, content]);
```

**保护策略**：
- ✅ 检测用户是否正在编辑（焦点 + 光标位置）
- ✅ 保存和恢复光标位置
- ✅ 只在光标在末尾时追加ASR文本
- ✅ 如果光标在中间位置，不更新DOM（避免干扰用户）

### 5. 文本差异检测算法

**`diffToOperations` 方法**：

```typescript
static diffToOperations(oldText: string, newText: string, author: 'asr' | 'user'): Operation[] {
  // 1. 找到第一个不同的位置（从前向后）
  let i = 0;
  while (i < oldText.length && i < newText.length && oldText[i] === newText[i]) {
    i++;
  }

  // 2. 找到最后一个相同的位置（从后向前）
  let j = oldText.length - 1;
  let k = newText.length - 1;
  while (j >= i && k >= i && oldText[j] === newText[j]) {
    j--;
    k--;
  }

  // 3. 检测追加操作
  if (newText.startsWith(oldText)) {
    return [{
      type: 'insert',
      position: oldText.length,
      text: newText.slice(oldText.length),
      timestamp: Date.now(),
      author,
    }];
  }

  // 4. 检测删除操作
  if (oldText.startsWith(newText)) {
    return [{
      type: 'delete',
      position: newText.length,
      length: oldText.length - newText.length,
      timestamp: Date.now(),
      author,
    }];
  }

  // 5. 中间修改：先删除后插入
  // ...
}
```

## 数据同步

### 1. ASR到前端的同步

**路径**：ASR Provider → FastAPI Server → WebSocket → App.tsx

```python
# 后端：src/services/voice_service.py
def _on_asr_text_received(self, text: str, is_final: bool):
    self._current_text = text
    if self._on_text_callback:
        self._on_text_callback(text)  # 触发WebSocket广播

# 后端：src/api/server.py
def broadcast_text(text: str):
    message = {"type": "text_update", "text": text}
    for connection in active_connections:
        asyncio.create_task(connection.send_json(message))
```

### 2. 用户编辑到后端的同步

**路径**：BlockEditor → App.tsx → FastAPI API → Storage

```typescript
// 前端：App.tsx
const syncUserEditToBackend = async (userText: string) => {
  const response = await fetch(`${API_BASE_URL}/api/recording/sync-edit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: userText }),
  });
};

// 后端：src/api/server.py
@app.post("/api/recording/sync-edit")
async def sync_user_edit(request: SyncEditRequest):
    # 更新会话记录的用户编辑版本
    voice_service.storage_provider.update_record(session_id, request.text, metadata)
```

**同步策略**：
- ✅ 防抖：用户停止输入1秒后同步
- ✅ 只在录音或暂停状态时同步
- ✅ 更新会话记录，保留ASR原始文本

## 使用场景示例

### 场景1：ASR追加，用户未编辑

```
初始状态: "Hello"
ASR更新: "Hello World"
结果: "Hello World" ✅
```

### 场景2：ASR追加，用户正在编辑开头

```
初始状态: "Hello"
用户编辑: "Hi Hello" (在开头插入)
ASR更新: "Hello World"
结果: "Hi Hello World" ✅ (ASR追加到末尾)
```

### 场景3：ASR和用户同时编辑不同位置

```
初始状态: "Hello"
用户编辑: "Hello!" (在末尾添加)
ASR更新: "Hello World" (在中间插入)
结果: "Hello World!" ✅ (操作转换协调)
```

### 场景4：ASR和用户编辑重叠区域

```
初始状态: "Hello World"
用户编辑: "Hi World" (删除"Hello"，插入"Hi")
ASR更新: "Hello Beautiful World" (在"Hello"后插入"Beautiful")
结果: "Hi Beautiful World" ✅ (用户编辑优先，ASR操作调整)
```

## 性能优化

### 1. 防抖机制

- **用户编辑同步**：1秒防抖，避免频繁API调用
- **编辑状态检测**：2秒超时，自动清除编辑标记

### 2. 操作过滤

```typescript
// 过滤空操作（被跳过的操作）
const validOps = transformedAsrOps.filter(op => {
  if (op.type === 'insert') return op.text && op.text.length > 0;
  if (op.type === 'delete') return op.length && op.length > 0;
  if (op.type === 'replace') return op.text && op.oldText;
  return false;
});
```

### 3. DOM更新优化

- 使用 `ref` 直接操作DOM，避免不必要的React重渲染
- 只在必要时更新DOM内容
- 保护用户光标位置，避免闪烁

## 测试建议

### 1. 单元测试

- `OperationTransformer.diffToOperations` - 文本差异检测
- `OperationTransformer.transform` - 操作转换
- `OperationTransformer.applyOperation` - 操作应用

### 2. 集成测试

- ASR更新 + 用户编辑同时进行
- 光标位置保护
- 跨块插入ASR文本

### 3. 压力测试

- 高频ASR更新（每秒多次）
- 用户快速输入
- 长时间运行稳定性

## 已知限制

1. **操作转换简化**：当前实现是简化版OT，对于复杂冲突场景可能不够完善
2. **跨块插入**：`insertAsrText` 目前不支持在换行符位置插入新块
3. **撤销/重做**：当前未实现操作历史的撤销/重做功能

## 未来改进方向

1. **完整的OT实现**：实现更完善的操作转换算法
2. **撤销/重做**：基于操作历史实现撤销重做
3. **冲突可视化**：显示ASR和用户编辑的冲突区域
4. **性能监控**：添加操作转换性能指标

## 相关文档

- [架构设计文档](./ARCHITECTURE.md)
- [API文档](./ARCHITECTURE_API.md)
- [实现细节](./IMPLEMENTATION.md)

## 更新日志

- **2024-XX-XX**: 实现共享编辑模式，支持ASR和用户同时编辑
- **2024-XX-XX**: 添加操作转换系统，实现冲突解决
- **2024-XX-XX**: 优化光标保护机制，改进用户体验

