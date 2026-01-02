# SystemErrorInfo 扩展覆盖计划

## 📊 实施优先级

### 🔴 第一阶段：核心 API 端点（1-2天）

#### 1.1 录音控制 API
- [ ] `/api/recording/stop` - 停止录音错误
- [ ] `/api/recording/pause` - 暂停录音错误
- [ ] `/api/recording/resume` - 恢复录音错误

**预期错误类型：**
- AUDIO_STREAM_ERROR (2005) - 音频流错误
- SYSTEM_INTERNAL_ERROR (9000) - 内部错误

#### 1.2 历史记录 API
- [ ] `/api/text/save` - 保存失败
- [ ] `/api/records` - 加载列表失败
- [ ] `/api/records/{id}` - 加载单条失败
- [ ] `/api/records/delete` - 删除失败

**预期错误类型：**
- STORAGE_WRITE_FAILED (5001) - 写入失败
- STORAGE_READ_FAILED (5002) - 读取失败
- STORAGE_CONNECTION_FAILED (5000) - 连接失败
- STORAGE_DISK_FULL (5003) - 磁盘已满

#### 1.3 LLM API
- [ ] `/api/llm/chat` - 对话错误
- [ ] `/api/llm/simple-chat` - 简单对话错误
- [ ] `/api/summary/generate` - 生成摘要错误

**预期错误类型：**
- LLM_AUTH_FAILED (4000) - 认证失败
- LLM_QUOTA_EXCEEDED (4001) - 配额超限
- LLM_SERVICE_UNAVAILABLE (4002) - 服务不可用
- LLM_REQUEST_TIMEOUT (4003) - 请求超时
- LLM_RATE_LIMIT (4004) - 频率超限

---

### 🟡 第二阶段：WebSocket 和前端增强（2-3天）

#### 2.1 WebSocket 错误传递
- [ ] 更新 `on_error_callback` 传递 SystemErrorInfo
- [ ] 前端 WebSocket 消息处理完整的错误对象
- [ ] ASR 错误实时传递

#### 2.2 前端 App.tsx 增强
- [ ] `saveText()` - 使用 SystemErrorInfo
- [ ] `loadRecords()` - 使用 SystemErrorInfo
- [ ] `deleteRecords()` - 使用 SystemErrorInfo
- [ ] `loadRecord()` - 使用 SystemErrorInfo

#### 2.3 设置页面
- [ ] SettingsView.tsx - 音频设备错误
- [ ] 音频设备切换失败处理
- [ ] ASR配置重载失败处理

---

### 🟢 第三阶段：存储和配置层（1-2天）

#### 3.1 存储层错误
- [ ] SQLiteStorageProvider - 集成 SystemErrorInfo
- [ ] 数据库连接错误处理
- [ ] 磁盘空间检查

#### 3.2 配置层错误
- [ ] Config 类 - 配置加载错误
- [ ] 配置文件验证错误
- [ ] 配置解析错误

---

## 📝 实施示例

### 示例1：更新 `/api/text/save`

**当前代码：**
```python
@app.post("/api/text/save")
async def save_text(request: SaveTextRequest):
    try:
        # ... 保存逻辑 ...
    except Exception as e:
        logger.error(f"保存文本失败: {e}")
        return {"success": False, "message": str(e)}
```

**更新后：**
```python
@app.post("/api/text/save")
async def save_text(request: SaveTextRequest):
    try:
        # ... 保存逻辑 ...
    except IOError as e:
        # 磁盘空间或权限错误
        if "No space" in str(e) or "Disk full" in str(e):
            error_info = SystemErrorInfo(
                SystemError.STORAGE_DISK_FULL,
                details="磁盘空间不足",
                technical_info=str(e)
            )
        else:
            error_info = SystemErrorInfo(
                SystemError.STORAGE_WRITE_FAILED,
                details="写入失败",
                technical_info=str(e)
            )
        
        return {
            "success": False,
            "message": error_info.user_message,
            "error": error_info.to_dict()
        }
    except Exception as e:
        error_info = SystemErrorInfo(
            SystemError.SYSTEM_INTERNAL_ERROR,
            details="保存文本失败",
            technical_info=str(e)
        )
        return {
            "success": False,
            "message": error_info.user_message,
            "error": error_info.to_dict()
        }
```

### 示例2：更新前端 `saveText()`

**当前代码：**
```typescript
const saveText = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/text/save`, {...});
    const data = await response.json();
    if (data.success) {
      setText('');
      setToast({ message: '保存成功', type: 'success' });
    } else {
      setError(data.message || '保存失败');
    }
  } catch (e) {
    setToast({ message: '保存失败，请重试', type: 'error' });
  }
};
```

**更新后：**
```typescript
const saveText = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/text/save`, {...});
    const data = await response.json();
    if (data.success) {
      setText('');
      setToast({ message: '保存成功', type: 'success' });
    } else {
      // 使用 SystemErrorInfo
      if (data.error && data.error.code) {
        setSystemError(data.error);
      } else {
        setError(data.message || '保存失败');
      }
    }
  } catch (e) {
    setSystemError({
      code: ErrorCodes.NETWORK_TIMEOUT,
      category: 'NETWORK',
      message: '网络错误',
      user_message: '保存失败，请检查网络连接',
      suggestion: '请重试或检查网络状态',
      technical_info: String(e)
    });
  }
};
```

### 示例3：WebSocket 错误传递

**更新 voice_service.py：**
```python
# 错误回调改为传递完整的 SystemErrorInfo
def set_on_error_callback(self, callback: Callable[[SystemErrorInfo], None]):
    self._on_error_callback = callback

# 调用时传递完整对象
if self._on_error_callback:
    error_info = SystemErrorInfo(
        SystemError.ASR_CONNECTION_BROKEN,
        details="ASR连接中断",
        technical_info="WebSocket closed unexpectedly"
    )
    self._on_error_callback(error_info)
```

**更新 server.py：**
```python
def on_error_callback(error_info: SystemErrorInfo):
    broadcast({
        "type": "error",
        "error": error_info.to_dict()  # 传递完整对象
    })

voice_service.set_on_error_callback(on_error_callback)
```

**前端已准备好接收：**
```typescript
// App.tsx 中已经支持
case 'error':
  if (data.error && typeof data.error === 'object' && data.error.code) {
    setSystemError(data.error);
  }
  break;
```

---

## 🔧 通用工具函数

为了简化实施，可以创建辅助函数：

### 后端辅助函数

```python
# src/core/error_helpers.py

from src.core.error_codes import SystemError, SystemErrorInfo
from typing import Dict, Any

def create_error_response(error_info: SystemErrorInfo) -> Dict[str, Any]:
    """创建标准错误响应"""
    return {
        "success": False,
        "message": error_info.user_message,
        "error": error_info.to_dict()
    }

def handle_storage_exception(e: Exception) -> SystemErrorInfo:
    """处理存储相关异常"""
    error_msg = str(e)
    
    if "disk full" in error_msg.lower() or "no space" in error_msg.lower():
        return SystemErrorInfo(
            SystemError.STORAGE_DISK_FULL,
            details="磁盘空间不足",
            technical_info=error_msg
        )
    elif "permission" in error_msg.lower():
        return SystemErrorInfo(
            SystemError.STORAGE_WRITE_FAILED,
            details="没有写入权限",
            technical_info=error_msg
        )
    else:
        return SystemErrorInfo(
            SystemError.STORAGE_CONNECTION_FAILED,
            details="存储操作失败",
            technical_info=error_msg
        )

def handle_llm_exception(e: Exception) -> SystemErrorInfo:
    """处理 LLM 相关异常"""
    error_msg = str(e).lower()
    
    if "rate" in error_msg or "limit" in error_msg:
        return SystemErrorInfo(SystemError.LLM_RATE_LIMIT, ...)
    elif "auth" in error_msg or "401" in error_msg or "403" in error_msg:
        return SystemErrorInfo(SystemError.LLM_AUTH_FAILED, ...)
    elif "timeout" in error_msg:
        return SystemErrorInfo(SystemError.LLM_REQUEST_TIMEOUT, ...)
    elif "quota" in error_msg or "balance" in error_msg:
        return SystemErrorInfo(SystemError.LLM_QUOTA_EXCEEDED, ...)
    else:
        return SystemErrorInfo(SystemError.LLM_SERVICE_UNAVAILABLE, ...)
```

### 前端辅助函数

```typescript
// electron-app/src/utils/errorHelpers.ts

import { SystemErrorInfo, ErrorCodes } from './errorCodes';

export function handleApiError(
  data: any,
  fallbackMessage: string
): SystemErrorInfo | string {
  if (data.error && data.error.code) {
    return data.error as SystemErrorInfo;
  }
  return data.message || fallbackMessage;
}

export function createNetworkError(
  technicalInfo: string
): SystemErrorInfo {
  return {
    code: ErrorCodes.NETWORK_TIMEOUT,
    category: 'NETWORK',
    message: '网络错误',
    user_message: '网络请求失败，请检查网络连接',
    suggestion: '1. 检查网络连接\n2. 重试操作\n3. 查看网络状态',
    technical_info: technicalInfo
  };
}
```

---

## 📊 进度跟踪

### 已完成 ✅
- [x] 错误码体系定义（37个错误码）
- [x] 后端日志系统
- [x] 前端错误展示组件（3种）
- [x] `/api/recording/start` - 音频设备错误
- [x] App.tsx - 基础错误处理
- [x] ASR/LLM/AudioRecorder 日志集成

### 进行中 🚧
- [ ] 核心 API 端点错误处理

### 待开始 📋
- [ ] WebSocket 错误传递
- [ ] 前端组件错误增强
- [ ] 存储层错误处理
- [ ] 配置层错误处理

---

## 🎯 预期收益

完成所有扩展后：

1. **错误覆盖率：** 从 30% → 95%
2. **用户体验：** 所有错误都有友好提示
3. **问题排查：** 完整的错误追踪链路
4. **开发效率：** 标准化的错误处理流程

---

## 📅 时间估算

- **第一阶段：** 1-2天（10-15小时）
- **第二阶段：** 2-3天（15-20小时）
- **第三阶段：** 1-2天（8-12小时）

**总计：** 4-7天（33-47小时）

---

**文档版本：** 1.0  
**创建日期：** 2026-01-02  
**维护者：** 深圳王哥 & AI

