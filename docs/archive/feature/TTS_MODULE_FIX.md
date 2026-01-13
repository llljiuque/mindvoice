# TTS模块独立化修复记录

**日期**: 2026-01-13  
**状态**: ✅ 已修复

---

## 问题描述

将TTS调整为独立模块后，后端无法正常启动。

---

## 发现的问题

### 1. 导入路径错误

**文件**: `src/providers/tts/__init__.py`

**问题**: 
```python
from ..core.base import TTSProvider  # 错误：路径层级不对
```

**原因**: 
- `src/providers/tts/__init__.py` 位于 `src/providers/tts/` 目录
- 要导入 `src/core/base.py`，需要向上3级，而不是2级

**修复**:
```python
from ...core.base import TTSProvider  # 正确：向上3级
```

### 2. 缺少类属性

**文件**: `src/providers/tts/cosyvoice3.py`

**问题**: 
- `CosyVoice3Provider` 类缺少 `DISPLAY_NAME` 和 `DESCRIPTION` 属性
- API端点 `/api/tts/providers` 需要这些属性来显示提供商信息

**修复**:
```python
class CosyVoice3Provider(BaseTTSProvider):
    PROVIDER_NAME = "cosyvoice3"
    DISPLAY_NAME = "Fun-CosyVoice3"
    DESCRIPTION = "基于ModelScope的Fun-CosyVoice3模型，支持流式合成、多语言和零样本音色克隆"
```

---

## 修复内容

### 修改的文件

1. **`src/providers/tts/__init__.py`**
   - 修复导入路径：`..core.base` → `...core.base`

2. **`src/providers/tts/cosyvoice3.py`**
   - 添加 `DISPLAY_NAME` 类属性
   - 添加 `DESCRIPTION` 类属性

---

## 验证测试

创建了测试脚本 `tests/test_tts_module_import.py` 验证修复：

```bash
python tests/test_tts_module_import.py
```

**测试结果**: ✅ 所有测试通过

- ✅ 提供商模块导入成功
- ✅ 列出可用提供商成功
- ✅ 获取提供商类成功
- ✅ TTS服务导入成功
- ✅ TTS服务初始化成功

---

## 架构验证

### 模块结构

```
src/
├── providers/
│   └── tts/
│       ├── __init__.py          # 提供商注册和发现
│       ├── base_tts.py          # 基类
│       └── cosyvoice3.py        # CosyVoice3实现
├── services/
│   └── tts_service.py          # TTS服务层
└── api/
    └── server.py                # API端点
```

### 导入路径

- `src/providers/tts/__init__.py` → `...core.base` (向上3级)
- `src/services/tts_service.py` → `..providers.tts` (向上1级)
- `src/api/server.py` → `..providers.tts` (向上2级)

---

## 后续建议

1. **添加更多TTS提供商时**:
   - 确保实现 `DISPLAY_NAME` 和 `DESCRIPTION` 属性
   - 在 `src/providers/tts/__init__.py` 中注册新提供商

2. **测试新提供商**:
   - 运行 `tests/test_tts_module_import.py` 验证导入
   - 运行 `tests/test_tts_diagnosis.py` 验证初始化
   - 运行 `tests/test_tts.py` 验证功能

3. **API端点测试**:
   - `GET /api/tts/providers` - 查询可用提供商
   - `GET /api/tts/voices` - 查询音色列表
   - `POST /api/tts/synthesize` - 文本转语音

---

## 相关文档

- [TTS测试指南](../guides/TTS_TESTING.md)
- [TTS快速开始](../guides/TTS_QUICK_START.md)
