# 停止ASR完整流程分析

**日期**: 2026-01-04  
**分析者**: 深圳王哥 & AI

---

## 完整停止流程

### 前端（Electron App）

```
用户点击停止按钮
    ↓
App.tsx: stopAsr()
    ↓
1. 设置 asrState = 'stopping'
2. 设置 10秒超时保护
3. 发送 POST /api/recording/stop
    ↓
等待后端响应...
```

### 后端（Python FastAPI）

```
接收 /api/recording/stop 请求
    ↓
server.py: stop_recording()
    ↓
voice_service.stop_recording()
    ↓
【阶段1：停止录音器】
1. _notify_state_change(STOPPING)  → 发送消息到前端
2. recorder.stop_recording()       → 停止音频采集
3. 清除音频回调
    ↓
【阶段2：触发ASR停止】
recorder.stop_recording() 内部:
    → audio_asr_gateway.stop()
    → _on_speech_end() 回调
    → 发送 None 到 ASR 音频队列
    ↓
【阶段3：等待ASR完成】⏳
VoiceService 等待循环（最多5秒）:
    while self._streaming_active and waited_time < 5.0:
        time.sleep(0.1)
        waited_time += 0.1
    
在这个等待期间，可能发生：
    ✅ ASR 继续处理队列中的音频数据
    ✅ ASR 发送器发送负包 (seq=-N, is_last=True)
    ✅ ASR 接收器继续接收服务器响应
    ✅ 可能收到 text_update (中间结果)
    ✅ 可能收到 text_final (确定结果，带时间信息)
    ✅ 最终收到 is_last_package=True
    ↓
【阶段4：ASR断开连接】
ASR接收器检测到 is_last_package:
    → _disconnect()
    → 关闭 WebSocket
    → finally: _streaming_active = False
    → _on_asr_disconnected() 回调
    → VoiceService._streaming_active = False
    ↓
【阶段5：完成停止】
等待循环退出
    → _notify_state_change(IDLE)  → 发送消息到前端
    → 返回 final_text
    ↓
后端返回响应: { "success": true, "final_text": "..." }
```

### 前端接收响应

```
stopAsr() 收到响应
    ↓
1. 清除超时定时器
2. 显示 Toast: "ASR已停止"
3. 状态通过 IPC 消息更新为 'idle'
```

---

## 关键时序点

### 正常流程时序

```
T0:  用户点击停止
T1:  前端 asrState → 'stopping'
T2:  发送 /api/recording/stop
T3:  后端停止录音器
T4:  发送 state_change(STOPPING) → 前端
T5:  发送 None 到ASR队列
T6:  ASR发送负包
T7-T12: 等待期间，可能收到多个 text_update/text_final
T13: ASR收到 is_last_package
T14: ASR断开连接
T15: _streaming_active → False
T16: 发送 state_change(IDLE) → 前端
T17: 后端返回 HTTP 响应
T18: 前端显示 Toast
```

### 可能的问题场景

#### 场景1：等待超时（5秒）

```
问题：ASR 一直没有返回 is_last_package
      → waited_time >= 5.0
      → 强制退出等待
      → 但 _streaming_active 可能还是 True
      → finally 块强制设为 False
结果：可能丢失最后的识别结果
```

#### 场景2：HTTP请求超时（5秒）

```
问题：后端在等待 ASR 完成时，前端的 fetch 超时了
      → AbortSignal.timeout(5000) 触发
      → 前端显示错误 Toast
      → 但后端还在继续等待
结果：前端和后端状态不一致
```

#### 场景3：ASR WebSocket 连接问题

```
问题：ASR 内部的 WebSocket 连接已断开
      → 后端等待 5 秒超时
      → 返回响应，但可能包含错误信息
可能原因：
    - 网络问题
    - 火山引擎服务器问题
    - WebSocket 连接意外关闭
```

---

## 当前问题分析

### 用户报告的问题

停止ASR时，显示错误："网络连接失败，请检查网络连接 #1000"

### 可能的原因

1. **前端 fetch 超时（5秒）**
   - 后端等待ASR完成需要最多5秒
   - 前端 fetch 也设置了5秒超时
   - 如果后端等待接近5秒，前端可能先超时

2. **定期API检查干扰**
   - `checkApiConnection()` 每5秒运行一次
   - 如果在停止ASR时恰好运行，可能设置网络错误

3. **后端实际返回了错误**
   - ASR停止过程中出现异常
   - 后端返回 success=false
   - 但前端的错误处理可能不够清晰

---

## 改进建议

### 1. 调整超时时间

```typescript
// 前端：给后端更多时间
const response = await fetch(`${API_BASE_URL}/api/recording/stop`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ user_edited_text: null }),
  signal: AbortSignal.timeout(8000) // 8秒，给后端充足时间
});
```

### 2. 改进日志

**前端添加：**
```typescript
console.log('[App] 开始停止ASR...');
console.log('[App] 发送停止请求到: /api/recording/stop');
console.log(`[App] 停止请求响应状态: ${response.status}`);
console.log('[App] 停止请求响应数据:', data);
```

**后端添加：**
```python
logger.info("[语音服务] 等待ASR完成...")
logger.info(f"[语音服务] 等待完成，用时: {waited_time:.2f}秒")
logger.info(f"[语音服务] _streaming_active={self._streaming_active}")
```

### 3. 避免错误覆盖

```typescript
// checkApiConnection 中
if (!systemError) {
  // 只在没有其他错误时才设置网络错误
  setSystemError({...});
}
```

### 4. 使用 Toast 而不是 Banner

```typescript
// stopAsr 的错误处理
setToast({ 
  message: `停止ASR失败: ${errorMessage}`, 
  type: 'error',
  duration: 5000
});
```

---

## 测试建议

### 测试1：正常停止

```
1. 开始录音
2. 说一段话（约5秒）
3. 点击停止
4. 观察控制台日志：
   [App] 开始停止ASR...
   [App] 发送停止请求到: /api/recording/stop
   [主进程] [轮询] 收到消息: state_change → stopping
   [主进程] [轮询] 收到消息: text_update/text_final (可能多个)
   [主进程] [轮询] 收到消息: state_change → idle
   [App] 停止请求响应状态: 200
   [App] ASR停止成功
5. 应该看到 Toast: "ASR已停止"
6. 不应该看到红色错误横幅
```

### 测试2：快速停止

```
1. 开始录音
2. 立即点击停止（不说话）
3. 观察是否有错误
```

### 测试3：长时间录音后停止

```
1. 开始录音
2. 说话1分钟
3. 点击停止
4. 观察停止耗时（应该<5秒）
```

---

## 当前实现的改进

✅ 已完成：
1. stopAsr 使用 Toast 而不是 SystemError Banner
2. 添加详细的控制台日志
3. fetch 请求添加 5秒超时
4. checkApiConnection 避免覆盖其他错误
5. 轮询日志显示消息详情

⏳ 待完成：
1. 调整前端超时时间为 8秒
2. 添加后端详细日志
3. 测试验证

---

**分析完成时间**: 2026-01-04

