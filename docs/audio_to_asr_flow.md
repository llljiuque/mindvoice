# 音频到ASR流程详解

本文档详细说明 MindVoice 项目中从音频采集到语音识别（ASR）的完整流程。

## 📋 目录

- [流程概览](#流程概览)
- [详细流程](#详细流程)
- [关键技术点](#关键技术点)
- [数据流图](#数据流图)
- [代码位置](#代码位置)
- [故障排查](#故障排查)

---

## 流程概览

音频到ASR的完整流程包含以下14个步骤：

```
前端触发 → API接收 → VoiceService启动 → 音频录制器初始化 
→ 音频采集 → 消费线程 → VoiceService接收 → ASR提供者接收 
→ WebSocket发送 → ASR服务识别 → 结果接收 → 结果处理 
→ API广播 → 前端显示
```

---

## 详细流程

### 1. 前端触发录音

**位置**: `electron-app/src/App.tsx`

前端通过 REST API 调用启动录音：

```typescript
const startAsr = () => callAsrApi('/api/recording/start');
```

**关键代码**:
```typescript
const callAsrApi = async (endpoint: string) => {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, { 
    method: 'POST' 
  });
  const data = await response.json();
  return data.success;
};
```

---

### 2. 后端API接收请求

**位置**: `src/api/server.py`

FastAPI 接收 POST 请求并调用语音服务：

```python
@app.post("/api/recording/start", response_model=StartRecordingResponse)
async def start_recording():
    if not voice_service:
        raise HTTPException(status_code=503, detail="语音服务未初始化")
    
    try:
        success = voice_service.start_recording()
        if success:
            return StartRecordingResponse(success=True, message="录音已开始")
        else:
            return StartRecordingResponse(success=False, message="启动录音失败")
    except Exception as e:
        # 错误处理...
```

---

### 3. VoiceService 启动录音和ASR

**位置**: `src/services/voice_service.py`

`VoiceService.start_recording()` 方法执行以下操作：

1. **启动 ASR 流式识别**
   - 建立 WebSocket 连接到火山引擎 ASR 服务
   - 创建异步发送和接收任务

2. **设置音频回调**
   ```python
   self.recorder.set_on_audio_chunk_callback(self._on_audio_chunk)
   ```

3. **启动音频录制器**
   ```python
   success = self.recorder.start_recording()
   ```

**关键代码**:
```python
def start_recording(self) -> bool:
    # 启动流式 ASR 识别
    if self.asr_provider:
        self.asr_provider.set_on_text_callback(self._on_asr_text_received)
        await self.asr_provider.start_streaming_recognition(language)
        self.recorder.set_on_audio_chunk_callback(self._on_audio_chunk)
    
    # 开始录音
    success = self.recorder.start_recording()
    if success:
        self._notify_state_change(RecordingState.RECORDING)
    return success
```

---

### 4. 音频录制器初始化

**位置**: `src/utils/audio_recorder.py`

使用 `sounddevice` 库创建音频输入流：

**音频参数**:
- **采样率**: 16000 Hz
- **声道数**: 1 (单声道)
- **格式**: PCM 16位 (`np.int16`)
- **块大小**: 3200 帧/块（推荐配置，200ms）或 1024 帧/块（默认值，64ms）

**关键代码**:
```python
def start_recording(self) -> bool:
    self.stream = sd.InputStream(
        samplerate=self.rate,        # 16000 Hz
        channels=self.channels,      # 1 (单声道)
        dtype=np.int16,              # PCM 16位
        blocksize=self.chunk,        # 1024 帧
        device=self.device,
        callback=self._audio_callback  # 音频回调函数
    )
    self.stream.start()
    
    # 启动音频消费线程
    self.thread = threading.Thread(target=self._consume_audio, daemon=True)
    self.thread.start()
```

---

### 5. 音频采集（实时循环）

**位置**: `src/utils/audio_recorder.py`

`sounddevice` 库会定期调用 `_audio_callback` 函数：

**回调频率**: 
- 推荐配置（3200帧）: 约每 200ms 调用一次
- 默认配置（1024帧）: 约每 64ms 调用一次

**关键代码**:
```python
def _audio_callback(self, indata, frames, time, status):
    """音频回调函数 - 由 sounddevice 定期调用"""
    if self.running and not self.paused:
        audio_data = indata.tobytes()  # numpy数组转bytes
        audio_size = len(audio_data)
        self.audio_queue.put(audio_data)  # 放入队列
        self._chunk_count += 1
        self._total_bytes += audio_size
```

**数据格式**:
- `indata`: numpy 数组，形状为 `(chunk, 1)`，数据类型为 `int16`
- 转换为 bytes: 
  - 推荐配置（3200帧）: 每个块约 6400 字节（3200帧 × 2字节/样本）
  - 默认配置（1024帧）: 每个块约 2048 字节（1024帧 × 2字节/样本）

---

### 6. 音频消费线程

**位置**: `src/utils/audio_recorder.py`

独立的线程从队列中取出音频数据并处理：

**关键代码**:
```python
def _consume_audio(self):
    """消费音频数据 - 在独立线程中运行"""
    while self.running:
        try:
            data = self.audio_queue.get(timeout=0.1)
            if not self.paused:
                # 保存到缓冲区（用于完整录音）
                self.audio_buffer.extend(data)
                
                # 实时发送音频数据块（用于流式 ASR）
                if self.on_audio_chunk:
                    self.on_audio_chunk(data)  # 调用回调函数
        except queue.Empty:
            continue
```

**作用**:
- 从队列中取出音频块
- 保存到缓冲区（用于完整录音保存）
- 调用回调函数，实时发送给 ASR

---

### 6.5 VAD过滤器（可选）

**位置**: `src/utils/vad_filter.py`（如果启用VAD）

如果配置中启用了VAD（`audio.vad.enabled: true`），音频数据会在发送到VoiceService之前进行语音活动检测：

**处理流程**:
1. **帧拆分**: 将200ms块拆分为10个20ms块（WebRTC VAD要求）
2. **VAD检测**: 对每个20ms块进行语音活动检测
3. **过滤**: 只发送检测到语音的块，过滤静音和非语音音频
4. **状态响应**: 自动响应暂停/恢复/停止控制信号

**关键代码**:
```python
def __call__(self, audio_data: bytes):
    # 检查录音器状态（响应控制信号）
    if self.recorder.get_state() == RecordingState.PAUSED:
        return  # 暂停时不处理
    
    # 拆分200ms块为20ms块
    # VAD检测每个20ms块
    # 只发送检测到语音的块
    if is_speech:
        self.callback(audio_data)
```

**作用**:
- ✅ 过滤静音和非语音音频
- ✅ 减少发送到ASR的数据量（预计节约40-60%）
- ✅ 节约ASR成本
- ✅ 对顶层调用完全透明

**注意**: VAD默认关闭，需要显式配置启用。详见 [VAD集成规划方案](vad_integration_plan.md)

---

### 7. VoiceService 接收音频数据块

**位置**: `src/services/voice_service.py`

`_on_audio_chunk` 方法接收音频数据并发送给 ASR 提供者：

**关键代码**:
```python
def _on_audio_chunk(self, audio_data: bytes):
    """音频数据块回调"""
    # 如果录音器处于暂停状态，不发送音频数据
    if self.recorder and self.recorder.get_state() == RecordingState.PAUSED:
        return
    
    if self._streaming_active and self.asr_provider and self._loop:
        try:
            if not self._loop.is_closed():
                if self._loop.is_running():
                    # 事件循环正在运行，使用线程安全的方式
                    asyncio.run_coroutine_threadsafe(
                        self.asr_provider.send_audio_chunk(audio_data),
                        self._loop
                    )
                else:
                    self._loop.run_until_complete(
                        self.asr_provider.send_audio_chunk(audio_data)
                    )
        except Exception as e:
            logger.error(f"发送音频数据块失败: {str(e)}")
```

**关键点**:
- 检查录音状态（暂停时不发送）
- 使用 `asyncio.run_coroutine_threadsafe` 确保线程安全
- 将同步的音频回调转换为异步调用

---

### 8. ASR 提供者接收音频数据

**位置**: `src/providers/asr/volcano.py`

`send_audio_chunk` 方法将音频数据放入异步队列：

**关键代码**:
```python
async def send_audio_chunk(self, audio_data: bytes):
    """发送音频数据块"""
    if not self._streaming_active or not self._audio_queue:
        return
    
    try:
        await self._audio_queue.put(audio_data)
    except Exception as e:
        logger.error(f"音频数据入队失败: {e}")
```

**队列作用**:
- 解耦音频采集和 WebSocket 发送
- 允许发送任务以不同速率处理数据
- 缓冲音频数据，避免阻塞

---

### 9. 音频发送任务（WebSocket）

**位置**: `src/providers/asr/volcano.py`

异步任务从队列中取出音频数据并通过 WebSocket 发送：

**关键代码**:
```python
async def _audio_sender(self):
    """音频发送任务 - 异步运行"""
    last_audio = None
    
    while True:
        audio_data = await self._audio_queue.get()
        
        if not self._is_conn_available():
            break
        
        if audio_data is None:  # 结束标记
            # 发送最后一包
            if last_audio is not None:
                request = RequestBuilder.new_audio_only_request(
                    self.seq, last_audio, is_last=True
                )
                await self.conn.send_bytes(request)
            break
        
        # 发送上一包数据（延迟一包，确保最后一包能正确标记）
        if last_audio is not None:
            request = RequestBuilder.new_audio_only_request(
                self.seq, last_audio, is_last=False
            )
            await self.conn.send_bytes(request)
            self.seq += 1
        
        last_audio = audio_data
```

**协议格式**:
- 使用火山引擎自定义二进制协议
- 音频数据经过 GZIP 压缩
- 包含序列号和结束标记

---

### 10. 火山引擎 ASR 服务

**服务地址**: `wss://openspeech.bytedance.com/api/v3/sauc/bigmodel`

**处理流程**:
1. 接收 WebSocket 音频流
2. 实时进行语音识别
3. 返回识别结果（中间结果和最终结果）

**识别模式**:
- **流式识别**: 实时返回中间结果
- **非流式识别** (可选): 返回更准确的最终结果

---

### 11. ASR 接收任务

**位置**: `src/providers/asr/volcano.py`

异步任务接收 WebSocket 消息并解析识别结果：

**关键代码**:
```python
async def _audio_receiver(self):
    """音频接收任务 - 异步运行"""
    async for msg in self.conn:
        if msg.type == aiohttp.WSMsgType.BINARY:
            # 解析响应
            response = ResponseParser.parse_response(msg.data)
            
            if response.payload_msg:
                result = response.payload_msg.get('result', {})
                if isinstance(result, dict):
                    text = result.get('text', '')
                    if text:
                        # 处理识别结果
                        self._handle_recognition_result(result, response.is_last_package)
```

**响应格式**:
- 二进制消息，包含协议头和压缩的 JSON 数据
- 需要解压和解析 JSON
- 包含文本、时间信息、确定标记等

---

### 12. 识别结果处理

**位置**: `src/providers/asr/volcano.py`

`_handle_recognition_result` 方法处理识别结果：

**关键代码**:
```python
def _handle_recognition_result(self, result: dict, is_last_package: bool):
    """处理识别结果"""
    text = result.get('text', '')
    if not text:
        return
    
    # 检测是否为确定的utterance
    is_definite_utterance, time_info = self._detect_definite_utterance(result, text)
    
    self._last_text = text
    self._current_text = text
    
    # 调用回调函数
    if self._on_text_callback:
        self._on_text_callback(text, is_definite_utterance, time_info)
```

**结果类型**:
- **中间结果** (`is_definite_utterance=False`): 实时更新的文本
- **确定结果** (`is_definite_utterance=True`): 完整的、确定的语音识别单元

---

### 13. VoiceService 接收识别结果

**位置**: `src/services/voice_service.py`

`_on_asr_text_received` 方法接收识别结果并调用回调：

**关键代码**:
```python
def _on_asr_text_received(self, text: str, is_definite_utterance: bool, time_info: dict):
    """ASR文本接收回调"""
    if is_definite_utterance:
        logger.info(f"收到确定utterance: '{text}'")
    
    self._current_text = text
    
    # 调用上层回调
    if self._on_text_callback:
        self._on_text_callback(text, is_definite_utterance, time_info)
```

---

### 14. API 服务器广播

**位置**: `src/api/server.py`

在 `setup_voice_service()` 中设置的回调函数：

**关键代码**:
```python
def on_text_callback(text: str, is_definite: bool, time_info: dict):
    """文本回调函数"""
    message = {
        "type": "text_final" if is_definite else "text_update",
        "text": text
    }
    if is_definite and time_info:
        message["start_time"] = time_info.get('start_time', 0)
        message["end_time"] = time_info.get('end_time', 0)
    
    # 广播给所有 WebSocket 连接
    broadcast(message)

voice_service.set_on_text_callback(on_text_callback)
```

**消息类型**:
- `text_update`: 中间识别结果（实时更新）
- `text_final`: 确定的完整utterance（包含时间信息）

---

### 15. 前端接收并显示

**位置**: `electron-app/src/App.tsx`

前端通过 WebSocket 接收消息并更新 UI：

**关键代码**:
```typescript
wsRef.current.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch (data.type) {
    case 'text_update':
      // 更新中间结果
      setCurrentText(data.text);
      break;
    
    case 'text_final':
      // 处理确定的utterance
      setCurrentText(data.text);
      // 保存时间信息等
      break;
    
    case 'state_change':
      setAsrState(data.state);
      break;
  }
};
```

---

## 关键技术点

### 1. 音频格式规范

| 参数 | 值 | 说明 |
|------|-----|------|
| 采样率 | 16000 Hz | 标准语音识别采样率 |
| 声道数 | 1 | 单声道 |
| 位深度 | 16位 | PCM格式 |
| 块大小 | 3200帧（推荐） | 约200ms的音频数据 |
| 块大小 | 1024帧（默认） | 约64ms的音频数据 |

### 2. 流式处理架构

```
音频采集 (同步回调)
    ↓
队列缓冲 (解耦)
    ↓
消费线程 (同步处理)
    ↓
[VAD过滤器] (可选，过滤静音)
    ↓
回调函数 (同步→异步转换)
    ↓
异步队列 (解耦)
    ↓
WebSocket发送 (异步)
```

### 3. 异步并发设计

- **发送任务** (`_audio_sender`): 独立异步任务，负责发送音频数据
- **接收任务** (`_audio_receiver`): 独立异步任务，负责接收识别结果
- **完全并发**: 发送和接收互不阻塞

### 4. 线程安全处理

- 音频回调在系统线程中运行（同步）
- 使用 `asyncio.run_coroutine_threadsafe` 转换为异步调用
- 确保事件循环安全

### 5. 状态管理

**录音状态流转**:
```
idle → recording → stopping → idle
         ↑    ↓
         └─ paused
```

**状态检查点**:
- 暂停时不发送音频数据
- 停止时发送结束标记
- 状态变化通过 WebSocket 同步

---

## 数据流图

```
┌─────────────────────────────────────────────────────────────────┐
│  前端 (Electron)                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  App.tsx                                                  │  │
│  │  POST /api/recording/start                                │  │
│  └────────────────────┬─────────────────────────────────────┘  │
└───────────────────────┼─────────────────────────────────────────┘
                        │ HTTP
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│  后端 API (FastAPI)                                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  server.py                                                │  │
│  │  voice_service.start_recording()                         │  │
│  └────────────────────┬─────────────────────────────────────┘  │
└───────────────────────┼─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│  VoiceService                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  1. 启动 ASR 流式识别 (WebSocket连接)                     │  │
│  │  2. 设置音频回调                                           │  │
│  │  3. 启动录音器                                             │  │
│  └────────────────────┬─────────────────────────────────────┘  │
└───────────────────────┼─────────────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
        ▼                               ▼
┌───────────────────┐         ┌───────────────────┐
│  音频录制器        │         │  ASR 提供者       │
│  (SoundDevice)    │         │  (Volcano)        │
│                   │         │                   │
│  sounddevice      │         │  WebSocket连接    │
│  InputStream      │         │  发送/接收任务    │
└─────────┬─────────┘         └─────────┬─────────┘
          │                             │
          │ 音频回调                     │ WebSocket
          │ (每200ms推荐)                 │
          ▼                             ▼
┌───────────────────┐         ┌───────────────────┐
│  音频消费线程      │         │  火山引擎 ASR      │
│  _consume_audio() │         │  服务              │
│                   │         │                   │
│  队列 → 回调      │         │  实时识别          │
└─────────┬─────────┘         └─────────┬─────────┘
          │                             │
          │ 音频数据块                   │ 识别结果
          │ (200ms块)                    │
          ▼                             │
┌───────────────────┐                  │
│  VAD过滤器(可选)   │                  │
│  - 拆分20ms块      │                  │
│  - 语音检测        │                  │
│  - 过滤静音        │                  │
└─────────┬─────────┘                  │
          │                             │
          │ 过滤后的音频                 │
          └───────────────┬─────────────┘
                          │
                          ▼
                ┌───────────────────┐
                │  VoiceService      │
                │  _on_audio_chunk() │
                │  _on_asr_text_    │
                │    received()      │
                └─────────┬─────────┘
                          │
                          ▼
                ┌───────────────────┐
                │  API 服务器       │
                │  broadcast()      │
                └─────────┬─────────┘
                          │ WebSocket
                          ▼
                ┌───────────────────┐
                │  前端显示          │
                │  更新 UI           │
                └───────────────────┘
```

---

## 代码位置

### 核心文件

| 文件路径 | 说明 |
|---------|------|
| `src/utils/audio_recorder.py` | 音频录制器实现（sounddevice） |
| `src/services/voice_service.py` | 语音服务主类（整合录音和ASR） |
| `src/providers/asr/volcano.py` | 火山引擎 ASR 提供者 |
| `src/api/server.py` | FastAPI 服务器和 WebSocket 处理 |
| `electron-app/src/App.tsx` | 前端主应用 |

### 关键方法

| 方法 | 文件 | 说明 |
|------|------|------|
| `start_recording()` | `voice_service.py` | 启动录音和ASR |
| `_audio_callback()` | `audio_recorder.py` | 音频采集回调 |
| `_consume_audio()` | `audio_recorder.py` | 音频消费线程 |
| `_on_audio_chunk()` | `voice_service.py` | 音频数据块处理 |
| `send_audio_chunk()` | `volcano.py` | 发送音频到ASR |
| `_audio_sender()` | `volcano.py` | WebSocket发送任务 |
| `_audio_receiver()` | `volcano.py` | WebSocket接收任务 |
| `_handle_recognition_result()` | `volcano.py` | 识别结果处理 |

---

## 故障排查

### 常见问题

#### 1. 音频设备无法打开

**症状**: 启动录音时提示"音频设备打开失败"

**可能原因**:
- 音频设备被其他程序占用
- 设备不支持单声道录音
- 设备ID配置错误

**解决方法**:
- 检查音频设备设置
- 尝试更换音频输入设备
- 检查系统音频权限

#### 2. WebSocket 连接失败

**症状**: ASR 无法启动，提示"连接失败"

**可能原因**:
- 网络连接问题
- ASR 配置错误（access_key/app_key）
- 认证失败

**解决方法**:
- 检查 `config.yml` 中的 ASR 配置
- 验证 access_key 和 app_key 是否正确
- 检查网络连接

#### 3. 音频数据未发送

**症状**: 录音正常，但没有识别结果

**可能原因**:
- 音频回调未设置
- 队列阻塞
- WebSocket 连接断开

**解决方法**:
- 检查日志中的音频回调设置
- 检查 WebSocket 连接状态
- 查看是否有错误日志

#### 4. 识别结果延迟

**症状**: 识别结果返回较慢

**可能原因**:
- 网络延迟
- 队列积压
- ASR 服务负载高

**解决方法**:
- 检查网络连接质量
- 查看队列大小
- 检查 ASR 服务状态

### 调试技巧

1. **启用详细日志**
   - 查看 `config.yml` 中的日志级别设置
   - 关注 `[音频]`、`[ASR-WS]`、`[语音服务]` 标签的日志

2. **检查音频数据流**
   - 查看音频回调是否被调用
   - 检查音频队列是否正常
   - 验证音频数据大小

3. **监控 WebSocket 连接**
   - 检查连接状态
   - 查看发送/接收的消息
   - 验证协议格式

4. **性能分析**
   - 测量音频采集延迟
   - 检查队列积压情况
   - 分析网络传输时间

---

## 总结

音频到ASR的流程是一个复杂的实时流式处理系统，涉及：

- **多线程处理**: 音频采集线程、消费线程
- **异步并发**: WebSocket 发送/接收任务
- **队列缓冲**: 解耦不同处理阶段
- **状态管理**: 录音状态、连接状态
- **错误处理**: 各环节的错误处理和恢复

整个流程设计保证了：
- ✅ 实时性：音频采集后立即处理
- ✅ 可靠性：错误处理和状态同步
- ✅ 可扩展性：插件化架构，易于替换ASR提供者
- ✅ 性能：异步并发，不阻塞主流程

---

**文档版本**: 1.0  
**最后更新**: 2026-01-01  
**维护者**: MindVoice 开发团队

