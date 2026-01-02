# VAD集成 - 安装和测试指南

## 📦 已完成的更改

### 1. 新增文件
- ✅ `src/utils/vad_filter.py` - VAD过滤器核心实现
- ✅ `docs/vad_integration_final.md` - 完整技术方案文档

### 2. 修改文件
- ✅ `requirements.txt` - 添加webrtcvad依赖
- ✅ `src/utils/audio_recorder.py` - 集成VAD功能
- ✅ `src/api/server.py` - 传入VAD配置
- ✅ `config.yml.example` - 添加VAD配置示例
- ✅ `config.yml` - 添加VAD配置

---

## 🚀 安装步骤

### 步骤1: 安装VAD依赖

```bash
# 激活虚拟环境
source venv/bin/activate

# 安装webrtcvad
pip install webrtcvad>=2.0.10

# 验证安装
python -c "import webrtcvad; print('VAD安装成功')"
```

### 步骤2: 更新音频参数（推荐）

编辑 `config.yml`，将音频chunk从1024改为3200：

```yaml
audio:
  chunk: 3200  # 从1024改为3200，获得更好的性能
```

**原因**: 
- 3200帧 = 200ms，符合火山引擎ASR推荐的最优配置
- VAD按20ms帧处理，200ms可以整除为10个20ms帧
- 减少处理次数，提高效率

---

## 🧪 测试步骤

### 测试1: VAD未启用（默认行为）

1. **确认配置**:
```yaml
audio:
  vad:
    enabled: false  # 保持关闭
```

2. **启动服务**:
```bash
./quick_start.sh
```

3. **测试录音**:
- 开始录音
- 说话并保持静音
- 停止录音

4. **验证**:
- ✅ 日志中无 `[VAD]` 标签
- ✅ ASR正常识别
- ✅ 功能正常，向后兼容

### 测试2: VAD启用（成本节约）

1. **修改配置**:
```yaml
audio:
  vad:
    enabled: true  # 启用VAD
```

2. **重启服务**:
```bash
./stop.sh
./quick_start.sh
```

3. **测试场景A - 正常对话**:
```
动作: 说话 "你好，我想问一下..." 
预期: 
- 日志显示 [VAD] 初始化成功
- 日志显示 [VAD] 语音开始
- ASR正常识别全部内容（包括"你好"）
- 日志显示 [VAD] 语音结束
```

4. **测试场景B - 开头词测试**:
```
动作: 说话 "嗯...这个问题..." 
预期:
- "嗯..."不应被截断
- 完整识别所有内容
```

5. **测试场景C - 长时间静音**:
```
动作: 说话 → 静音30秒 → 再说话
预期:
- 第一次说话正常识别
- 静音期间不发送数据
- 第二次说话正常识别（可能有短暂延迟200-500ms）
```

6. **查看统计信息**:
停止录音后，检查日志：
```
[VAD] 统计: 总帧数=1000, 语音帧=300, 过滤帧=700, 过滤率=70.0%
```

**预期过滤率**: 60-80%

---

## 📊 性能验证

### 验证1: 延迟测试

```bash
# 测量音频采集到ASR识别的延迟
# 预期: 延迟增加 < 20ms
```

### 验证2: CPU占用测试

```bash
# 监控CPU占用率
# 预期: CPU占用增加 < 5%
top -pid $(pgrep -f api_server)
```

### 验证3: 过滤率测试

**正常范围**: 60-80%

**调整建议**:
- 过滤率过高（>90%）: 可能误判语音为静音
  - 降低 `mode`（如2→1）
  - 降低 `speech_start_threshold`（如2→1）
  
- 过滤率过低（<20%）: 可能误判静音为语音
  - 提高 `mode`（如2→3）
  - 提高 `speech_end_threshold`（如10→15）

---

## 🔧 故障排查

### 问题1: 导入错误

**错误信息**:
```
ModuleNotFoundError: No module named 'webrtcvad'
```

**解决**:
```bash
source venv/bin/activate
pip install webrtcvad>=2.0.10
```

### 问题2: 语音截断

**症状**: "嗯...我想问"被识别为"我想问"

**解决**: 增大前置缓冲
```yaml
audio:
  vad:
    pre_speech_padding_ms: 200  # 从100改为200
```

### 问题3: 过滤率异常

**症状**: 过滤率显示0%或100%

**检查**:
1. 确认 `enabled: true`
2. 查看日志是否有 `[VAD] 初始化成功`
3. 检查 `chunk` 是否为3200

### 问题4: 连接超时

**症状**: 长时间静音后ASR无响应

**说明**: 这是正常的，连接超时（>60秒）会断开

**解决**: 
- 方案A: 接受短暂延迟（推荐）
- 方案B: 实现自动重连（可选）

---

## 📈 成本分析

### 启用前（无VAD）
```
假设: 1小时录音
- 发送音频: 100%
- ASR调用: 100%
- 成本: 1.0x
```

### 启用后（有VAD）
```
假设: 1小时录音，70%过滤率
- 发送音频: 30%
- ASR调用: 30%
- 成本: 0.3x
- 节约: 70%
```

**实际节约**: 预计40-60%（考虑到语音间隙、后置缓冲等）

---

## 📝 配置调优指南

### 场景1: 安静环境（办公室）

```yaml
vad:
  mode: 2                          # 标准敏感度
  speech_start_threshold: 2        # 标准
  speech_end_threshold: 10         # 标准
  pre_speech_padding_ms: 100       # 标准
  post_speech_padding_ms: 300      # 标准
```

### 场景2: 嘈杂环境（街道）

```yaml
vad:
  mode: 3                          # 更严格（减少噪音误检）
  speech_start_threshold: 3        # 更高阈值
  speech_end_threshold: 12         # 更高阈值
  pre_speech_padding_ms: 150       # 更多缓冲
  post_speech_padding_ms: 400      # 更多缓冲
```

### 场景3: 快速对话

```yaml
vad:
  mode: 1                          # 更宽松（减少漏检）
  speech_start_threshold: 1        # 更快开始
  speech_end_threshold: 8          # 更快结束
  pre_speech_padding_ms: 150       # 更多缓冲
  post_speech_padding_ms: 250      # 适中
```

---

## ✅ 验收标准

### 功能验收
- [ ] VAD未启用时，系统功能正常（向后兼容）
- [ ] VAD启用时，能正常过滤静音
- [ ] 无语音截断问题（包括开头词"嗯..."）
- [ ] 过滤率在60-80%范围

### 性能验收
- [ ] 延迟增加 < 20ms
- [ ] CPU占用增加 < 5%
- [ ] 内存占用增加 < 10MB

### 成本验收
- [ ] 实际成本节约 40-60%
- [ ] ASR调用次数明显减少

---

## 🎯 下一步优化（可选）

1. **自动重连机制** - 处理长时间静音超时
2. **动态参数调整** - 根据环境噪音自动调整VAD参数
3. **性能监控** - 添加Prometheus指标监控VAD效果
4. **A/B测试** - 对比VAD启用前后的成本和质量

---

**文档版本**: 1.0  
**创建日期**: 2026-01-02  
**维护者**: MindVoice 开发团队

