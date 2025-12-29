# API架构文档

## 概述

本项目采用**前后端完全分离**的架构设计，便于后续更换前端框架。

## 架构图

```
┌─────────────────────────────────┐
│  前端层（可替换）                │
│  - Electron（当前）              │
│  - Tauri（未来可选）             │
│  - Web应用（未来可选）            │
└────────────┬────────────────────┘
             │ HTTP/WebSocket
┌────────────▼────────────────────┐
│  API服务层（Python FastAPI）     │
│  - HTTP REST API                │
│  - WebSocket实时推送             │
└────────────┬────────────────────┘
             │
┌────────────▼────────────────────┐
│  业务逻辑层（Python）            │
│  - VoiceService                 │
│  - AudioRecorder                │
│  - ASRProvider                  │
│  - StorageProvider               │
└─────────────────────────────────┘
```

## API接口规范

### HTTP REST API

#### 1. 获取状态
```
GET /api/status

响应:
{
  "state": "idle" | "recording" | "paused" | "processing",
  "current_text": "当前识别的文本"
}
```

#### 2. 开始录音
```
POST /api/recording/start

响应:
{
  "success": true,
  "message": "录音已开始"
}
```

#### 3. 暂停录音
```
POST /api/recording/pause

响应:
{
  "success": true,
  "message": "录音已暂停"
}
```

#### 4. 恢复录音
```
POST /api/recording/resume

响应:
{
  "success": true,
  "message": "录音已恢复"
}
```

#### 5. 停止录音
```
POST /api/recording/stop

响应:
{
  "success": true,
  "final_text": "最终识别的文本",
  "message": "录音已停止"
}
```

### WebSocket API

#### 连接
```
ws://127.0.0.1:8765/ws
```

#### 消息类型

1. **初始状态**（连接时自动发送）
```json
{
  "type": "initial_state",
  "state": "idle",
  "text": ""
}
```

2. **文本更新**
```json
{
  "type": "text_update",
  "text": "识别到的文本"
}
```

3. **状态变化**
```json
{
  "type": "state_change",
  "state": "recording"
}
```

4. **错误**
```json
{
  "type": "error",
  "error_type": "ASR_ERROR",
  "message": "错误描述"
}
```

## 前端替换指南

### 替换为Tauri

1. 保持API接口不变
2. 修改前端代码使用Tauri的HTTP客户端
3. 使用Tauri的WebSocket API

### 替换为Web应用

1. 部署Python API服务器到云服务器
2. 修改API地址配置
3. 使用任何Web框架（React/Vue/Angular等）

### 替换为移动应用

1. 使用相同的API接口
2. 使用移动端HTTP/WebSocket客户端
3. 适配移动端UI

## 配置

API服务器默认配置：
- 地址: `127.0.0.1`
- 端口: `8765`
- HTTP端点: `http://127.0.0.1:8765/api/`
- WebSocket端点: `ws://127.0.0.1:8765/ws`

可以通过环境变量或命令行参数修改：
```bash
python api_server.py --host 0.0.0.0 --port 8080
```

## 安全考虑

1. **CORS配置**: 当前允许所有来源，生产环境应限制
2. **认证**: 未来可以添加API密钥或Token认证
3. **HTTPS/WSS**: 生产环境应使用加密连接

## 扩展性

API服务层设计支持：
- 多客户端连接（WebSocket广播）
- 异步处理（FastAPI + asyncio）
- 插件化架构（ASR/Storage提供商）

