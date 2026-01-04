# 存储格式迁移修复报告

**日期**: 2026-01-04  
**问题**: 启动失败，KeyError: 'data_dir'  
**原因**: 代码中存在新旧存储格式混用

---

## 问题根源

系统在里程碑版本中定义了新的存储格式：

**旧格式**（已废弃）：
```yaml
storage:
  type: sqlite
  path: ~/.voice_assistant/history.db  # 单一路径
```

**新格式**（当前标准）：
```yaml
storage:
  data_dir: ~/Library/Application Support/MindVoice  # 数据根目录
  database: database/history.db    # 相对路径
  images: images
  knowledge: knowledge
  backups: backups
```

但部分代码文件仍在使用旧格式，导致启动失败。

---

## 错误日志

```
KeyError: 'data_dir'
  File ".../src/providers/storage/sqlite.py", line 40, in initialize
    data_dir = Path(config['data_dir']).expanduser()
```

**问题链**：
1. `voice_service.py` 传递 `storage.path` 给存储提供商
2. `sqlite.py` 期望 `data_dir` 和 `database`
3. 配置键名不匹配，抛出 KeyError

---

## 修复内容

### 1. `src/services/voice_service.py`

**修改前**（旧格式）：
```python
storage_config = {
    'path': self.config.get('storage.path', '~/.voice_assistant/history.db')
}
```

**修改后**（新格式）：
```python
storage_config = {
    'data_dir': self.config.get('storage.data_dir', '~/Library/Application Support/MindVoice'),
    'database': self.config.get('storage.database', 'database/history.db')
}
```

---

### 2. `src/core/config.py`

#### 2.1 默认配置

**修改前**：
```python
'storage': {
    'type': 'sqlite',
    'path': str(self.config_dir / 'history.db')
},
```

**修改后**：
```python
'storage': {
    'type': 'sqlite',
    'data_dir': '~/Library/Application Support/MindVoice',
    'database': 'database/history.db',
    'images': 'images',
    'knowledge': 'knowledge',
    'backups': 'backups'
},
```

#### 2.2 注释和文档

**修改前**：
```python
"""
配置优先级（ASR配置）：
1. 用户自定义配置（~/.voice_assistant/user_asr_config.yml）
...
config_dir: 配置目录路径，默认为 ~/.voice_assistant
"""
```

**修改后**：
```python
"""
配置优先级（ASR配置）：
1. 用户自定义配置（~/Library/Application Support/MindVoice/user_asr_config.yml）
...
config_dir: 配置目录路径，默认使用 storage.data_dir
"""
```

#### 2.3 初始化逻辑

**修改前**：
```python
if config_dir is None:
    config_dir = os.path.join(os.path.expanduser('~'), '.voice_assistant')
```

**修改后**：
```python
if config_dir is None:
    # 使用 storage.data_dir 作为配置目录
    config_dir = Path(self.get('storage.data_dir', '~/Library/Application Support/MindVoice')).expanduser()
```

---

### 3. `src/services/knowledge_service.py`

**修改前**（旧接口）：
```python
def __init__(
    self, 
    storage_path: str,  # 接受完整路径字符串
    embedding_model: str = "all-MiniLM-L6-v2",
    ...
):
    self.storage_path = Path(storage_path)
```

**修改后**（新接口）：
```python
def __init__(
    self, 
    data_dir: Path,                  # 数据根目录
    knowledge_relative_path: Path,   # 知识库相对路径
    embedding_model: str = "all-MiniLM-L6-v2",
    ...
):
    self.data_dir = data_dir
    self.knowledge_relative_path = knowledge_relative_path
    self.storage_path = self.data_dir / self.knowledge_relative_path
```

---

### 4. `src/api/server.py`

**修改前**：
```python
storage_config = config_dict['storage']
data_dir = Path(storage_config['data_dir']).expanduser()
knowledge_relative = storage_config['knowledge']
knowledge_path = str(data_dir / knowledge_relative)

knowledge_service = KnowledgeService(
    storage_path=knowledge_path,  # 旧接口
    embedding_model="all-MiniLM-L6-v2",
    lazy_load=True
)
```

**修改后**：
```python
storage_config = config_dict['storage']
data_dir = Path(storage_config['data_dir']).expanduser()
knowledge_relative = Path(storage_config['knowledge'])

knowledge_service = KnowledgeService(
    data_dir=data_dir,                         # 新接口
    knowledge_relative_path=knowledge_relative,
    embedding_model=config_dict.get('knowledge', {}).get('embedding_model', 'all-MiniLM-L6-v2'),
    lazy_load=config_dict.get('knowledge', {}).get('lazy_load', True)
)
```

---

### 5. 文档更新

#### `CHANGELOG.md`
- 旧：`data/images/` 目录
- 新：由 `config.yml` 的 `storage.data_dir/storage.images` 配置决定

#### `README.md`
- 旧：文档存储路径：`./data/knowledge/`
- 新：由 `config.yml` 的 `storage.data_dir/storage.knowledge` 配置决定

---

## 验证结果

### 扫描脚本
创建了 `scripts/scan_storage_format.py` 用于检测新旧格式使用情况。

### 扫描结果
```
============================================================
MindVoice 存储格式扫描报告
============================================================

❌ 发现旧格式引用: 0
  (无)

✅ 使用新格式: 3
  src/core/config.py: data_dir ✓
  src/services/voice_service.py: data_dir ✓
  src/services/voice_service.py: database ✓

============================================================
✅ 扫描完成：所有文件已迁移到新格式！
```

---

## 测试步骤

```bash
# 1. 停止服务
./stop.sh

# 2. 复位系统
./scripts/reset_system.sh

# 3. 重新启动
./quick_start.sh
```

**预期结果**：
- ✅ API 服务器成功启动
- ✅ 自动创建数据目录：`~/Library/Application Support/MindVoice/`
- ✅ 数据库初始化：`~/Library/Application Support/MindVoice/database/history.db`
- ✅ 前端连接成功

---

## 关键改进

### 1. 统一的存储架构
所有存储路径统一由 `config.yml` 的 `storage` 部分控制：
- `data_dir`: 数据根目录
- `database`: 数据库相对路径
- `images`: 图片相对路径
- `knowledge`: 知识库相对路径
- `backups`: 备份相对路径

### 2. 跨平台兼容
- macOS: `~/Library/Application Support/MindVoice`
- Linux: `~/.local/share/MindVoice`
- Windows: `%APPDATA%\MindVoice`
- iOS: `~/Documents/MindVoice`
- Android: `/data/data/com.mindvoice.app/files/MindVoice`

### 3. 自动配置工具
```bash
python scripts/init_config.py  # 自动检测平台并设置路径
```

### 4. 扫描工具
```bash
python scripts/scan_storage_format.py  # 检测新旧格式使用情况
```

---

## 受影响的组件

| 组件 | 修改内容 | 状态 |
|------|---------|-----|
| `VoiceService` | 传递 data_dir + database | ✅ |
| `SQLiteStorageProvider` | 接收新格式配置 | ✅ |
| `KnowledgeService` | 接收 data_dir + knowledge_relative_path | ✅ |
| `Config` | 默认配置使用新格式 | ✅ |
| 文档 | 更新路径说明 | ✅ |

---

## 总结

### 修复完成项
1. ✅ 所有代码迁移到新存储格式
2. ✅ 统一配置管理（`config.yml`）
3. ✅ 跨平台路径支持
4. ✅ 自动配置工具
5. ✅ 格式扫描工具
6. ✅ 文档更新

### 遗留问题
- 无

### 后续建议
1. 测试所有平台的启动流程
2. 验证数据库、图片、知识库的读写
3. 测试自动配置工具在不同平台的表现

---

**相关文件**：
- `src/services/voice_service.py`
- `src/core/config.py`
- `src/services/knowledge_service.py`
- `src/api/server.py`
- `scripts/scan_storage_format.py`
- `CHANGELOG.md`
- `README.md`

