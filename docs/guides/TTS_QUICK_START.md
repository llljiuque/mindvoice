# TTS 功能快速开始

**日期**: 2026-01-13

---

## 快速测试 TTS 功能

### 1. 启动服务器

```powershell
# Windows PowerShell
cd D:\work\mindvoice\mindvoice

# 设置镜像源（可选，如果下载慢）
$env:HF_ENDPOINT = "https://hf-mirror.com"
$env:MODELSCOPE_MIRROR = "https://www.modelscope.cn"

# 启动服务器
python api_server.py
```

### 2. 测试 API

```powershell
# Windows PowerShell
# 查询提供商
curl http://localhost:8765/api/tts/providers

# 语音合成
curl -X POST http://localhost:8765/api/tts/synthesize `
  -H "Content-Type: application/json" `
  -d '{\"text\": \"你好，这是TTS测试\", \"language\": \"zh-CN\"}' `
  --output test_output.wav
```

```bash
# Linux/Mac
# 查询提供商
curl http://localhost:8765/api/tts/providers

# 语音合成
curl -X POST http://localhost:8765/api/tts/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "你好，这是TTS测试", "language": "zh-CN"}' \
  --output test_output.wav
```

### 3. 验证结果

```powershell
# Windows PowerShell
# 检查文件是否存在
Test-Path test_output.wav

# 查看文件大小
(Get-Item test_output.wav).Length
```

---

## 相关文档

- [测试指南](./TTS_TESTING.md) - 详细测试步骤
- [环境配置](./TTS_ENVIRONMENT_SETUP.md) - 环境配置和问题排查
- [实施总结](./TTS_IMPLEMENTATION_SUMMARY.md) - 功能实现总结

---

**最后更新**: 2026-01-13
