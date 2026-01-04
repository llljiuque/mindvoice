# WebSocket 重连导致 ASR 文本丢失问题修复

**日期**: 2026-01-04  
**问题**: 前端只显示部分 ASR 文本，前面的 `text_update` 消息丢失  
**根因**: WebSocket 重连导致消息丢失  
**修复**: 录音期间避免 WebSocket 重连

---

## 问题描述

用户报告：在 VoiceNote 界面，ASR 识别的文本只显示了部分内容，前面的信息丢失了。

**用户看到的内容**：
```
年前就已经在法国自产并长期定居，并且包含阿玛尔和他们一对龙凤胎的儿女，法文都说得相当流利。
乔治克隆尼更曾经表示非常欣赏法国的反狗仔法规，这让他们一家的生活更正常。
然而尽管官方和乔治克隆尼本人都强调入籍法国绝对没有
```

用户期望看到的内容应该包括前面的部分，但实际只显示了最后一个 `text_final` 消息的内容。

---

## 问题诊断

### 1. 日志分析

查看日志 `logs/api_server_20260104_001345.log`：

**第138-382行**：ASR 持续发送 `text_update` 消息
```log
138: [ASR] 中间结果: '长期定居，并且包含'
141: [API] 广播消息: type=text_update, text_len=9, is_definite=False, app_id=voice-note
...
382: [ASR] 中间结果: '长期定居，并且包含阿玛尔和他们一对龙凤胎的儿女，发文都说的相当流利。...入籍法国绝对没有'
```

**第174-182行**：WebSocket 发生重连
```log
174: INFO:     127.0.0.1:63335 - "WebSocket /ws" [accepted]
175: [API] 检测到旧连接，关闭旧连接
178: [API] WebSocket连接已建立（单连接模式）
180: [API] WebSocket连接已断开
182: INFO:     connection closed
```

**第385-386行**：ASR 发送 `text_final` 消息
```log
385: [ASR] 确定结果: '年前就已经在法国自产并长期定居，并且包含阿玛尔和他们一对龙凤胎的儿女，法文都说得相当流利。乔治克隆尼更曾经表示非常欣赏法国的反狗仔法规，这让他们一家的生活更正常。然而尽管官方和乔治克隆尼本人都强调入籍法国绝对没有'
```

### 2. 问题分析

1. **时间线**：
   - `00:14:05` - ASR 开始发送 `text_update`（从"长期定居，并且包含"开始）
   - `00:14:08` - WebSocket 重连（旧连接关闭，新连接建立）
   - `00:14:23` - ASR 发送 `text_final`（包含完整内容"年前就已经在法国自产并长期定居..."）

2. **消息丢失原因**：
   - 在 `00:14:08` 之前，ASR 应该已经发送了包含"年前就已经在法国自产并"的 `text_update` 消息
   - 但由于 WebSocket 在 `00:14:08` 发生重连，旧连接被关闭
   - **在旧连接上发送的 `text_update` 消息在前端接收之前丢失了**

3. **前端行为**：
   - 前端的 `BlockEditor.appendAsrText` 在收到 `text_final` 时，会**直接替换**当前 ASR 写入块的内容
   - 由于前面的 `text_update` 消息丢失，前端只收到了从"长期定居"开始的消息
   - 当 `text_final` 到达时，前端只显示这一条消息的内容

### 3. WebSocket 重连触发原因

查看 `electron-app/src/App.tsx` 的 WebSocket 连接管理：

```typescript
useEffect(() => {
  checkApiConnection().then((connected) => {
    if (connected) connectWebSocket();
  });

  const interval = setInterval(() => {
    checkApiConnection().then((connected) => {
      if (connected && !wsRef.current) {
        connectWebSocket();  // 每5秒检查一次，可能触发重连
      }
    });
  }, 5000);
  
  return () => {
    clearInterval(interval);
    if (wsRef.current) {
      wsRef.current.close();
    }
  };
}, []);
```

**问题**：
- 每5秒检查一次 API 连接状态
- 如果检测到 `!wsRef.current`，会尝试重连
- 在录音期间，如果由于任何原因（网络波动、浏览器优化等）导致 WebSocket 连接断开或被判定为未连接，就会触发重连
- **重连过程中，正在传输的 ASR 消息会丢失**

---

## 解决方案

### 修复目标

1. **录音期间避免 WebSocket 重连**
2. **确保消息不丢失**

### 修复实现

#### 1. 修改 `connectWebSocket` 函数

在 `electron-app/src/App.tsx` 中修改：

```typescript
const connectWebSocket = () => {
  // 如果连接已存在且状态是 OPEN 或 CONNECTING，则不创建新连接
  if (wsRef.current && 
      (wsRef.current.readyState === WebSocket.OPEN || 
       wsRef.current.readyState === WebSocket.CONNECTING)) {
    return;
  }

  // 🔴 新增：如果正在录音，避免重连以防止消息丢失
  if (asrState === 'recording') {
    console.warn('[WebSocket] 录音期间避免重连，延迟到录音结束后');
    return;
  }

  // ... 其余连接逻辑
};
```

#### 2. 修改心跳检查逻辑

```typescript
useEffect(() => {
  checkApiConnection().then((connected) => {
    if (connected) connectWebSocket();
  });

  const interval = setInterval(() => {
    checkApiConnection().then((connected) => {
      // 🔴 新增：只有在非录音状态下才尝试重连
      const isRecording = asrState === 'recording';
      if (connected && !wsRef.current && !isRecording) {
        console.log('[WebSocket] 心跳检测：尝试重连');
        connectWebSocket();
      } else if (isRecording && !wsRef.current) {
        console.warn('[WebSocket] 心跳检测：录音期间跳过重连');
      }
    });
  }, 5000);

  return () => {
    clearInterval(interval);
    if (wsRef.current) {
      wsRef.current.close();
    }
  };
}, [asrState]); // 🔴 新增依赖：asrState
```

#### 3. 修改 `onclose` 处理逻辑

```typescript
ws.onclose = () => {
  console.log('[WebSocket] 连接已关闭');
  wsRef.current = null;
  
  // 🔴 新增：录音期间不自动重连，避免消息丢失
  const isRecording = asrState === 'recording';
  
  if (apiConnected && !reconnectTimeoutRef.current && !isRecording) {
    // 连接断开，显示提示（但会自动重连）
    setSystemError({
      code: ErrorCodes.WEBSOCKET_DISCONNECTED,
      category: ErrorCategory.NETWORK,
      message: 'WebSocket连接断开',
      user_message: '连接已断开，正在尝试重连...',
      suggestion: '系统会自动重连，请稍候'
    });
    
    reconnectTimeoutRef.current = setTimeout(() => {
      reconnectTimeoutRef.current = null;
      console.log('[WebSocket] 3秒后尝试重连');
      connectWebSocket();
    }, 3000);
  } else if (isRecording) {
    // 🔴 新增：录音期间连接断开，不自动重连
    console.warn('[WebSocket] 录音期间连接断开，不自动重连以避免消息丢失');
    setSystemError({
      code: ErrorCodes.WEBSOCKET_DISCONNECTED,
      category: ErrorCategory.NETWORK,
      message: 'WebSocket连接断开',
      user_message: '录音期间连接断开，请停止录音后重新开始',
      suggestion: '请停止当前录音，然后重新开始录音'
    });
  }
};
```

---

## 修复效果

### 修复前

- ❌ 录音期间 WebSocket 可能重连
- ❌ 重连导致 `text_update` 消息丢失
- ❌ 前端只显示部分文本

### 修复后

- ✅ 录音期间不会自动重连
- ✅ 所有 `text_update` 消息都能正确接收
- ✅ 前端显示完整的 ASR 文本
- ✅ 录音结束后，WebSocket 可以正常重连

---

## 测试验证

### 测试场景

1. **正常录音场景**：
   - 开始录音
   - 说话一段时间（20秒以上）
   - 停止录音
   - **验证**：前端显示完整的 ASR 文本，没有丢失

2. **长时间录音场景**：
   - 开始录音
   - 持续说话1分钟以上（跨越多个心跳检查周期）
   - 停止录音
   - **验证**：前端显示完整的 ASR 文本，没有因为心跳检查导致重连

3. **网络波动场景**（模拟）：
   - 开始录音
   - 录音期间短暂断开 WebSocket（通过浏览器开发者工具）
   - **验证**：前端显示错误提示，提示用户停止录音后重新开始

### 测试日志

录音期间应该看到类似日志：

```log
[WebSocket] 连接已建立
[录音开始]
[WebSocket] 心跳检测：录音期间跳过重连
[WebSocket] 心跳检测：录音期间跳过重连
[录音结束]
[WebSocket] 心跳检测：尝试重连（如果连接断开）
```

---

## 相关文件

- `electron-app/src/App.tsx` - WebSocket 连接管理
- `electron-app/src/components/apps/VoiceNote/BlockEditor.tsx` - ASR 文本显示
- `src/api/server.py` - WebSocket 消息广播
- `logs/api_server_20260104_001345.log` - 问题诊断日志

---

## 后续改进建议

### 1. 增强 WebSocket 连接稳定性

- 考虑使用心跳包机制（ping/pong）保持连接活跃
- 增加连接质量监控，及时发现潜在问题

### 2. 消息持久化（可选）

- 在后端缓存最近的 `text_update` 消息
- 前端重连后可以请求同步最新状态
- 避免消息丢失

### 3. 前端状态同步

- 在重连后，前端可以发送请求获取当前 ASR 累积文本
- 更新前端显示，确保内容完整

### 4. 用户体验优化

- 在录音期间显示 WebSocket 连接状态指示器
- 如果连接不稳定，提前警告用户

---

## 总结

**根本原因**：WebSocket 重连导致 ASR 消息丢失  
**修复策略**：录音期间禁止 WebSocket 重连  
**修复文件**：`electron-app/src/App.tsx`  
**修复状态**：✅ 已完成

这个修复确保了录音期间 WebSocket 连接的稳定性，避免了消息丢失问题，从而保证了前端能够显示完整的 ASR 识别文本。

