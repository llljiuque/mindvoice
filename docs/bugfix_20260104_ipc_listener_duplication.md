# Bug修复：IPC监听器重复注册导致状态失控

## 问题描述

用户报告：在工作一段时间后，出现以下异常现象：
1. **后台轮询正常**：日志显示轮询仍在继续
2. **麦克风状态异常**：麦克风显示正在使用
3. **UI状态错误**：语音笔记的录音按钮恢复到等待录音状态（绿色）
4. **数据不更新**：文字不再更新到界面
5. **日志与UI不一致**：后台和前端状态完全不同步

## 问题分析日期
2026-01-04

## 根本原因

### 1. IPC 监听器的生命周期问题

在 `App.tsx` 中，IPC 监听器设置在 `useEffect` 中，依赖数组为空 `[]`：

```typescript
// App.tsx 第 318-384 行
useEffect(() => {
  console.log('[IPC] 设置消息监听器');
  
  const handleAsrMessage = (data: any) => {
    // ... 处理消息
    blockEditorRef.current?.appendAsrText(...);
  };

  if (window.electronAPI?.onAsrMessage) {
    window.electronAPI.onAsrMessage(handleAsrMessage);
    console.log('[IPC] 监听器已设置');
  }

  return () => {
    console.log('[IPC] 移除消息监听器');
    if (window.electronAPI?.removeAsrMessageListener) {
      window.electronAPI.removeAsrMessageListener(handleAsrMessage);
    }
  };
}, []); // ⚠️ 空依赖数组
```

### 2. removeListener 实现的问题

在 `preload.ts` 中，`removeAsrMessageListener` 的实现有严重缺陷：

```typescript
// preload.ts 第 21-23 行
removeAsrMessageListener: (callback: (message: any) => void) => {
  ipcRenderer.removeListener('asr-message', callback);
},
```

**问题所在**：
- Electron 的 `ipcRenderer.removeListener()` 基于**函数引用相等性**来移除监听器
- 如果传入的 `callback` 引用与注册时不同，移除会失败
- React 的热重载、状态更新可能导致组件重新挂载，创建新的函数引用

### 3. 监听器累积效应

随着时间推移，可能发生以下情况：

1. **热重载触发** → App 组件重新挂载
2. **新监听器注册** → 添加新的 `handleAsrMessage`
3. **旧监听器未移除** → 因为函数引用不同
4. **多个监听器共存** → 每个监听器都会处理消息
5. **blockEditorRef 被覆盖** → 旧监听器引用的 ref 可能已失效

### 4. 视图切换的影响

当切换视图时（如从 voice-note 切换到 history）：

```typescript
// App.tsx 第 856-873 行
{activeView === 'voice-note' && (
  <VoiceNote
    blockEditorRef={blockEditorRef}
    // ...
  />
)}
```

- **VoiceNote 组件卸载** → `blockEditorRef.current` 可能变为 null
- **IPC 监听器仍在运行** → 继续接收消息
- **调用失效的 ref** → `blockEditorRef.current?.appendAsrText()` 无效
- **状态不同步** → 后端继续录音，但前端 UI 已重置

## 复现条件

1. 启动应用并进入语音笔记
2. 开始录音
3. 在录音过程中切换到其他视图（如历史记录）
4. 再切换回语音笔记
5. 或者：在开发环境中触发热重载

结果：
- 后端 ASR 状态可能仍是 "recording"
- 前端 UI 状态被重置为 "idle"
- 消息继续发送，但无法正确处理

## 技术细节

### IPC 监听器的工作机制

```
主进程轮询 (100ms)
    ↓
收到后端消息
    ↓
mainWindow.webContents.send('asr-message', message)
    ↓
渲染进程 ipcRenderer.on('asr-message', callback)
    ↓
所有已注册的 callback 都会被调用 ⚠️
```

### removeListener 的失败场景

```typescript
// 场景 1：函数引用不同
const callback1 = (msg) => console.log(msg);
ipcRenderer.on('asr-message', callback1);

const callback2 = (msg) => console.log(msg); // 新的函数对象
ipcRenderer.removeListener('asr-message', callback2); // ❌ 无效

// 场景 2：React 热重载
// 第一次渲染
const handleMsg = (msg) => { /* ... */ };
ipcRenderer.on('asr-message', handleMsg);

// 热重载后（新的组件实例）
const handleMsg = (msg) => { /* ... */ }; // 新的函数引用
ipcRenderer.removeListener('asr-message', handleMsg); // ❌ 移除失败
```

## 解决方案

### 方案 1：使用 removeAllListeners（推荐）

修改 `preload.ts`，添加移除所有监听器的方法：

```typescript
contextBridge.exposeInMainWorld('electronAPI', {
  // ... 其他方法
  onAsrMessage: (callback: (message: any) => void) => {
    // 先移除所有旧的监听器，避免累积
    ipcRenderer.removeAllListeners('asr-message');
    ipcRenderer.on('asr-message', (_event, message) => callback(message));
  },
  removeAllAsrMessageListeners: () => {
    ipcRenderer.removeAllListeners('asr-message');
  },
});
```

修改 `App.tsx`：

```typescript
useEffect(() => {
  console.log('[IPC] 设置消息监听器');
  
  const handleAsrMessage = (data: any) => {
    // ... 处理逻辑
  };

  if (window.electronAPI?.onAsrMessage) {
    window.electronAPI.onAsrMessage(handleAsrMessage);
    console.log('[IPC] 监听器已设置');
  }

  return () => {
    console.log('[IPC] 移除所有消息监听器');
    if (window.electronAPI?.removeAllAsrMessageListeners) {
      window.electronAPI.removeAllAsrMessageListeners();
    }
  };
}, []);
```

### 方案 2：使用 ref 保存回调引用

```typescript
const asrMessageHandlerRef = useRef<((data: any) => void) | null>(null);

useEffect(() => {
  const handleAsrMessage = (data: any) => {
    // ... 处理逻辑
  };
  
  asrMessageHandlerRef.current = handleAsrMessage;
  
  if (window.electronAPI?.onAsrMessage) {
    window.electronAPI.onAsrMessage(handleAsrMessage);
  }

  return () => {
    if (asrMessageHandlerRef.current && window.electronAPI?.removeAsrMessageListener) {
      window.electronAPI.removeAsrMessageListener(asrMessageHandlerRef.current);
    }
  };
}, []);
```

### 方案 3：添加状态同步检查

在切换视图或组件挂载时，主动从后端同步状态：

```typescript
// App.tsx
useEffect(() => {
  // 当 activeView 切换到 voice-note 时，同步 ASR 状态
  if (activeView === 'voice-note' && apiConnected) {
    fetch(`${API_BASE_URL}/api/asr/status`)
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          setAsrState(data.state);
        }
      });
  }
}, [activeView, apiConnected]);
```

### 方案 4：后端状态强制同步

修改主进程轮询逻辑，定期推送状态：

```typescript
// main.ts
async function pollMessages() {
  // ... 现有逻辑
  
  // 每 5 秒推送一次完整状态（而不仅仅是增量消息）
  if (Date.now() - lastStateSync > 5000) {
    const stateResponse = await fetch(`${API_URL}/api/asr/status`);
    const stateData = await stateResponse.json();
    mainWindow?.webContents.send('asr-message', {
      type: 'state_sync',
      state: stateData.state,
      timestamp: Date.now()
    });
    lastStateSync = Date.now();
  }
}
```

## 推荐修复方案

**组合方案**：方案 1 + 方案 3

1. **立即修复**：使用 `removeAllListeners` 避免监听器累积（方案 1）
2. **增强同步**：在视图切换时主动同步状态（方案 3）

这样可以：
- ✅ 防止监听器累积
- ✅ 确保 UI 与后端状态一致
- ✅ 处理热重载场景
- ✅ 处理视图切换场景

## 实施步骤

1. 修改 `electron/preload.ts`
2. 修改 `src/App.tsx` 的 IPC 监听器清理逻辑
3. 在 App.tsx 中添加视图切换时的状态同步
4. 添加调试日志，监控监听器注册/移除
5. 测试场景：
   - 热重载
   - 视图切换
   - 长时间录音
   - 切换期间录音

## 预期效果

修复后：
- ✅ 监听器不会累积
- ✅ UI 状态与后端保持一致
- ✅ 切换视图后状态正确恢复
- ✅ 热重载不会导致状态错乱
- ✅ 日志与 UI 显示一致

## 相关文件

- `electron-app/electron/preload.ts` - IPC 接口定义
- `electron-app/src/App.tsx` - IPC 监听器设置
- `electron-app/electron/main.ts` - 主进程轮询逻辑
- `electron-app/src/components/apps/VoiceNote/VoiceNote.tsx` - 语音笔记组件

## 后续优化建议

1. **添加监听器计数监控**：在开发模式下，监控当前注册的监听器数量
2. **状态机验证**：在状态转换时验证合法性
3. **心跳机制**：前后端定期对账，确保状态一致
4. **错误恢复**：检测到状态不一致时，自动重置到安全状态

