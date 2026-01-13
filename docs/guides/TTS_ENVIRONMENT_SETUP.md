# TTS 环境配置指南

**日期**: 2026-01-13

---

## 环境检查

### 确认 Python 环境

```powershell
python --version  # 应该是 3.10.x
python -c "import sys; print(sys.executable)"  # 应该包含 my_env3.10
```

### 检查依赖

```powershell
python -m pip list | findstr "funasr modelscope soundfile"
```

---

## 安装依赖

### 激活环境并安装

```powershell
# 1. 激活 conda 环境
conda activate my_env3.10

# 2. 确认环境
python --version  # 应该是 3.10.x

# 3. 如果 torch DLL 加载失败，使用 CPU 版本
python -m pip uninstall torch torchaudio -y
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m pip install torchaudio --index-url https://download.pytorch.org/whl/cpu

# 4. 安装 TTS 依赖
python -m pip install modelscope>=1.9.0 funasr>=1.0.0 soundfile>=0.12.0 scipy>=1.10.0 numpy>=1.24.0

# 5. 安装 CosyVoice 依赖
cd D:\work\mindvoice\mindvoice\third_party\CosyVoice-main
pip install -r requirements.txt
cd D:\work\mindvoice\mindvoice

# 6. 验证安装
python tests/check_funasr_install.py
```

---

## 常见问题

### 问题 1: Python 版本不匹配

**解决**:
```powershell
conda activate my_env3.10
# 或创建新环境
conda create -n my_env3.10 python=3.10
```

### 问题 2: torch DLL 加载失败

**解决**: 使用 CPU 版本的 torch（见上方步骤 3）

### 问题 3: 依赖安装在错误环境

**解决**: 使用 `python -m pip install` 而不是 `pip install`

---

## 验证安装

```powershell
python tests/check_funasr_install.py
python tests/test_tts_module_import.py
```

**预期输出**: 所有测试通过，TTS 服务可用

---

## 参考文档

- [快速开始](./TTS_QUICK_START.md) - 快速测试命令
- [测试指南](./TTS_TESTING.md) - 详细测试步骤

---

**最后更新**: 2026-01-13
