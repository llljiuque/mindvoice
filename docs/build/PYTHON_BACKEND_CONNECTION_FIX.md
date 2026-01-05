# Python 后端连接问题修复说明

**修复日期**: 2026-01-05  
**问题**: `ERR_CONNECTION_REFUSED` - Python API 服务器无法启动

---

## 🔍 问题分析

### 根本原因

1. **配置文件路径问题**
   - Python 后端期望在项目根目录找到 `config.yml`
   - 打包后的应用，工作目录是 `process.resourcesPath`
   - 配置文件被放在了 `config/config.yml.example`，路径不匹配

2. **Python 后端查找配置的逻辑**
   ```python
   # src/core/config.py
   project_root = Path(__file__).parent.parent.parent
   self.project_config_file = project_root / 'config.yml'
   ```
   - 打包后 `__file__` 指向 PyInstaller 临时目录
   - 无法通过相对路径找到配置文件

---

## ✅ 已完成的修复

### 1. 配置文件路径修正

**修改**: `build/config/electron-builder.json`

```json
{
  "from": "../config.yml.example",
  "to": "config.yml.example"  // 从 config/ 改为根目录
}
```

**效果**: 配置文件现在在 `Resources/config.yml.example`

### 2. 改进日志输出

**修改**: `electron-app/electron/main.ts`

- 添加详细的工作目录日志
- 收集 Python 后端的 stdout/stderr
- 检查配置文件是否存在并提示

### 3. 工作目录设置

- 生产环境工作目录: `process.resourcesPath`
- Python 后端在此目录查找 `config.yml`

---

## ⚠️ 当前限制

### 问题

打包后的 Python 可执行文件，`__file__` 指向 PyInstaller 临时目录，所以：

```python
project_root = Path(__file__).parent.parent.parent  # ❌ 指向错误位置
```

无法通过这种方式找到配置文件。

### 临时解决方案

**方法 1: 手动创建配置文件（推荐）**

1. 打开应用包：
   ```bash
   open /Applications/MindVoice.app/Contents/Resources/
   ```

2. 复制配置文件：
   ```bash
   cp config.yml.example config.yml
   ```

3. 编辑 `config.yml`，填入 API 密钥

4. 重启应用

**方法 2: 使用默认配置**

- Python 后端会使用默认配置
- 但功能受限（无 ASR、无 LLM）

---

## 🔧 永久解决方案（需要修改 Python 代码）

### 修改 Config 类支持工作目录查找

**文件**: `src/core/config.py`

```python
def __init__(self, config_dir: Optional[str] = None):
    # 优先从环境变量或工作目录查找
    if os.getenv('MINDVOICE_CONFIG_DIR'):
        project_root = Path(os.getenv('MINDVOICE_CONFIG_DIR'))
    elif os.getcwd():  # 从当前工作目录查找
        project_root = Path(os.getcwd())
    else:
        # 降级：使用 __file__ 相对路径
        project_root = Path(__file__).parent.parent.parent
    
    self.project_config_file = project_root / 'config.yml'
```

**然后重新打包 Python 后端**。

---

## 📋 验证步骤

### 1. 检查应用包内容

```bash
# 检查配置文件
ls -lh /Applications/MindVoice.app/Contents/Resources/config.yml.example

# 检查 Python 后端
ls -lh /Applications/MindVoice.app/Contents/Resources/python-backend/mindvoice-api
```

### 2. 查看启动日志

```bash
# 打开 Console.app
# 搜索 "MindVoice" 或 "Python"
# 查看是否有错误信息
```

### 3. 测试 API 连接

```bash
# 检查端口是否监听
lsof -i :8765

# 测试 API
curl http://127.0.0.1:8765/api/status
```

---

## 🎯 当前状态

- ✅ 配置文件已放在正确位置（Resources 根目录）
- ✅ 工作目录已设置正确
- ✅ 日志输出已改进
- ⚠️ Python 后端仍可能找不到配置文件（需要修改 Python 代码）

---

## 💡 建议

### 短期方案

1. **用户手动配置**（当前）
   - 复制 `config.yml.example` 为 `config.yml`
   - 填入 API 密钥

2. **应用首次启动向导**
   - 检测配置文件不存在
   - 显示配置向导界面
   - 引导用户配置

### 长期方案

1. **修改 Python Config 类**
   - 支持从工作目录查找配置
   - 支持环境变量指定配置目录

2. **配置文件位置**
   - 使用用户数据目录：`~/Library/Application Support/MindVoice/config.yml`
   - 应用启动时自动复制示例配置

---

**修复完成时间**: 2026-01-05  
**状态**: ⚠️ 部分修复（需要用户手动配置或修改 Python 代码）

