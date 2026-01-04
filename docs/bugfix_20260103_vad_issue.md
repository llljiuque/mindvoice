# VAD 问题诊断报告 - 2026-01-03

## 问题描述
用户报告语音输入功能不正常，应用一直显示"ASR输入中..."状态，但没有识别结果输出。

## 问题分析过程

### 1. 初始症状
- 应用启动录音后一直处于录音状态
- 界面显示"ASR输入中..."
- 录音按钮保持红色
- 无任何识别文本输出

### 2. 日志分析

#### 时间线（2026-01-03）
- **22:38:24** - 用户开始录音
- **22:41:13** - VAD 检测到语音（延迟约 **3分钟**）
- **22:41:14** - ASR 启动成功
- **22:41:14**（同一秒）- VAD 立即触发停止 ASR
- **22:41:14 之后** - VAD 每隔几秒就反复触发停止 ASR

#### 关键日志片段
```
2026-01-03 22:41:13 - src.services.voice_service - INFO - [语音服务] AudioASRGateway 触发：启动ASR
2026-01-03 22:41:14 | [32mINFO[0m | MindVoice.ASR.Volcano | [ASR-WS] ✓ 流式识别已启动
2026-01-03 22:41:14 - src.services.voice_service - INFO - [语音服务] ✓ ASR已启动（由AudioASRGateway触发）
2026-01-03 22:41:14 - src.services.voice_service - INFO - [语音服务] AudioASRGateway 触发：停止ASR（发送结束标记）
2026-01-03 22:41:15 - src.services.voice_service - INFO - [语音服务] AudioASRGateway 触发：停止ASR（发送结束标记）
2026-01-03 22:41:27 - src.services.voice_service - INFO - [语音服务] AudioASRGateway 触发：停止ASR（发送结束标记）
... (反复出现)
```

### 3. 根本原因

**VAD 配置过于严格，导致误判和反复触发**

当前配置：
```yaml
vad:
  enabled: true
  mode: 3  # WebRTC VAD 最严格模式（0-3）
  speech_start_threshold: 5  # 需要连续5帧都是语音才启动
  speech_end_threshold: 15  # 连续15帧静音才停止
```

问题表现：
1. **启动延迟过高**：mode=3 + threshold=5 导致需要3分钟才检测到语音
2. **状态不稳定**：检测到语音后，因为信号不够强，VAD 在 SPEECH ↔ SILENCE 之间快速切换
3. **ASR 反复启停**：每次切换到 SILENCE 状态都触发 `on_speech_end` 回调，导致 ASR 收到大量停止信号
4. **JSON 解析错误**：频繁的停止操作导致 WebSocket 消息格式异常

### 4. 为什么会这样？

#### WebRTC VAD 工作原理
WebRTC VAD 基于能量和频谱分析检测语音活动：
- **Mode 0**: 最宽松，适合远场/低质量麦克风
- **Mode 1**: 宽松，适合普通环境
- **Mode 2**: 中等（默认）
- **Mode 3**: 最严格，适合近场/高质量麦克风 + 安静环境

#### 为什么 Mode=3 失败？
1. **环境噪音**：即使很小的背景噪音也可能导致检测失败
2. **麦克风质量**：如果麦克风增益不足，语音能量可能达不到阈值
3. **说话方式**：正常说话的能量波动可能超出严格模式的容忍范围

#### 为什么延迟3分钟？
需要满足：
- 连续 **5帧**（100ms）都被判定为语音
- Mode=3 对每帧的要求极高
- 用户可能说了很多话，但都没有连续5帧达标

## 解决方案

### 方案1：禁用 VAD（立即解决）✅

```yaml
vad:
  enabled: false  # 禁用 VAD
```

**优点**：
- 立即解决问题，ASR 稳定工作
- 无延迟，响应灵敏

**缺点**：
- 所有音频都发送给 ASR，包括静音
- ASR 成本增加（无过滤）

### 方案2：降低 VAD 敏感度（推荐长期方案）

```yaml
vad:
  enabled: true
  mode: 1  # 改为宽松模式
  speech_start_threshold: 3  # 降低阈值
  speech_end_threshold: 15
```

**优点**：
- 保留成本节约优势（过滤静音）
- 更适合实际使用环境
- 响应更快

**缺点**：
- 可能误检测一些背景噪音为语音

### 方案3：自适应 VAD（未来优化）

- 动态调整 VAD 参数
- 根据环境噪音水平自动选择 mode
- 学习用户的语音特征

## 当前状态

已将 VAD 配置更改为：
```yaml
vad:
  enabled: false  # 暂时禁用，确保功能正常
```

**需要重启应用以应用新配置**

## 测试验证

重启后需要验证：
1. ✅ 点击录音按钮，ASR 立即启动
2. ✅ 对着麦克风说话，实时显示识别文本
3. ✅ 点击停止按钮，正确保存识别结果
4. ✅ 不再有反复的 "AudioASRGateway 触发：停止ASR" 日志

## 经验教训

1. **VAD 配置需要根据实际环境调整**：不能盲目使用最严格模式
2. **需要更好的调试工具**：实时显示 VAD 检测状态
3. **需要添加 VAD 健康检查**：如果长时间无法检测到语音，应发出警告
4. **考虑添加手动模式切换**：让用户可以选择是否启用 VAD

## 相关文件

- 配置文件：`config.yml`
- VAD 实现：`src/utils/audio_asr_gateway.py`
- 语音服务：`src/services/voice_service.py`
- 日志文件：`logs/api_server_20260103_223737.log`

