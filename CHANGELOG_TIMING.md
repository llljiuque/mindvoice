# 时间信息功能更新日志

## 版本：v1.0.1 (2026-01-02)

### 修复问题

#### 音频缓冲区内存泄漏修复

修复了长时间录音导致的内存持续累积和延迟增加问题。

**问题描述**：
- 长时间录音（如1小时演讲）会导致延迟越来越长（可达数十秒）
- 内存占用持续增长（可达100-200MB）
- 处理性能逐渐下降

**根本原因**：
- 音频缓冲区 `audio_buffer` 持续累积数据，从不清理
- 33分钟录音累积到123MB，1小时可达200-300MB

**解决方案**：
1. 添加 `max_buffer_seconds` 配置参数（默认60秒）
2. 自动清理超过限制的旧数据（保留50%）
3. 不影响实时ASR识别功能

### 变更详情

#### 1. 音频录音器增强 (`audio_recorder.py`)

**新增参数**：
```python
def __init__(self, ..., max_buffer_seconds: int = 60):
    # 计算最大缓冲区大小
    self.max_buffer_size = rate * channels * 2 * max_buffer_seconds
    self._buffer_cleanups = 0  # 清理次数统计
```

**缓冲区管理逻辑**：
```python
def _consume_audio(self):
    # 检查缓冲区大小
    if buffer_size > self.max_buffer_size:
        # 保留最新的一半，删除旧的一半
        keep_size = self.max_buffer_size // 2
        self.audio_buffer = self.audio_buffer[remove_size:]
        logger.info(f"缓冲区清理: 删除了 {remove_size}MB 旧数据")
```

#### 2. 配置文件更新

**config.yml 新增**：
```yaml
audio:
  max_buffer_seconds: 60  # 最大缓冲时长（秒）
```

**说明**：
- 16kHz单声道：60秒约1.92MB，120秒约3.84MB
- 建议值：60秒（语音识别）- 120秒（高质量）

#### 3. 服务器初始化更新 (`server.py`)

```python
recorder = SoundDeviceRecorder(
    rate=config.get('audio.rate', 16000),
    channels=config.get('audio.channels', 1),
    chunk=config.get('audio.chunk', 1024),
    device=audio_device,
    vad_config=vad_config,
    max_buffer_seconds=config.get('audio.max_buffer_seconds', 60)  # 新增
)
```

### 性能改进

**修复前**：
- 1小时录音：缓冲区115MB，延迟数十秒
- 内存持续增长，性能下降

**修复后**：
- 1小时录音：缓冲区稳定在1.92MB，延迟稳定
- 定期清理（约60次），性能恒定

### 影响范围

- ✅ 不影响实时ASR识别
- ✅ 不影响VAD过滤功能  
- ✅ 向后兼容（默认值60秒）
- ⚠️ 无法保存完整录音（如需要，请另外实现）

### 相关文档

- [缓冲区内存修复文档](docs/buffer_memory_fix.md)
- [验证步骤](docs/buffer_fix_verification.md)
- [测试脚本](test_buffer.py)

---

## 版本：v1.1.0 (2025-12-31)

### 新增功能

#### ASR 时间信息增强

为 `text_final` WebSocket 消息添加了开始时间和结束时间信息，方便前端显示语音识别的时间范围。

### 变更详情

#### 1. WebSocket 消息格式变更

**text_final 消息**（新增字段）
```json
{
  "type": "text_final",
  "text": "这十年过来。",
  "start_time": 0,      // 新增：开始时间（毫秒）
  "end_time": 4440      // 新增：结束时间（毫秒）
}
```

**text_update 消息**（格式不变）
```json
{
  "type": "text_update",
  "text": "这十年过来"
}
```

#### 2. 回调函数签名变更

**ASR Provider (`volcano.py`)**
```python
# 旧签名
set_on_text_callback(callback: Callable[[str, bool], None])

# 新签名
set_on_text_callback(callback: Callable[[str, bool, dict], None])
# 新增参数: time_info: dict - 包含 start_time 和 end_time
```

**Voice Service (`voice_service.py`)**
```python
# 旧签名
_on_asr_text_received(text: str, is_definite_utterance: bool)

# 新签名
_on_asr_text_received(text: str, is_definite_utterance: bool, time_info: dict)
```

#### 3. 内部方法变更

**`_detect_definite_utterance()` 返回值变更**
```python
# 旧返回值
return bool  # True 或 False

# 新返回值
return tuple[bool, dict]  # (是否确定, 时间信息字典)
```

### 使用示例

#### 前端 TypeScript 示例

```typescript
interface TextFinalMessage {
  type: 'text_final';
  text: string;
  start_time: number;  // 毫秒
  end_time: number;    // 毫秒
}

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'text_final') {
    const msg = data as TextFinalMessage;
    const duration = (msg.end_time - msg.start_time) / 1000;
    
    console.log(`[${msg.start_time/1000}s - ${msg.end_time/1000}s] ${msg.text}`);
    console.log(`Duration: ${duration.toFixed(2)}s`);
  }
};
```

#### Python 回调示例

```python
def on_text_callback(text: str, is_definite: bool, time_info: dict):
    if is_definite:
        start = time_info.get('start_time', 0)
        end = time_info.get('end_time', 0)
        duration = (end - start) / 1000
        print(f"[{start/1000:.2f}s - {end/1000:.2f}s] {text} (duration: {duration:.2f}s)")
    else:
        print(f"[中间结果] {text}")

voice_service.set_on_text_callback(on_text_callback)
```

### 兼容性说明

#### 破坏性变更 ⚠️

1. **回调函数签名变更**: 所有使用 `set_on_text_callback` 的代码需要更新
2. **内部方法返回值变更**: `_detect_definite_utterance()` 返回值从 `bool` 改为 `tuple[bool, dict]`

#### 向前兼容 ✅

1. **WebSocket 消息**: 前端可以选择忽略新增的 `start_time` 和 `end_time` 字段
2. **时间信息可选**: 如果 ASR 服务不返回时间信息，字段值为 0

### 迁移指南

#### 更新 API Server 回调

**旧代码**:
```python
voice_service.set_on_text_callback(
    lambda text, is_definite: broadcast({
        "type": "text_final" if is_definite else "text_update",
        "text": text
    })
)
```

**新代码**:
```python
def on_text_callback(text: str, is_definite: bool, time_info: dict):
    message = {
        "type": "text_final" if is_definite else "text_update",
        "text": text
    }
    if is_definite and time_info:
        message["start_time"] = time_info.get('start_time', 0)
        message["end_time"] = time_info.get('end_time', 0)
    broadcast(message)

voice_service.set_on_text_callback(on_text_callback)
```

#### 更新前端代码

**可选更新**（前端可以继续使用旧代码，忽略时间字段）:

```typescript
// 旧代码（仍然有效）
if (data.type === 'text_final') {
  displayText(data.text);
}

// 新代码（利用时间信息）
if (data.type === 'text_final') {
  displayTextWithTimestamp(
    data.text, 
    data.start_time, 
    data.end_time
  );
}
```

### 测试要点

1. ✅ 验证 `text_final` 消息包含 `start_time` 和 `end_time` 字段
2. ✅ 验证 `text_update` 消息不包含时间字段
3. ✅ 验证时间值合理性：
   - `end_time > start_time`
   - 时间值为非负数
   - 持续时间在合理范围内（通常几秒）
4. ✅ 验证日志输出包含时间信息

### 相关文档

- [ASR 时间信息文档](docs/ASR_TIMING_INFO.md) - 详细技术文档
- [架构文档](docs/ARCHITECTURE.md) - 系统架构说明
- [状态管理文档](docs/STATES.md) - 状态转换说明

### 修改的文件

- `src/providers/asr/volcano.py` - ASR Provider 实现
- `src/services/voice_service.py` - Voice Service 实现
- `src/api/server.py` - API Server 实现
- `docs/ASR_TIMING_INFO.md` - 新增文档

### 待办事项

- [ ] 更新前端代码以显示时间信息
- [ ] 添加单元测试验证时间信息提取
- [ ] 更新 API 文档
- [ ] 发布新版本

---

**更新日期**: 2025-12-31
**影响范围**: ASR Provider, Voice Service, API Server
**破坏性变更**: 是（回调函数签名变更）

