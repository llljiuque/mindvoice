# TTS 功能测试指南

**日期**: 2026-01-13

---

## 一、测试前准备

### 启动服务器

```powershell
cd D:\work\mindvoice\mindvoice
python api_server.py
```

**默认地址**: `http://127.0.0.1:8765`

---

## 二、API 功能测试

### 测试 1: 查询提供商

```powershell
curl http://localhost:8765/api/tts/providers
```

**预期**: 返回 `cosyvoice3` 提供商，`available: true`

### 测试 2: 查询音色

```powershell
curl http://localhost:8765/api/tts/voices
```

### 测试 3: 语音合成

```powershell
curl -X POST http://localhost:8765/api/tts/synthesize `
  -H "Content-Type: application/json" `
  -d '{\"text\": \"你好，这是测试\", \"language\": \"zh-CN\"}' `
  --output test_output.wav
```

**验证**: 检查 `test_output.wav` 文件是否存在且可播放

### 测试 4: 流式合成

```powershell
curl -X POST http://localhost:8765/api/tts/stream `
  -H "Content-Type: application/json" `
  -d '{\"text\": \"你好，这是流式测试\", \"language\": \"zh-CN\"}' `
  --output test_stream.wav
```

---

## 三、应用内交互测试

### 前提条件
- 后端服务器已启动
- 前端应用已启动

### 测试步骤
1. 打开 MindVoice 应用
2. 确认 API 连接状态正常
3. 测试 TTS 功能（如果有）
4. 验证音频播放正常

---

## 四、故障排查

### 错误 1: TTS 服务不可用

**解决**:
1. 查看服务器日志
2. 检查 `config.yml` 中 `tts.enabled: true`
3. 确认依赖已安装

### 错误 2: 连接被拒绝

**解决**:
1. 确认服务器已启动
2. 检查端口号（默认 8765）

### 错误 3: 模型加载失败

**解决**:
1. 查看日志错误信息
2. 确认 CosyVoice 路径正确（`third_party/CosyVoice-main`）
3. 确认模型已下载或可以下载

---

## 五、测试检查清单

- [ ] 服务器可以正常启动
- [ ] TTS 服务初始化成功（查看日志）
- [ ] `/api/tts/providers` 返回正确
- [ ] `/api/tts/voices` 返回正确
- [ ] `/api/tts/synthesize` 可以生成音频
- [ ] 生成的音频文件可以播放

---

**最后更新**: 2026-01-13
