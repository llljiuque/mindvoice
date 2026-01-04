# 功能优化：EXIT 退出时自动保存

**日期**: 2026-01-03  
**开发人员**: 深圳王哥 & AI  
**功能类型**: 用户体验优化  
**影响范围**: 语音笔记模块

---

## 功能需求

### 用户需求
用户希望在点击 EXIT 按钮时，能够自动保存当前内容后再退出，避免内容丢失。

### 设计理念

#### 两种工作模式
MindVoice 的语音笔记支持两种不同的工作模式：

1. **临时退出（切换视图）**
   - **触发方式**: 切换到其他视图（历史记录、设置等）
   - **行为**: 保留工作现场（草稿自动保存到 localStorage）
   - **重新进入**: 恢复上次的工作内容
   - **用途**: 临时查看其他信息，稍后继续工作

2. **正式退出（EXIT）**
   - **触发方式**: 点击 EXIT 按钮
   - **行为**: 自动保存到历史记录，清空工作区，显示欢迎界面
   - **重新进入**: 全新的空白笔记
   - **用途**: 完成当前笔记，开始新的记录

---

## 实现方案

### 核心函数：`exitWithSave`

```typescript
// EXIT退出：保存后退出（显示欢迎界面，开始全新记录）
const exitWithSave = async () => {
  // 1. 检查前置条件（API连接、ASR状态）
  // 2. 检查是否有内容需要保存
  // 3. 如果有内容，自动保存到历史记录
  // 4. 保存成功后，清空工作区并显示欢迎界面
  // 5. 如果保存失败，询问用户是否仍然退出
}
```

### 保存逻辑

#### 1. 前置检查
```typescript
if (!apiConnected) {
  setError('API未连接');
  return;
}

if (asrState !== 'idle') {
  setToast({ message: '请先停止ASR后再退出', type: 'info' });
  return;
}
```

#### 2. 检查内容
```typescript
const blocks = blockEditorRef.current?.getBlocks();
const hasContent = blocks && blocks.some((b: any) => 
  b.type !== 'note-info' && 
  !b.isBufferBlock && 
  b.content.trim()
);
```

#### 3. 自动保存
如果有内容，执行以下操作：
- 获取笔记信息（标题、类型、相关人员等）
- 设置结束时间
- 生成完整的保存内容（包含笔记信息和正文）
- 调用 `/api/text/save` API 保存到历史记录
- 保存成功后，调用 `endWorkSession()` 清空工作区

#### 4. 错误处理
如果保存失败：
- 显示错误信息
- 询问用户是否仍然退出
- 如果用户选择退出，内容将丢失

---

## 用户体验流程

### 场景 1：有内容，保存成功

```
用户操作流程：
1. 用户在语音笔记中记录了内容
2. 点击 EXIT 按钮
3. 系统自动保存内容到历史记录
4. Toast 提示："笔记已保存，退出成功"
5. 显示欢迎界面
6. 工作区已清空，可以开始新的记录

技术流程：
1. exitWithSave() 被调用
2. 检查 hasContent = true
3. 获取笔记信息和 blocks 数据
4. 设置结束时间
5. 调用 /api/text/save API
6. 保存成功，调用 endWorkSession()
7. 清空 initialBlocks 和草稿
8. 显示欢迎界面
```

### 场景 2：有内容，保存失败

```
用户操作流程：
1. 用户在语音笔记中记录了内容
2. 点击 EXIT 按钮
3. 系统尝试保存，但失败（网络问题、API错误等）
4. 显示错误信息
5. 弹出确认对话框："保存失败，是否仍然退出？未保存的内容将丢失。"
6a. 用户选择"确定"：清空工作区，显示欢迎界面（内容丢失）
6b. 用户选择"取消"：保持当前状态，用户可以重试或手动保存

技术流程：
1. exitWithSave() 被调用
2. 检查 hasContent = true
3. 调用 /api/text/save API 失败
4. 显示错误信息（ErrorBanner 或 Toast）
5. window.confirm() 询问用户
6a. confirmed = true: 调用 endWorkSession()
6b. confirmed = false: 不执行任何操作
```

### 场景 3：没有内容

```
用户操作流程：
1. 用户打开语音笔记，但没有输入任何内容
2. 点击 EXIT 按钮
3. Toast 提示："已退出，可以开始新的记录"
4. 显示欢迎界面

技术流程：
1. exitWithSave() 被调用
2. 检查 hasContent = false
3. 直接调用 endWorkSession()
4. 显示欢迎界面
```

---

## 代码实现

### 修改文件
- `electron-app/src/App.tsx`

### 新增函数

```typescript
// EXIT退出：保存后退出（显示欢迎界面，开始全新记录）
const exitWithSave = async () => {
  if (!apiConnected) {
    setError('API未连接');
    return;
  }

  if (asrState !== 'idle') {
    setToast({ message: '请先停止ASR后再退出', type: 'info' });
    return;
  }

  // 检查是否有内容需要保存
  const blocks = blockEditorRef.current?.getBlocks();
  const hasContent = blocks && blocks.some((b: any) => 
    b.type !== 'note-info' && 
    !b.isBufferBlock && 
    b.content.trim()
  );

  // 如果有内容，先保存
  if (hasContent) {
    try {
      // 获取笔记信息和设置结束时间
      const noteInfo = blockEditorRef.current?.getNoteInfo?.();
      let endTime: string | undefined;
      if (blockEditorRef.current?.setNoteInfoEndTime) {
        endTime = blockEditorRef.current.setNoteInfoEndTime();
        if (noteInfo) {
          noteInfo.endTime = endTime;
        }
      }
      
      // 生成保存内容
      const textContent = blocks
        .filter((b: any) => b.type !== 'note-info' && !b.isBufferBlock && b.content.trim())
        .map((b: any) => b.content)
        .join('\n');
      
      let contentToSave = textContent;
      if (noteInfo) {
        const infoHeader = [
          `📋 笔记信息`,
          noteInfo.title ? `📌 标题: ${noteInfo.title}` : '',
          noteInfo.type ? `🏷️ 类型: ${noteInfo.type}` : '',
          noteInfo.relatedPeople ? `👥 相关人员: ${noteInfo.relatedPeople}` : '',
          noteInfo.location ? `📍 地点: ${noteInfo.location}` : '',
          `⏰ 开始时间: ${noteInfo.startTime}`,
          noteInfo.endTime ? `⏱️ 结束时间: ${noteInfo.endTime}` : '',
          '',
          '---',
          '',
        ].filter(line => line).join('\n');
        
        contentToSave = infoHeader + contentToSave;
      }
      
      // 保存到历史记录
      const response = await fetch(`${API_BASE_URL}/api/text/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          text: contentToSave,
          app_type: 'voice-note',
          blocks: blocks
        }),
      });
      
      const data = await response.json();
      if (data.success) {
        setToast({ message: '笔记已保存，退出成功', type: 'success' });
        // 如果历史记录视图是打开的，刷新历史记录列表
        if (activeView === 'history') {
          loadRecords(1);
        }
        // 退出工作会话
        endWorkSession();
      } else {
        // 保存失败，询问用户
        if (data.error && data.error.code) {
          setSystemError(data.error);
        } else {
          setError(data.message || '保存失败');
        }
        const confirmed = window.confirm('保存失败，是否仍然退出？未保存的内容将丢失。');
        if (confirmed) {
          endWorkSession();
        }
      }
    } catch (e) {
      // 网络错误，询问用户
      setSystemError({
        code: ErrorCodes.NETWORK_TIMEOUT,
        category: ErrorCategory.NETWORK,
        message: '网络错误',
        user_message: '保存失败，请检查网络连接',
        suggestion: '1. 检查网络连接\n2. 重试保存操作\n3. 确认后端服务运行正常',
        technical_info: String(e)
      });
      const confirmed = window.confirm('保存失败，是否仍然退出？未保存的内容将丢失。');
      if (confirmed) {
        endWorkSession();
      }
    }
  } else {
    // 没有内容，直接退出
    setToast({ message: '已退出，可以开始新的记录', type: 'info' });
    endWorkSession();
  }
};
```

### 修改 VoiceNote 组件调用

```typescript
{activeView === 'voice-note' && (
  <VoiceNote
    asrState={asrState}
    onAsrStart={handleAsrStart}
    onAsrStop={handleAsrStop}
    onSaveText={saveText}
    onCopyText={copyText}
    onCreateNewNote={createNewNote}
    apiConnected={apiConnected}
    blockEditorRef={blockEditorRef}
    isWorkSessionActive={isWorkSessionActive}
    onStartWork={() => startWorkSession('voice-note')}
    onEndWork={exitWithSave}  // 使用 exitWithSave 而不是 endWorkSession
    initialBlocks={initialBlocks}
  />
)}
```

---

## 与其他功能的对比

### EXIT vs NEW（新笔记）

| 功能 | EXIT | NEW |
|------|------|-----|
| 触发方式 | 点击 EXIT 按钮 | 点击 NEW 按钮 |
| 保存行为 | 自动保存 | 自动保存 |
| 退出行为 | 显示欢迎界面 | 保持在工作界面 |
| 工作会话 | 结束会话 | 保持会话 |
| 后续操作 | 需要重新开始工作 | 可以立即开始新笔记 |

### EXIT vs 切换视图

| 功能 | EXIT | 切换视图 |
|------|------|---------|
| 触发方式 | 点击 EXIT 按钮 | 点击侧边栏其他视图 |
| 保存行为 | 保存到历史记录 | 保存草稿到 localStorage |
| 工作现场 | 清空，显示欢迎界面 | 保留，稍后恢复 |
| 重新进入 | 全新的空白笔记 | 恢复上次的内容 |
| 用途 | 完成当前工作 | 临时查看其他信息 |

---

## 技术细节

### 1. 草稿自动保存机制（临时退出）

```typescript
// 自动保存草稿到 localStorage（使用blocks）
useEffect(() => {
  if (isWorkSessionActive && activeView === 'voice-note' && blockEditorRef.current) {
    // 清除之前的定时器
    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
    }
    
    // 3秒后自动保存草稿
    autoSaveTimerRef.current = setTimeout(() => {
      try {
        const blocks = blockEditorRef.current?.getBlocks();
        if (blocks && blocks.some((b: any) => b.type !== 'note-info' && !b.isBufferBlock && b.content.trim())) {
          const draft = {
            blocks,
            app: activeView,
            timestamp: Date.now(),
          };
          localStorage.setItem('voiceNoteDraft', JSON.stringify(draft));
          console.log('草稿已自动保存');
        }
      } catch (e) {
        console.error('保存草稿失败:', e);
      }
    }, 3000);
  }
  
  return () => {
    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
    }
  };
}, [isWorkSessionActive, activeView]);
```

### 2. 草稿恢复机制

```typescript
// 恢复草稿（使用blocks）
useEffect(() => {
  try {
    const savedDraft = localStorage.getItem('voiceNoteDraft');
    if (savedDraft) {
      const draft = JSON.parse(savedDraft);
      // 只恢复24小时内的草稿
      const oneDayAgo = Date.now() - 24 * 60 * 60 * 1000;
      if (draft.timestamp > oneDayAgo && draft.blocks) {
        setInitialBlocks(draft.blocks);
        // 恢复草稿时自动启动工作会话
        const appType = draft.app || 'voice-note';
        if (appType === 'voice-note') {
          startWorkSession('voice-note');
        }
        setToast({ message: '已恢复上次未保存的草稿', type: 'info' });
      } else {
        // 清除过期草稿
        localStorage.removeItem('voiceNoteDraft');
      }
    }
  } catch (e) {
    console.error('恢复草稿失败:', e);
  }
}, []);
```

### 3. 工作会话状态管理

```typescript
// 开始工作会话
const startWorkSession = (app: AppView): boolean => {
  setActiveWorkingApp(app);
  setIsWorkSessionActive(true);
  return true;
};

// 结束工作会话（清空所有状态）
const endWorkSession = () => {
  setActiveWorkingApp(null);
  setIsWorkSessionActive(false);
  // 清空blocks
  setInitialBlocks(undefined);
  // 清除草稿
  localStorage.removeItem('voiceNoteDraft');
};
```

---

## 测试建议

### 测试场景 1：有内容，保存成功
1. 在语音笔记中输入或语音识别内容
2. 点击 EXIT 按钮
3. **预期结果**: 
   - Toast 提示"笔记已保存，退出成功"
   - 显示欢迎界面
   - 切换到历史记录，可以看到新保存的记录

### 测试场景 2：有内容，保存失败
1. 在语音笔记中输入内容
2. 关闭后端服务（模拟保存失败）
3. 点击 EXIT 按钮
4. **预期结果**:
   - 显示错误信息
   - 弹出确认对话框
   - 选择"取消"后，保持当前状态

### 测试场景 3：没有内容
1. 打开语音笔记（欢迎界面 → 开始工作）
2. 不输入任何内容
3. 点击 EXIT 按钮
4. **预期结果**:
   - Toast 提示"已退出，可以开始新的记录"
   - 显示欢迎界面

### 测试场景 4：ASR 正在运行
1. 在语音笔记中开始语音识别
2. 点击 EXIT 按钮
3. **预期结果**:
   - Toast 提示"请先停止ASR后再退出"
   - EXIT 按钮应该是禁用状态（由 VoiceNote 组件控制）

### 测试场景 5：切换视图后重新进入
1. 在语音笔记中输入内容
2. 切换到历史记录视图（不点击 EXIT）
3. 再次切换回语音笔记视图
4. **预期结果**:
   - 内容被保留（从草稿恢复）
   - 可以继续编辑

### 测试场景 6：EXIT 后重新进入
1. 在语音笔记中输入内容
2. 点击 EXIT 按钮
3. 再次切换回语音笔记视图
4. **预期结果**:
   - 显示欢迎界面（全新开始）
   - 之前的内容已保存到历史记录

---

## 用户体验改进

### 改进前
- 点击 EXIT 直接退出，不保存内容
- 用户需要记得先点击"保存"或"NEW"按钮
- 容易丢失内容

### 改进后
- 点击 EXIT 自动保存内容
- 用户体验更顺畅
- 减少内容丢失风险

### 保留的灵活性
- 如果保存失败，用户可以选择：
  - 取消退出，重试保存
  - 强制退出，放弃内容
- 用户仍然可以使用"NEW"按钮来保存并继续工作

---

## 相关文件

- `electron-app/src/App.tsx`: 主应用逻辑，退出和保存功能
- `electron-app/src/components/apps/VoiceNote/VoiceNote.tsx`: 语音笔记组件，EXIT 按钮
- `src/api/server.py`: 后端保存 API

---

## 后续优化建议

### 1. 保存进度提示
在保存过程中显示进度提示，避免用户误以为程序无响应：
```typescript
setToast({ message: '正在保存...', type: 'info' });
```

### 2. 快捷键支持
添加键盘快捷键（如 Cmd+Q 或 Ctrl+Q）快速退出：
```typescript
useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'q') {
      e.preventDefault();
      exitWithSave();
    }
  };
  window.addEventListener('keydown', handleKeyDown);
  return () => window.removeEventListener('keydown', handleKeyDown);
}, []);
```

### 3. 自动保存提示
在退出时显示上次自动保存的时间，让用户更放心：
```typescript
setToast({ 
  message: `笔记已保存（最后编辑：${lastEditTime}），退出成功`, 
  type: 'success' 
});
```

---

## 总结

通过实现 `exitWithSave` 函数，优化了 EXIT 按钮的行为，使其更符合用户的直觉和预期：

**核心改进**:
- ✅ EXIT 时自动保存内容
- ✅ 区分两种工作模式（临时退出 vs 正式退出）
- ✅ 保存失败时给用户选择权
- ✅ 提供清晰的用户反馈

**设计原则**:
- 🎯 用户友好：减少操作步骤，避免内容丢失
- 🔒 安全可靠：保存失败时不强制退出
- 🎨 体验流畅：自动保存 + 即时反馈
- 🔄 灵活可控：用户可以选择是否强制退出

**功能状态**: ✅ 已完成

