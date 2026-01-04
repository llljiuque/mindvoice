# Bug修复记录：ASR停止时内容丢失

**日期**：2026-01-03  
**Bug ID**：ASR停止时前端只显示最后几个字  
**严重程度**：高

---

## 🐛 问题描述

### 用户反馈
用户在使用语音笔记功能时，点击"停止ASR"后，前端文字只显示"松松的就"（最后几个字），而不是完整的识别内容。

### 日志分析

从 `logs/api_server_20260103_200457.log` 可以看到：

1. **第1个utterance**（line 464-471）：识别出149字符的完整内容
   ```
   F35 隐身战机吧。是。就是你也能看出来，因为委内瑞拉没有任何的反制能力...
   ```

2. **第2个utterance**（line 512-522）：识别出21字符
   ```
   学也门啊，买上买上买上百十来发的弹道导弹。
   ```

3. **第3个utterance**（line 532-595）：开始识别
   ```
   就好像说到导弹了，对吧
   ```

4. **用户点击停止**（line 600）

**结果**：前端只显示第3个utterance的内容，第1和第2个utterance的内容全部丢失！

---

## 🔍 根本原因

### 问题定位

在 `electron-app/src/components/apps/VoiceNote/BlockEditor.tsx` 中，存在一个有问题的 `useEffect`：

```typescript
// 旧代码（有问题）
useEffect(() => {
  if (!isAsrActive) {  // ⚠️ 当ASR停止时触发
    if (initialBlocks && initialBlocks.length > 0) {
      const blocksWithBuffer = ensureBottomBufferBlock(initialBlocks);
      setBlocks(blocksWithBuffer);  // ❌ 用旧的initialBlocks重置所有blocks
    } else {
      const newBlocks = ensureBottomBufferBlock(createBlocksFromContent(initialContent));
      setBlocks(newBlocks);  // ❌ 用旧的initialContent重置所有blocks
    }
    asrWritingBlockIdRef.current = null;
  }
}, [initialContent, initialBlocks, isAsrActive, ensureBottomBufferBlock]);
```

### 问题机制

1. **ASR录音过程中**：
   - `appendAsrText()` 不断更新blocks
   - blocks中累积了多个utterance（第1、2、3个）
   - 但`initialBlocks`状态**从未更新**（保持为初始值或undefined）

2. **用户点击停止ASR**：
   - `isAsrActive` 变为 `false`
   - 触发上述 `useEffect`
   - `setBlocks(initialBlocks)` 或 `setBlocks(createBlocksFromContent(initialContent))`
   - **所有ASR过程中积累的blocks被清空！**

3. **结果**：
   - 如果`initialBlocks`是空的，所有内容丢失
   - 如果`initialContent`包含之前的文本，只显示旧文本，ASR新增的内容丢失

---

## ✅ 解决方案

### 修复思路

**核心原则**：`isAsrActive`变化时，**不应该重置blocks**，除非是明确的内容更新（如从历史记录恢复、创建新笔记）。

### 新代码

```typescript
// 新代码（已修复）
// 初始化blocks
// 策略：
// 1. 首次渲染时初始化
// 2. 当initialBlocks或initialContent显式更新时重新初始化（如从历史记录恢复、创建新笔记）
// 3. 注意：不应该仅因为isAsrActive变化而重置blocks，否则会丢失ASR过程中的内容
const isFirstRenderRef = useRef(true);
const prevInitialBlocksRef = useRef<any[] | undefined>(initialBlocks);
const prevInitialContentRef = useRef<string>(initialContent);

useEffect(() => {
  // 检查是否是首次渲染，或者initialBlocks/initialContent发生了变化
  const isFirstRender = isFirstRenderRef.current;
  const initialBlocksChanged = prevInitialBlocksRef.current !== initialBlocks;
  const initialContentChanged = prevInitialContentRef.current !== initialContent;
  
  // 只在以下情况重新初始化：
  // 1. 首次渲染
  // 2. initialBlocks改变（如从历史记录恢复、创建新笔记）
  // 3. initialContent改变且不在ASR活动中（避免ASR过程中被重置）
  if (isFirstRender || initialBlocksChanged || (initialContentChanged && !isAsrActive)) {
    if (isFirstRender) {
      isFirstRenderRef.current = false;
    }
    
    // 更新prev引用
    prevInitialBlocksRef.current = initialBlocks;
    prevInitialContentRef.current = initialContent;
    
    if (initialBlocks && initialBlocks.length > 0) {
      const blocksWithBuffer = ensureBottomBufferBlock(initialBlocks);
      setBlocks(blocksWithBuffer);
    } else {
      const newBlocks = ensureBottomBufferBlock(createBlocksFromContent(initialContent));
      setBlocks(newBlocks);
    }
    asrWritingBlockIdRef.current = null;
  }
}, [initialBlocks, initialContent, isAsrActive, ensureBottomBufferBlock]);
```

### 修复要点

1. **使用ref追踪前一个值**：
   - `prevInitialBlocksRef`：追踪上一次的`initialBlocks`
   - `prevInitialContentRef`：追踪上一次的`initialContent`
   - `isFirstRenderRef`：标记是否首次渲染

2. **只在必要时重置blocks**：
   - 首次渲染
   - `initialBlocks`显式更新（从历史记录恢复、创建新笔记）
   - `initialContent`显式更新**且**不在ASR活动中

3. **ASR停止时保留blocks**：
   - 当`isAsrActive`从`true`变为`false`时
   - 如果`initialBlocks`和`initialContent`没有变化
   - **不会重置blocks**，保留ASR过程中的所有内容

---

## 🔄 与ASR架构的关系

### 最新ASR架构要点

根据 `docs/audio_to_asr_flow.md` 的更新：

1. **AudioASRGateway统一网关**：
   - Audio和ASR之间的控制层
   - 通过VAD检测控制ASR的启停
   - 回调：`on_speech_start()` 和 `on_speech_end()`

2. **异步断开流程**：
   ```
   用户停止 → _on_speech_end() → 发送None标记 → 
   ASR发送负包 → 等待服务器最后响应 → 
   收到is_last_package=True → _disconnect() → 
   _on_asr_disconnected()回调 → 重置状态
   ```

3. **关键时序约束**：
   - `_on_speech_end()`只发送结束标记，不立即重置状态
   - ASR接收器继续运行，等待服务器的最后响应
   - 最后的text_final可能在停止后才到达

### 前端需要注意的点

1. **text_final可能延迟到达**：
   - 用户点击停止ASR后
   - 后端可能还在处理最后的音频
   - 可能收到延迟的`text_final`消息
   - **前端必须继续处理这些消息**

2. **不要过早重置blocks**：
   - 状态变为`idle`时，不要立即清空blocks
   - 保持blocks内容，直到明确的清空操作（创建新笔记、保存等）

3. **WebSocket消息处理正确**：
   - `text_update`：实时更新（中间结果）
   - `text_final`：确定结果（带时间信息）
   - `state_change`：状态变化
   - 都正确处理，无需修改

---

## 📝 测试建议

### 测试场景

1. **基本场景**：
   - 开始录音
   - 说一段话，等待识别完成（看到text_final）
   - 继续说第二段话，等待识别完成
   - 继续说第三段话（中途）
   - 点击停止ASR
   - **验证**：前端应显示所有三段话的内容

2. **快速启停**：
   - 开始录音
   - 快速说话并停止（在第一个utterance完成前）
   - **验证**：应显示识别的内容，不丢失

3. **VAD自动启停**（如果启用）：
   - 开始录音
   - 说话 → 停顿1.5秒 → 再说话 → 停顿1.5秒 → 再说话
   - 点击停止ASR
   - **验证**：所有分段识别的内容都应保留

4. **历史记录恢复**：
   - 保存一条笔记
   - 从历史记录恢复
   - **验证**：应正确显示保存的blocks内容

5. **创建新笔记**：
   - 有内容的情况下点击"创建新笔记"
   - **验证**：内容被清空，准备新笔记

---

## 📊 影响范围

### 修改的文件

- `electron-app/src/components/apps/VoiceNote/BlockEditor.tsx`
  - 修改：`useEffect`逻辑（第201-238行）
  - 影响：blocks初始化和重置逻辑

### 不需要修改的文件

- `electron-app/src/App.tsx`
  - WebSocket消息处理正确
  - ASR控制流程正确
  - 无需修改

- `src/services/voice_service.py`
  - 后端逻辑符合最新ASR架构
  - AudioASRGateway回调正确设置
  - 无需修改

---

## ✅ 验证结果

### 预期行为

修复后，相同的场景应该：

1. **第1个utterance识别完成** → blocks中添加第1个block
2. **第2个utterance识别完成** → blocks中添加第2个block
3. **第3个utterance开始识别** → blocks中添加第3个block（实时更新）
4. **用户点击停止ASR** → `isAsrActive`变为`false`
5. **blocks保持不变** → 所有3个blocks都保留
6. **前端显示** → 完整显示所有识别内容

---

## 📚 相关文档

- [音频到ASR流程详解](./audio_to_asr_flow.md)
- [任务恢复功能](./restore_task_feature.md)

---

## 🔖 标签

`bugfix` `asr` `frontend` `voice-note` `blocks` `content-loss`

