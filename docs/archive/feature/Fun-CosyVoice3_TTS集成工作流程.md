# Fun-CosyVoice3 TTS 集成工作流程

## 概述

本文档详细说明如何在 MindVoice 项目中集成 **Fun-CosyVoice3-0.5B-2512** TTS 模型，实现语音合成功能。项目采用插件化架构，TTS 功能将遵循与 ASR、LLM 相同的设计模式。

## 一、环境准备

### 1.1 Python 环境要求

- **Python 版本**: >= 3.10（Fun-CosyVoice3 要求）
- **虚拟环境**: 使用已创建的 `my_env3.10` conda 环境

### 1.2 依赖安装

在 `requirements.txt` 中添加以下依赖：

```txt
# TTS 相关依赖
modelscope>=1.9.0          # ModelScope SDK，用于模型下载和管理
funasr>=1.0.0              # FunASR 框架，Fun-CosyVoice3 依赖
soundfile>=0.12.0          # 音频文件处理
scipy>=1.10.0              # 音频处理（重采样、信号处理）
numpy>=1.24.0               # 数值计算（已存在，确保版本兼容）
```

**安装命令**：
```powershell
conda activate my_env3.10
cd d:\work\mindvoice\mindvoice
pip install modelscope funasr soundfile scipy
```

### 1.3 模型下载

Fun-CosyVoice3 模型将通过 ModelScope 自动下载，首次使用时会在 `~/.cache/modelscope` 目录下载模型文件（约 2-3GB）。

**模型信息**：
- **模型ID**: `FunAudioLLM/Fun-CosyVoice3-0.5B-2512`
- **模型大小**: 约 2-3GB
- **支持语言**: 中文、英文、日语、韩语等 9 种语言
- **特性**: 流式合成、零样本音色克隆、低延迟

## 二、代码结构设计

### 2.1 目录结构

按照项目现有的插件化架构，TTS 功能将创建以下文件结构：

```
src/
├── core/
│   └── base.py                    # 添加 TTSProvider 抽象基类
├── providers/
│   └── tts/                       # 新建 TTS 提供商目录
│       ├── __init__.py            # 模块初始化
│       ├── base_tts.py            # TTS 提供商基类
│       └── cosyvoice3.py          # Fun-CosyVoice3 实现
├── services/
│   └── tts_service.py             # TTS 业务服务层（新建）
└── api/
    ├── server.py                   # 添加 TTS API 端点
    └── tts_api.py                 # TTS API 路由（新建，可选）
```

### 2.2 架构层次

```
┌─────────────────────────────────────┐
│   FastAPI API 层                    │
│   /api/tts/synthesize               │
│   /api/tts/voices                   │
│   /api/tts/stream                   │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   TTS Service 层                    │
│   - 文本预处理                       │
│   - 参数验证                         │
│   - 错误处理                         │
│   - 音频格式转换                     │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   TTS Provider 层                   │
│   CosyVoice3Provider                │
│   - 模型加载                         │
│   - 语音合成                         │
│   - 流式输出                         │
└──────────────────────────────────────┘
```

## 三、实施步骤

### 3.1 步骤 1: 定义 TTSProvider 抽象基类

**文件**: `src/core/base.py`

在文件末尾添加 `TTSProvider` 抽象基类，参考 `ASRProvider` 和 `LLMProvider` 的设计模式：

**需要定义的方法**：
- `name` (property): 提供商名称
- `supported_languages` (property): 支持的语言列表
- `initialize(config)`: 初始化提供商
- `synthesize(text, language, voice, speed, **kwargs)`: 合成语音（异步，返回 bytes）
- `synthesize_stream(text, language, voice, speed, **kwargs)`: 流式合成（异步生成器）
- `list_voices(language)`: 列出可用音色（异步）
- `is_available()`: 检查服务是否可用

### 3.2 步骤 2: 创建 TTS Provider 基类

**文件**: `src/providers/tts/base_tts.py`

创建 `BaseTTSProvider` 类，继承 `TTSProvider`，提供通用功能：
- 配置管理
- 初始化状态跟踪
- 基础错误处理

### 3.3 步骤 3: 实现 CosyVoice3Provider

**文件**: `src/providers/tts/cosyvoice3.py`

**核心功能实现**：

1. **模型初始化**：
   - 使用 `modelscope.snapshot_download()` 下载模型（如果本地不存在）
   - 使用 `funasr.AutoModel` 加载模型
   - 支持 CPU/CUDA 设备选择
   - 配置模型缓存目录

2. **语音合成** (`synthesize` 方法)：
   - 接收文本、语言、音色、语速等参数
   - 调用模型的 `generate()` 方法
   - 支持零样本音色克隆（通过 `ref_audio` 参数）
   - 将音频数组转换为 WAV 格式字节流
   - 返回音频数据（bytes）

3. **流式合成** (`synthesize_stream` 方法)：
   - 将文本分块处理（建议 50-100 字符/块）
   - 逐块生成音频
   - 使用异步生成器逐步返回音频数据

4. **音色列表** (`list_voices` 方法)：
   - 返回默认音色信息
   - 支持按语言过滤
   - 为未来扩展预留接口（零样本克隆音色管理）

5. **音频格式转换**：
   - 使用 `soundfile` 将 numpy 数组转换为 WAV 字节流
   - 确保采样率为 24000 Hz（Fun-CosyVoice3 默认）
   - 支持单声道输出
   - 使用 PCM_16 格式

**关键代码结构**（伪代码）：

```python
class CosyVoice3Provider(BaseTTSProvider):
    def __init__(self):
        self.model = None
        self.model_dir = None
    
    def initialize(self, config):
        # 1. 下载模型（如果需要）
        # 2. 加载模型
        # 3. 设置默认参数
        pass
    
    async def synthesize(self, text, language, voice, speed, **kwargs):
        # 1. 参数验证
        # 2. 调用模型生成
        # 3. 格式转换
        # 4. 返回音频字节流
        pass
    
    async def synthesize_stream(self, text, language, voice, speed, **kwargs):
        # 1. 文本分块
        # 2. 逐块生成
        # 3. yield 音频数据
        pass
```

### 3.4 步骤 4: 创建 TTS Service 层

**文件**: `src/services/tts_service.py`

**功能职责**：
- 封装 TTS Provider，提供业务逻辑层
- 文本预处理（清理、分段）
- 参数验证和默认值设置
- 错误处理和日志记录
- 音频格式统一（确保返回标准 WAV 格式）

**类设计**：

```python
class TTSService:
    def __init__(self, config: Config):
        self.config = config
        self.tts_provider = None
        self._initialize_provider()
    
    def _initialize_provider(self):
        # 从配置读取 TTS 设置
        # 创建并初始化 CosyVoice3Provider
        pass
    
    async def synthesize(self, text, language, voice, speed):
        # 调用 provider.synthesize()
        # 添加业务逻辑（如文本清理）
        pass
    
    async def synthesize_stream(self, text, language, voice, speed):
        # 调用 provider.synthesize_stream()
        pass
    
    async def list_voices(self, language):
        # 调用 provider.list_voices()
        pass
    
    def is_available(self):
        # 检查服务是否可用
        pass
```

### 3.5 步骤 5: 添加 API 端点

**文件**: `src/api/server.py`

**需要添加的内容**：

1. **导入 TTS 服务**：
   ```python
   from src.services.tts_service import TTSService
   ```

2. **全局服务实例**：
   ```python
   tts_service: Optional[TTSService] = None
   ```

3. **初始化函数**：
   ```python
   def setup_tts_service():
       global tts_service
       tts_service = TTSService(config)
   ```

4. **在 lifespan 中调用**：
   ```python
   @asynccontextmanager
   async def lifespan(app: FastAPI):
       setup_logging()
       setup_voice_service()
       setup_llm_service()
       setup_tts_service()  # 新增
       # ... 其他初始化
   ```

5. **API 端点**：

   **端点 1: 语音合成**
   ```
   POST /api/tts/synthesize
   ```
   - **请求体**:
     ```json
     {
       "text": "要合成的文本",
       "language": "zh-CN",
       "voice": "default",
       "speed": 1.0
     }
     ```
   - **响应**: 返回 WAV 格式音频文件（`audio/wav`）

   **端点 2: 流式合成**
   ```
   POST /api/tts/stream
   ```
   - **请求体**: 同上
   - **响应**: `StreamingResponse`，逐步返回音频数据块

   **端点 3: 获取音色列表**
   ```
   GET /api/tts/voices?language=zh-CN
   ```
   - **响应**:
     ```json
     {
       "success": true,
       "voices": [
         {
           "id": "default",
           "name": "默认音色",
           "language": "zh-CN",
           "gender": "neutral"
         }
       ]
     }
     ```

**API 实现示例**（伪代码）：

```python
@app.post("/api/tts/synthesize")
async def synthesize_tts(request: TTSRequest):
    if not tts_service or not tts_service.is_available():
        raise HTTPException(503, "TTS service unavailable")
    
    audio_data = await tts_service.synthesize(
        text=request.text,
        language=request.language,
        voice=request.voice,
        speed=request.speed
    )
    
    return Response(
        content=audio_data,
        media_type="audio/wav",
        headers={"Content-Disposition": "attachment; filename=tts_output.wav"}
    )

@app.post("/api/tts/stream")
async def synthesize_tts_stream(request: TTSRequest):
    async def generate():
        async for chunk in tts_service.synthesize_stream(...):
            yield chunk
    
    return StreamingResponse(
        generate(),
        media_type="audio/wav"
    )
```

### 3.6 步骤 6: 更新配置文件

**文件**: `config.yml.example`

添加 TTS 配置节：

```yaml
# TTS 配置（Fun-CosyVoice3）
tts:
  provider: cosyvoice3              # TTS 提供商名称
  enabled: true                     # 是否启用 TTS 功能
  
  # Fun-CosyVoice3 特定配置
  cosyvoice3:
    model_id: "FunAudioLLM/Fun-CosyVoice3-0.5B-2512"  # ModelScope 模型ID
    model_dir: null                  # 本地模型路径（可选，null 表示自动下载）
    device: "cpu"                    # 设备：cpu 或 cuda
    cache_dir: "~/.cache/modelscope" # 模型缓存目录
    
    # 默认参数
    default_language: "zh-CN"        # 默认语言
    default_voice: "default"         # 默认音色
    default_speed: 1.0               # 默认语速
    
    # 流式合成配置
    stream:
      enabled: true                  # 是否启用流式合成
      chunk_size: 50                 # 文本分块大小（字符数）
```

### 3.7 步骤 7: 更新模块初始化

**文件**: `src/providers/tts/__init__.py`

```python
"""
TTS 提供商模块
"""
from .base_tts import BaseTTSProvider
from .cosyvoice3 import CosyVoice3Provider

__all__ = ['BaseTTSProvider', 'CosyVoice3Provider']
```

## 四、API 设计详细说明

### 4.1 请求/响应模型

**文件**: `src/api/server.py` 或新建 `src/api/tts_api.py`

**请求模型**：

```python
class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="要合成的文本")
    language: str = Field(default="zh-CN", description="语言代码")
    voice: Optional[str] = Field(default=None, description="音色ID")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="语速（0.5-2.0）")
    ref_audio: Optional[str] = Field(default=None, description="参考音频（Base64编码，用于音色克隆）")
```

**响应模型**：

```python
class TTSResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    audio_url: Optional[str] = None  # 如果返回文件URL
    duration_ms: Optional[int] = None  # 音频时长（毫秒）

class VoicesResponse(BaseModel):
    success: bool
    voices: list[Dict[str, Any]]
```

### 4.2 错误处理

- **503 Service Unavailable**: TTS 服务未初始化或不可用
- **400 Bad Request**: 请求参数无效（文本为空、语速超出范围等）
- **500 Internal Server Error**: 模型推理失败、音频生成错误

## 五、前端集成（Electron）

### 5.1 API 调用

在 Electron 前端中，当需要播放 TTS 音频时：

1. **调用合成 API**：
   ```typescript
   const response = await fetch('http://127.0.0.1:8765/api/tts/synthesize', {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({
       text: llmResponse,
       language: 'zh-CN',
       speed: 1.0
     })
   });
   
   const audioBlob = await response.blob();
   const audioUrl = URL.createObjectURL(audioBlob);
   ```

2. **播放音频**：
   ```typescript
   const audio = new Audio(audioUrl);
   audio.play();
   ```

### 5.2 流式播放（可选）

对于流式合成，可以使用 `MediaSource` API 或逐步拼接音频块。

## 六、测试验证

### 6.1 单元测试

**测试文件**: `tests/test_tts_provider.py`

**测试用例**：
1. 模型初始化测试
2. 基本合成测试（短文本）
3. 长文本合成测试
4. 流式合成测试
5. 多语言测试
6. 语速调整测试
7. 错误处理测试（无效参数、服务不可用）

### 6.2 集成测试

**测试场景**：
1. API 端点响应测试
2. 端到端流程测试（文本 → API → 音频 → 播放）
3. 并发请求测试
4. 性能测试（延迟、吞吐量）

### 6.3 手动测试步骤

1. **启动后端服务**：
   ```powershell
   conda activate my_env3.10
   cd d:\work\mindvoice\mindvoice
   python api_server.py
   ```

2. **测试 API**：
   ```powershell
   # 测试合成端点
   curl -X POST http://127.0.0.1:8765/api/tts/synthesize `
     -H "Content-Type: application/json" `
     -d '{"text":"你好，这是测试文本","language":"zh-CN"}' `
     --output test_output.wav
   
   # 测试音色列表
   curl http://127.0.0.1:8765/api/tts/voices
   ```

3. **验证音频文件**：
   - 使用音频播放器打开 `test_output.wav`
   - 检查音质、清晰度、自然度

## 七、性能优化建议

### 7.1 模型加载优化

- **延迟加载**: 首次使用时才加载模型，避免启动时阻塞
- **模型预热**: 启动后使用短文本进行一次合成，预热模型
- **模型缓存**: 确保模型文件缓存在本地，避免重复下载

### 7.2 推理优化

- **批处理**: 对于多个短文本，考虑批量合成（如果模型支持）
- **文本预处理**: 清理特殊字符，统一标点符号
- **缓存机制**: 对相同文本的合成结果进行缓存（可选）

### 7.3 资源管理

- **GPU 使用**: 如果有 CUDA，优先使用 GPU 加速
- **内存管理**: 长时间运行后检查内存泄漏
- **并发控制**: 限制同时进行的合成任务数量

## 八、故障排查

### 8.1 常见问题

1. **模型下载失败**：
   - 检查网络连接
   - 检查 ModelScope 镜像配置
   - 手动下载模型到指定目录

2. **内存不足**：
   - 使用 CPU 模式（`device: "cpu"`）
   - 减少并发请求
   - 增加系统内存

3. **音频格式错误**：
   - 检查 `soundfile` 版本
   - 验证采样率设置（24000 Hz）

4. **初始化失败**：
   - 检查 Python 版本（>= 3.10）
   - 验证依赖安装完整性
   - 查看日志文件获取详细错误信息

### 8.2 日志位置

- **API 日志**: `logs/api_server_*.log`
- **TTS 服务日志**: 在 API 日志中查找 `[TTS]` 前缀的日志

## 九、后续扩展

### 9.1 功能扩展

1. **音色管理**: 实现音色上传、存储、管理功能
2. **情感控制**: 支持情感参数（如果模型支持）
3. **SSML 支持**: 支持更丰富的文本标记语言
4. **多模型支持**: 支持切换不同的 TTS 模型

### 9.2 性能扩展

1. **模型量化**: 使用量化模型减少内存占用
2. **ONNX 转换**: 转换为 ONNX 格式提升推理速度
3. **边缘部署**: 支持在边缘设备上运行

## 十、实施时间估算

- **步骤 1-3（Provider 层）**: 2-3 小时
- **步骤 4（Service 层）**: 1 小时
- **步骤 5（API 层）**: 2 小时
- **步骤 6（配置）**: 0.5 小时
- **测试和调试**: 2-3 小时

**总计**: 约 8-10 小时

## 十一、参考资料

- **Fun-CosyVoice3 官方文档**: https://www.modelscope.cn/models/FunAudioLLM/Fun-CosyVoice3-0.5B-2512
- **ModelScope SDK**: https://modelscope.cn/docs
- **FunASR 文档**: https://github.com/alibaba-damo-academy/FunASR
- **项目架构文档**: `docs/design/SYSTEM_ARCHITECTURE.md`

---

**文档版本**: v1.0  
**创建日期**: 2026-01-13  
**适用模型**: Fun-CosyVoice3-0.5B-2512
