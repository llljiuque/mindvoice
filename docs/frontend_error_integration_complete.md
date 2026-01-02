# 前端错误展示集成完成

**完成日期：** 2026-01-02  
**状态：** ✅ 已完成

---

## 完成的工作

### 1. 前端集成 (App.tsx)

#### 导入组件
```typescript
import { ErrorBanner, ErrorToast } from './components/shared/SystemErrorDisplay';
import { SystemErrorInfo, ErrorCodes } from './utils/errorCodes';
```

#### 状态管理
添加了新的 state：
```typescript
const [systemError, setSystemError] = useState<SystemErrorInfo | null>(null);
```

#### 错误处理更新

**API连接检查：**
- 网络不可达错误 (ErrorCodes.NETWORK_UNREACHABLE)
- API服务器不可用 (ErrorCodes.API_SERVER_UNAVAILABLE)

**WebSocket连接：**
- 支持后端传递的 SystemErrorInfo 对象
- WebSocket连接失败 (ErrorCodes.WEBSOCKET_CONNECTION_FAILED)
- WebSocket连接断开 (ErrorCodes.WEBSOCKET_DISCONNECTED)
- 消息解析失败处理

**ASR API调用：**
- 音频设备错误智能分类 (2000-2099)
- 网络超时处理 (ErrorCodes.NETWORK_TIMEOUT)
- 支持后端返回的完整 SystemErrorInfo

#### UI展示

**ErrorBanner（页面顶部横幅）：**
```tsx
{systemError && (
  <ErrorBanner
    error={systemError}
    onClose={() => setSystemError(null)}
  />
)}
```

**ErrorToast（音频设备错误专用）：**
```tsx
{systemError && systemError.code >= 2000 && systemError.code < 3000 && (
  <ErrorToast
    error={systemError}
    duration={5000}
    onClose={() => setSystemError(null)}
  />
)}
```

### 2. 后端集成 (server.py)

#### 导入错误系统
```python
from src.core.logger import get_logger
from src.core.error_codes import SystemError, SystemErrorInfo

logger = get_logger("API")
```

#### API响应模型更新
```python
class StartRecordingResponse(BaseModel):
    success: bool
    message: str
    error: Optional[Dict[str, Any]] = None  # SystemErrorInfo 对象
```

#### 错误处理增强
在 `start_recording` 端点中：
- 音频设备格式不支持 (AUDIO_DEVICE_FORMAT_NOT_SUPPORTED)
- 音频设备打开失败 (AUDIO_DEVICE_OPEN_FAILED)
- 音频设备权限拒绝 (AUDIO_DEVICE_PERMISSION_DENIED)
- 音频流错误 (AUDIO_STREAM_ERROR)

返回完整的 SystemErrorInfo：
```python
return StartRecordingResponse(
    success=False,
    message=error_info.user_message,
    error=error_info.to_dict()
)
```

---

## 错误展示策略

### ErrorBanner（横幅）- 重要但不阻塞
用于显示：
- 网络连接问题
- WebSocket断开（自动重连）
- ASR/LLM服务问题

**特点：**
- 显示在页面顶部
- 有关闭按钮
- 不阻塞用户操作

### ErrorToast（Toast提示）- 临时提示
用于显示：
- 音频设备错误 (2000-2099)
- 不需要用户立即处理的错误

**特点：**
- 右下角浮动
- 5秒后自动消失
- 可手动关闭
- 不阻塞操作

### 旧的 error 横幅 - 兼容保留
保留了原有的简单错误横幅，用于不需要详细错误信息的场景。

---

## 错误流程示例

### 场景1：音频设备被占用

1. **后端检测：**
```python
error_info = SystemErrorInfo(
    SystemError.AUDIO_DEVICE_BUSY,
    details="音频设备被占用",
    technical_info="PortAudioError: Device busy"
)
```

2. **API返回：**
```json
{
  "success": false,
  "message": "麦克风正被其他程序使用，请关闭其他音频应用",
  "error": {
    "code": 2001,
    "category": "AUDIO_DEVICE",
    "user_message": "麦克风正被其他程序使用...",
    "suggestion": "1. 关闭其他使用麦克风的应用..."
  }
}
```

3. **前端展示：**
   - 显示 ErrorToast（右下角）
   - 5秒后自动消失
   - 不阻塞用户其他操作

### 场景2：WebSocket断开

1. **前端检测：** `ws.onclose` 触发

2. **创建错误：**
```typescript
setSystemError({
  code: ErrorCodes.WEBSOCKET_DISCONNECTED,
  category: 'NETWORK',
  message: 'WebSocket连接断开',
  user_message: '连接已断开，正在尝试重连...',
  suggestion: '系统会自动重连，请稍候'
});
```

3. **前端展示：**
   - 显示 ErrorBanner（页面顶部）
   - 提示"正在重连"
   - 3秒后自动重连
   - 重连成功后自动清除错误

### 场景3：ASR认证失败

1. **后端检测：** ASR provider 初始化失败

2. **系统日志记录：**
```python
error_info = SystemErrorInfo(
    SystemError.ASR_AUTH_FAILED,
    details="认证失败",
    technical_info="HTTP 403: Invalid credentials"
)
sys_logger.log_error("ASR", error_info)
```

3. **通过WebSocket广播：**
```json
{
  "type": "error",
  "error": {
    "code": 3000,
    "category": "ASR_SERVICE",
    "user_message": "语音识别服务认证失败，请检查配置",
    "suggestion": "1. 检查config.yml中的access_key..."
  }
}
```

4. **前端展示：**
   - 显示 ErrorBanner
   - 显示完整的解决建议
   - 用户可点击关闭

---

## 测试建议

### 1. 测试音频设备错误
```bash
# 方法1：在其他应用中占用麦克风（如录音软件）
# 然后在 MindVoice 中点击开始录音

# 预期：显示 ErrorToast，提示"麦克风正被其他程序使用"
```

### 2. 测试网络错误
```bash
# 关闭后端服务器
./stop.sh

# 在前端刷新页面或点击操作
# 预期：显示 ErrorBanner，提示"无法连接到API服务器"
```

### 3. 测试WebSocket断开
```bash
# 启动应用后，在终端中强制结束 Python 进程
killall python

# 预期：
# 1. 显示 ErrorBanner "连接已断开，正在尝试重连..."
# 2. 3秒后自动尝试重连
```

### 4. 测试ASR错误
```bash
# 在 config.yml 中修改 access_key 为错误的值
# 重启后端服务并尝试开始录音

# 预期：显示 ErrorBanner，提示"语音识别服务认证失败"
```

---

## 兼容性说明

### 向后兼容
- 保留了旧的 `error` state 和简单错误横幅
- 旧的 Toast 组件仍然可用
- 不影响现有功能

### 渐进增强
- 后端可以逐步迁移到返回 SystemErrorInfo
- 前端同时支持新旧两种错误格式
- WebSocket消息支持带或不带 error 对象

---

## 后续优化建议

### 短期
- [ ] 在更多API端点中返回 SystemErrorInfo
- [ ] 在 WebSocket 错误回调中传递完整的错误对象
- [ ] 添加错误重试机制（带指数退避）

### 中期
- [ ] 实现错误统计和上报
- [ ] 添加用户反馈按钮（报告错误）
- [ ] 错误恢复自动化（如自动切换音频设备）

### 长期
- [ ] 错误预测和预防
- [ ] 智能错误诊断助手
- [ ] 集成远程监控服务

---

## 文件清单

### 前端
- ✅ `electron-app/src/App.tsx` - 集成错误展示组件
- ✅ `electron-app/src/utils/errorCodes.ts` - 错误码定义
- ✅ `electron-app/src/components/shared/SystemErrorDisplay.tsx` - 错误展示组件
- ✅ `electron-app/src/components/shared/SystemErrorDisplay.css` - 组件样式

### 后端
- ✅ `src/api/server.py` - 更新API返回 SystemErrorInfo
- ✅ `src/core/error_codes.py` - 错误码定义
- ✅ `src/core/logger.py` - 日志系统
- ✅ `src/services/llm_service.py` - LLM错误处理
- ✅ `src/services/voice_service.py` - 语音服务（已有日志）
- ✅ `src/providers/asr/volcano.py` - ASR错误处理
- ✅ `src/utils/audio_recorder.py` - 音频设备错误处理

---

**集成完成！** 🎉

系统现在具备了：
- ✅ 统一的错误码体系
- ✅ 智能错误分类
- ✅ 用户友好的错误提示
- ✅ 完整的错误追踪链路
- ✅ 优雅的错误展示UI

**开发者：** 深圳王哥 & AI  
**完成日期：** 2026-01-02

