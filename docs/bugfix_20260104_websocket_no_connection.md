# WebSocket 连接断开导致前端无ASR显示问题诊断

**日期**: 2026-01-04  
**问题**: 前端UI什么信息都没显示  
**根因**: WebSocket 连接在录音期间完全断开，导致所有 ASR 消息被跳过  
**状态**: 🔍 诊断中

---

## 问题描述

用户报告：前端 UI 在录音期间完全没有显示任何 ASR 文本。

---

## 问题诊断

### 1. 日志分析 (`logs/api_server_20260104_002258.log`)

**关键证据**：

```log
行133: [API] WebSocket连接已断开
行170: [API] 无活跃连接，跳过消息: type=text_update
行176: [API] 无活跃连接，跳过消息: type=text_update
...
行254: [API] 无活跃连接，跳过消息: type=text_final
```

**时间线**：

1. **00:23:07-00:23:11** - WebSocket 多次建立和关闭（3次重连）
   ```log
   73: INFO:     127.0.0.1:64529 - "WebSocket /ws" [accepted]  (第1次)
   74: [API] WebSocket连接已建立（单连接模式）
   78: INFO:     127.0.0.1:64531 - "WebSocket /ws" [accepted]  (第2次)
   79: [API] 检测到旧连接，关闭旧连接
   82: [API] WebSocket连接已建立（单连接模式）
   84: [API] WebSocket连接已断开                              (第1次断开)
   88: INFO:     127.0.0.1:64540 - "WebSocket /ws" [accepted]  (第3次)
   89: [API] 检测到旧连接，关闭旧连接
   92: [API] WebSocket连接已建立（单连接模式）
   94: [API] WebSocket连接已断开                              (第2次断开)
   ```

2. **00:23:12** - 录音开始
   ```log
   98: [语音服务] 开始录音... (app_id=voice-note)
   123: POST /api/recording/start HTTP/1.1" 200 OK
   ```

3. **00:23:12** - WebSocket 连接断开（录音开始后立即断开！）
   ```log
   133: [API] WebSocket连接已断开  ⬅️ 问题关键
   ```

4. **00:23:17开始** - ASR 开始发送消息，但全部被跳过
   ```log
   166-170: [ASR] 中间结果: '穿鞋之后就推销高价的鞋油，还会'
           [API] 广播消息: type=text_update, text_len=15, app_id=voice-note
           [API] 无活跃连接，跳过消息: type=text_update  ⬅️ 消息丢失
   ```

### 2. 问题根因

**后端 WebSocket 连接管理**：
- 使用全局变量 `current_connection` 保存当前连接
- 当 `current_connection = None` 时，所有广播消息都被跳过

```python
async def send_to_client(message: dict):
    global current_connection
    
    if not current_connection:
        logger.debug(f"[API] 无活跃连接，跳过消息: type={message.get('type')}")
        return
    
    try:
        await current_connection.send_json(message)
        logger.debug(f"[API] 消息已发送: type={message.get('type')}")
    except Exception as e:
        logger.error(f"[API] 发送消息失败: {e}")
        current_connection = None
```

**前端 WebSocket 行为异常**：
1. 在录音开始前，前端频繁建立和关闭 WebSocket 连接（3次）
2. 录音开始后，最后一次 WebSocket 连接立即断开
3. 之后没有重新建立连接（可能是因为之前的错误修复导致）

### 3. 之前的错误修复的副作用

之前为了解决"WebSocket 重连导致消息丢失"问题，添加了以下逻辑：

```typescript
// ❌ 错误的修复：阻止录音期间重连
if (asrState === 'recording') {
  console.warn('[WebSocket] 录音期间避免重连，延迟到录音结束后');
  return;
}
```

这个修复导致：
- 如果 WebSocket 在录音期间断开，无法重连
- 整个录音过程没有 WebSocket 连接
- 所有 ASR 消息都被跳过

---

## 解决方案

### 1. 撤销之前的修复

撤销"禁止录音期间重连"的逻辑，恢复原有的 WebSocket 重连机制：

```typescript
// ✅ 恢复原有逻辑
const connectWebSocket = () => {
  // 如果连接已存在且状态是 OPEN 或 CONNECTING，则不创建新连接
  if (wsRef.current && 
      (wsRef.current.readyState === WebSocket.OPEN || 
       wsRef.current.readyState === WebSocket.CONNECTING)) {
    console.log(`[WebSocket] 连接已存在，状态=${wsRef.current.readyState === WebSocket.OPEN ? 'OPEN' : 'CONNECTING'}，跳过创建`);
    return;
  }

  console.log('[WebSocket] 创建新连接...');
  const ws = new WebSocket(WS_URL);
  // ... 其余逻辑
};
```

### 2. 添加详细日志

在 WebSocket 消息处理中添加更详细的日志，便于追踪 `app_id` 匹配问题：

```typescript
ws.onmessage = (event) => {
  try {
    const data = JSON.parse(event.data);

    // 检查app_id是否匹配
    if (data.app_id && data.app_id !== activeView) {
      console.warn(`[WebSocket] 消息app_id (${data.app_id}) 与当前视图 (${activeView}) 不匹配，忽略消息，当前activeView=${activeView}`);
      return;
    }

    console.log(`[WebSocket] 收到消息: type=${data.type}, app_id=${data.app_id || 'none'}, activeView=${activeView}`);

    switch (data.type) {
      // ... 消息处理
    }
  } catch (e) {
    console.error('解析WebSocket消息失败:', e);
  }
};
```

### 3. 需要进一步调查的问题

**为什么前端会频繁重连 WebSocket？**

可能的原因：
1. React 组件重渲染导致 `useEffect` 重复执行
2. 状态变化触发 WebSocket 重新创建
3. `activeView` 状态变化导致连接重建
4. 浏览器或网络问题导致连接不稳定

**调查方向**：
1. 检查浏览器控制台的 WebSocket 日志
2. 查看 React DevTools 的组件渲染次数
3. 添加日志追踪 `useEffect` 的执行次数
4. 检查 `activeView` 的状态变化

---

## 测试验证

### 测试步骤

1. 刷新前端页面
2. 打开浏览器控制台，查看 WebSocket 日志
3. 开始录音
4. 说话一段时间
5. 停止录音

### 预期结果

**浏览器控制台日志**：
```log
[WebSocket] 创建新连接...
[WebSocket] 连接已建立
[WebSocket] 收到消息: type=initial_state, app_id=none, activeView=voice-note
[录音开始]
[WebSocket] 收到消息: type=text_update, app_id=voice-note, activeView=voice-note
[WebSocket] 收到消息: type=text_update, app_id=voice-note, activeView=voice-note
...
[WebSocket] 收到消息: type=text_final, app_id=voice-note, activeView=voice-note
```

**后端日志**：
```log
[API] WebSocket连接已建立（单连接模式）
[API] 广播消息: type=text_update, text_len=15, app_id=voice-note
[API] 消息已发送: type=text_update
[API] 广播消息: type=text_final, text_len=50, app_id=voice-note
[API] 消息已发送: type=text_final
```

**前端UI**：
- 实时显示 ASR 文本
- 文本逐字增量更新
- 最终显示完整的识别结果

### 如果问题依旧

1. **检查 `app_id` 匹配**：
   - 查看浏览器控制台是否有 `app_id` 不匹配的警告
   - 确认 `activeView` 的值是否正确

2. **检查 WebSocket 连接状态**：
   - 查看浏览器控制台是否有 WebSocket 连接/断开的日志
   - 确认录音期间 WebSocket 是否保持连接

3. **检查后端广播**：
   - 查看后端日志是否有"无活跃连接"的消息
   - 确认 `current_connection` 是否为 `None`

---

## 相关文件

- `electron-app/src/App.tsx` - WebSocket 连接管理
- `src/api/server.py` - WebSocket 消息广播
- `docs/bugfix_20260104_websocket_reconnect_message_loss.md` - 之前的错误修复

---

## 状态

- ✅ 已撤销错误的修复
- ✅ 已添加详细日志
- 🔍 等待用户测试验证
- 🔍 需要进一步调查频繁重连的根本原因

