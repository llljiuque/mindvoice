# MindVoice 跨平台存储架构

**版本**: v1.0  
**日期**: 2026-01-04  
**状态**: ✅ 完成

---

## 概述

MindVoice 采用统一的跨平台存储架构，支持所有主流操作系统。用户无需手动配置，系统会自动检测平台并设置合适的数据目录。

---

## 支持的平台

### 桌面平台（主要支持）

| 平台 | 默认数据目录 | 说明 |
|------|------------|------|
| **macOS** | `~/Library/Application Support/MindVoice` | 遵循 Apple 规范 |
| **Linux** | `~/.local/share/MindVoice` | 遵循 XDG 规范 |
| **Windows** | `%APPDATA%\MindVoice` | 通常是 `C:\Users\用户名\AppData\Roaming\MindVoice` |

### 移动平台（参考支持）

| 平台 | 默认数据目录 | 说明 |
|------|------------|------|
| **iOS** | `~/Documents/MindVoice` | 实际应用应使用 `NSDocumentDirectory` |
| **Android** | `/data/data/com.mindvoice.app/files/MindVoice` | 实际应用应使用 `Context.getFilesDir()` |

### 通用方案

| 平台 | 默认数据目录 | 说明 |
|------|------------|------|
| **通用简化** | `~/MindVoice` | 所有桌面平台均可用，简单明了 |

---

## 目录结构（统一）

无论何种平台，数据目录结构完全相同：

```
<data_dir>/
├── database/
│   └── history.db                # SQLite 数据库
├── images/
│   └── *.png                     # 用户上传的图片
├── knowledge/
│   ├── chroma/                   # 向量数据库
│   │   └── chroma.sqlite3
│   └── files/                    # 原始知识库文件
│       └── *.md, *.txt
└── backups/
    └── *.db.backup               # 数据库备份
```

---

## 自动配置工具

### 使用方法

```bash
# 自动生成适合当前平台的配置
python scripts/init_config.py
```

### 工作原理

1. **检测操作系统**：`sys.platform`
2. **选择合适路径**：根据平台规范
3. **生成配置文件**：自动修改 `config.yml`

### 支持的平台检测

```python
import sys

if sys.platform == "darwin":
    # macOS
    data_dir = "~/Library/Application Support/MindVoice"
elif sys.platform.startswith("linux"):
    # Linux (包括 Android)
    data_dir = "~/.local/share/MindVoice"
elif sys.platform == "win32":
    # Windows
    data_dir = "%APPDATA%/MindVoice"
elif sys.platform == "ios":
    # iOS
    data_dir = "~/Documents/MindVoice"
```

---

## 路径处理

### Python 代码

```python
from src.utils.platform_paths import expand_data_dir

# 自动展开 ~ 和环境变量
data_dir = expand_data_dir(config['storage']['data_dir'])

# 拼接子路径
db_path = data_dir / "database" / "history.db"
```

### Shell 脚本

```bash
# 读取配置（处理空格和注释）
DATA_DIR_RAW=$(grep '^\s*data_dir:' config.yml | \
               sed 's/.*data_dir:\s*//; s/#.*//; s/^[[:space:]]*//; s/[[:space:]]*$//')

# 展开 ~ 为用户主目录
DATA_DIR="${DATA_DIR_RAW/#\~/$HOME}"

# 拼接子路径
DB_PATH="$DATA_DIR/database/history.db"
```

---

## 配置示例

### macOS 配置

```yaml
storage:
  data_dir: ~/Library/Application Support/MindVoice
  database: database/history.db
  images: images
  knowledge: knowledge
  backups: backups
```

### Linux 配置

```yaml
storage:
  data_dir: ~/.local/share/MindVoice
  database: database/history.db
  images: images
  knowledge: knowledge
  backups: backups
```

### Windows 配置

```yaml
storage:
  data_dir: %APPDATA%/MindVoice  # 注意：使用正斜杠
  database: database/history.db
  images: images
  knowledge: knowledge
  backups: backups
```

### 通用简化配置

```yaml
storage:
  data_dir: ~/MindVoice  # 所有桌面平台通用
  database: database/history.db
  images: images
  knowledge: knowledge
  backups: backups
```

---

## 移动平台注意事项

### iOS

**Python 方案**（参考）：
```yaml
storage:
  data_dir: ~/Documents/MindVoice
```

**原生应用**（推荐）：
```swift
// 使用 iOS 标准 API
let documentsPath = FileManager.default.urls(
    for: .documentDirectory, 
    in: .userDomainMask
).first!
let dataDir = documentsPath.appendingPathComponent("MindVoice")
```

### Android

**Python 方案**（参考）：
```yaml
storage:
  data_dir: /data/data/com.mindvoice.app/files/MindVoice
```

**原生应用**（推荐）：
```java
// 使用 Android 标准 API
File dataDir = new File(
    context.getFilesDir(), 
    "MindVoice"
);
```

**注意**：
- 移动平台路径仅供 Python 脚本参考
- 实际原生应用应使用平台 API 获取路径
- 权限管理：Android 需要 `WRITE_EXTERNAL_STORAGE` 权限（外部存储）

---

## 兼容性矩阵

| 功能 | macOS | Linux | Windows | iOS | Android |
|------|-------|-------|---------|-----|---------|
| **自动路径检测** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **~ 展开** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **环境变量展开** | ✅ | ✅ | ✅ | ⚠️ | ⚠️ |
| **空格路径** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **相对路径** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **SQLite 数据库** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **文件存储** | ✅ | ✅ | ✅ | ✅ | ✅ |

**图例**：
- ✅ 完全支持
- ⚠️ 需要平台 API

---

## 用户指南

### 普通用户（推荐）

1. **自动配置**：
   ```bash
   python scripts/init_config.py
   ```
   系统自动检测平台并设置合适路径。

2. **启动应用**：
   ```bash
   ./quick_start.sh
   ```
   数据目录会自动创建。

### 高级用户

1. **手动配置**：
   ```bash
   cp config.yml.example config.yml
   vim config.yml  # 修改 storage.data_dir
   ```

2. **自定义路径**：
   ```yaml
   storage:
     data_dir: /my/custom/path/MindVoice
   ```

3. **验证配置**：
   ```bash
   python -c "from src.utils.platform_paths import expand_data_dir; \
              print(expand_data_dir('~/MindVoice'))"
   ```

---

## 常见问题

### Q1: 如何查看实际数据目录？

```bash
# macOS/Linux
python -c "from src.utils.platform_paths import get_default_data_dir, expand_data_dir; \
           print(expand_data_dir(get_default_data_dir()))"

# Windows
python -c "from src.utils.platform_paths import get_default_data_dir, expand_data_dir; print(expand_data_dir(get_default_data_dir()))"
```

### Q2: 可以在桌面上创建数据目录吗？

可以，修改 `data_dir` 为：
```yaml
storage:
  data_dir: ~/Desktop/MindVoice  # macOS/Linux
  # 或
  data_dir: %USERPROFILE%/Desktop/MindVoice  # Windows
```

### Q3: 多用户共享数据怎么办？

**不推荐**，但如果需要：
```yaml
storage:
  data_dir: /opt/MindVoice/shared  # Linux/macOS
  # 或
  data_dir: C:/ProgramData/MindVoice  # Windows
```

**注意**：需要设置适当的文件权限。

### Q4: 如何迁移数据？

```bash
# 1. 复制整个数据目录
cp -r "<旧路径>" "<新路径>"

# 2. 修改 config.yml
vim config.yml  # 更新 storage.data_dir

# 3. 重启应用
./stop.sh && ./quick_start.sh
```

---

## 技术细节

### 路径展开优先级

1. **环境变量展开**：`os.path.expandvars()`
   - Windows: `%APPDATA%` → `C:\Users\用户名\AppData\Roaming`
   - Linux: `$HOME` → `/home/username`

2. **用户目录展开**：`os.path.expanduser()`
   - 所有平台: `~` → 用户主目录

3. **绝对路径转换**：`Path().absolute()`

### 字符编码

- **配置文件**：UTF-8 编码
- **路径字符串**：支持 Unicode（中文、日文等）
- **文件名**：支持所有平台合法字符

### 权限管理

| 平台 | 默认权限 | 说明 |
|------|---------|------|
| macOS | `drwx------` (700) | 仅用户可访问 |
| Linux | `drwx------` (700) | 仅用户可访问 |
| Windows | 用户完全控制 | NTFS ACL |
| iOS | 应用沙盒 | 自动隔离 |
| Android | 应用私有 | `/data/data/` 仅应用可访问 |

---

## 总结

MindVoice 的跨平台存储架构具有以下优势：

1. **自动适配**：无需用户手动配置
2. **规范标准**：遵循各平台最佳实践
3. **统一结构**：所有平台目录结构一致
4. **易于迁移**：数据目录独立，便于备份
5. **扩展性强**：支持自定义路径

用户只需运行 `python scripts/init_config.py`，系统会自动完成所有配置！

---

**相关文件**：
- `src/utils/platform_paths.py` - 跨平台路径工具
- `scripts/init_config.py` - 配置初始化脚本
- `config.yml.example` - 配置示例（含多平台说明）
- `.cursorrules` - 开发规范（含跨平台指南）


