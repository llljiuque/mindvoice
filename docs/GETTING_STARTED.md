# MindVoice 全新构建指南

**版本**: v1.0 里程碑基准版本  
**日期**: 2026-01-04  
**适用场景**: 首次部署、系统复位、重新开始

---

## 快速开始（全新环境）

### 1. 克隆项目

```bash
git clone <repository-url>
cd 语音桌面助手
```

### 2. 配置系统

```bash
# 方案一：自动生成配置（推荐，跨平台）
python scripts/init_config.py

# 方案二：手动复制配置
cp config.yml.example config.yml

# 编辑配置文件，填入必要的配置
# - ASR 配置（火山引擎）
# - LLM 配置（API密钥）
# - 存储配置（自动生成的路径通常无需修改）
vim config.yml  # 或使用其他编辑器
```

**配置说明**：
- `init_config.py` 会自动检测操作系统并设置合适的数据目录
- macOS: `~/Library/Application Support/MindVoice`
- Linux: `~/.local/share/MindVoice`
- Windows: `%APPDATA%\MindVoice`
- iOS: `~/Documents/MindVoice` (如果使用 Python for iOS)
- Android: `/data/data/com.mindvoice.app/files/MindVoice` (原生应用)

### 3. 安装依赖

```bash
# Python 依赖
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 前端依赖
cd electron-app
npm install
cd ..
```

### 4. 启动系统

```bash
./quick_start.sh
```

系统会自动：
- 创建数据目录结构
- 初始化数据库
- 启动后端服务
- 启动前端应用

---

## 系统复位（已有环境）

如果需要清空所有数据，从头开始：

### 方案一：使用复位脚本（推荐）

```bash
# 执行复位脚本
./scripts/reset_system.sh

# 系统会提示确认，输入 yes 继续
# ⚠️  此操作会删除所有数据！
```

复位脚本会清理：
- ✅ 所有历史记录（数据库）
- ✅ 所有图片文件
- ✅ 所有知识库数据
- ✅ 所有编译缓存
- ✅ 所有日志文件

### 方案二：手动清理

```bash
# 1. 删除数据目录
rm -rf ~/Library/Application\ Support/MindVoice

# 2. 清理项目缓存
rm -rf electron-app/dist electron-app/dist-electron
rm -rf electron-app/node_modules/.vite
find . -name "__pycache__" -exec rm -rf {} +
rm -rf logs/*

# 3. 重启系统
./quick_start.sh
```

---

## 数据目录结构

首次启动后，系统会自动创建以下目录结构：

**macOS**：
```
~/Library/Application Support/MindVoice/
├── database/
│   └── history.db                # SQLite 数据库（空）
├── images/                       # 图片存储（空）
├── knowledge/                    # 知识库（空）
│   ├── chroma/                   # 向量数据库
│   └── files/                    # 原始文件
└── backups/                      # 备份目录（空）
```

**Linux**：
```
~/.local/share/MindVoice/
├── database/
│   └── history.db
├── images/
├── knowledge/
│   ├── chroma/
│   └── files/
└── backups/
```

**Windows**：
```
C:\Users\用户名\AppData\Roaming\MindVoice\
├── database\
│   └── history.db
├── images\
├── knowledge\
│   ├── chroma\
│   └── files\
└── backups\
```

---

## 配置说明

### 必需配置

**ASR 配置**（火山引擎）：
```yaml
asr:
  app_id: "your_app_id"
  app_key: "your_app_key"
  access_key: "your_access_key"
```

**LLM 配置**：
```yaml
llm:
  api_key: "your_api_key"
  base_url: "https://api.example.com/v1"
  model: "model-name"
```

### 存储配置（可选）

默认配置已经适合大多数场景，`init_config.py` 会根据操作系统自动设置：

**桌面平台**：

**macOS**：
```yaml
storage:
  data_dir: ~/Library/Application Support/MindVoice
```

**Linux**：
```yaml
storage:
  data_dir: ~/.local/share/MindVoice
```

**Windows**：
```yaml
storage:
  data_dir: %APPDATA%\MindVoice
```

**移动平台**（参考）：

**iOS**：
```yaml
storage:
  data_dir: ~/Documents/MindVoice
```

**Android**：
```yaml
storage:
  data_dir: /data/data/com.mindvoice.app/files/MindVoice
```

**通用简化方案**（桌面平台）：
```yaml
storage:
  data_dir: ~/MindVoice  # 在用户主目录下
```

如需修改存储位置，只需修改 `data_dir`：

```yaml
storage:
  data_dir: /path/to/your/data  # 自定义路径
  # 其他配置保持不变
```

**注意**：
- 移动平台路径仅供参考，实际应用应使用平台 API 获取
- iOS: 应使用 `NSDocumentDirectory`
- Android: 应使用 `Context.getFilesDir()` 或 `getExternalFilesDir()`

---

## 验证安装

### 1. 检查后端服务

```bash
curl http://127.0.0.1:8765/health
```

应返回：
```json
{
  "status": "ok",
  "version": "1.0.0",
  "uptime": 123
}
```

### 2. 检查数据库

```bash
# 从配置文件读取数据库路径
DATA_DIR=$(grep 'data_dir:' config.yml | sed 's/.*data_dir:\s*//' | tr -d ' ' | sed "s|~|$HOME|")
DB_PATH="$DATA_DIR/database/history.db"

# 检查数据库
sqlite3 "$DB_PATH" ".schema records"
```

应显示表结构：
```sql
CREATE TABLE records (
    id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    metadata TEXT,
    app_type TEXT NOT NULL DEFAULT 'voice-note',
    created_at TIMESTAMP NOT NULL
);
```

### 3. 测试基本功能

1. 打开应用
2. 选择一个应用（如 VoiceNote）
3. 点击录音按钮
4. 说话测试语音识别
5. 保存记录
6. 查看历史记录

---

## 常见问题

### Q1: 配置文件不存在

```bash
cp config.yml.example config.yml
```

### Q2: Python 依赖安装失败

```bash
# 确保使用 Python 3.9+
python3 --version

# 升级 pip
pip install --upgrade pip

# 重新安装依赖
pip install -r requirements.txt
```

### Q3: 前端依赖安装失败

```bash
cd electron-app

# 清理缓存
rm -rf node_modules package-lock.json

# 重新安装
npm install
```

### Q4: 端口被占用

```bash
# 查找占用端口的进程
lsof -i :8765

# 杀死进程
kill -9 <PID>

# 或修改端口
python api_server.py --port 8766
```

### Q5: 数据库初始化失败

```bash
# 检查配置文件
grep 'storage:' -A 5 config.yml

# 检查目录权限
ls -la ~/Library/Application\ Support/MindVoice

# 手动创建目录
mkdir -p ~/Library/Application\ Support/MindVoice/database
```

---

## 开发模式

### 启动后端服务

```bash
source venv/bin/activate
python api_server.py --log-level DEBUG
```

### 启动前端开发服务

```bash
cd electron-app
npm run dev
```

### 热重载

- 前端：保存文件后自动重载
- 后端：需要手动重启服务

---

## 生产环境构建

### 构建应用

```bash
cd electron-app
npm run build
```

### 打包 macOS 应用

```bash
./scripts/build/build-macos.sh
```

生成的应用位于：
- `release/MindVoice-<version>-mac.dmg`
- `release/MindVoice-<version>-mac.zip`

---

## 目录说明

### 项目根目录

```
语音桌面助手/
├── config.yml              # 配置文件（不提交）
├── config.yml.example      # 配置示例
├── quick_start.sh          # 快速启动脚本
├── stop.sh                 # 停止服务脚本
├── requirements.txt        # Python 依赖
├── src/                    # Python 后端源码
├── electron-app/           # Electron 前端源码
├── scripts/                # 工具脚本
│   ├── reset_system.sh     # 系统复位
│   ├── rebuild_database.sh # 数据库重建
│   └── build/              # 构建脚本
└── docs/                   # 文档
```

### 数据目录

```
~/Library/Application Support/MindVoice/
├── database/               # 数据库文件
├── images/                 # 图片文件
├── knowledge/              # 知识库
└── backups/                # 备份文件
```

---

## 更新版本

### 更新应用代码

```bash
git pull origin main
```

### 更新依赖

```bash
# Python 依赖
source venv/bin/activate
pip install -r requirements.txt --upgrade

# 前端依赖
cd electron-app
npm install
```

### 数据迁移

如果数据库结构有变化：

```bash
# 备份当前数据
cp ~/Library/Application\ Support/MindVoice/database/history.db \
   ~/Library/Application\ Support/MindVoice/backups/history.db.$(date +%Y%m%d)

# 重建数据库（会备份旧数据）
./scripts/rebuild_database.sh
```

---

## 备份和恢复

### 备份数据

```bash
# 方案一：备份整个数据目录
tar -czf mindvoice_backup_$(date +%Y%m%d).tar.gz \
  ~/Library/Application\ Support/MindVoice

# 方案二：仅备份数据库
./scripts/rebuild_database.sh  # 选项1: 备份
```

### 恢复数据

```bash
# 从备份恢复
tar -xzf mindvoice_backup_20260104.tar.gz -C ~/Library/Application\ Support/

# 或复制备份文件
cp ~/Library/Application\ Support/MindVoice/backups/history.db.20260104 \
   ~/Library/Application\ Support/MindVoice/database/history.db
```

---

## 技术支持

- **文档**: [项目 README](../README.md)
- **配置指南**: [config.yml.example](../config.yml.example)
- **构建指南**: [docs/build/BUILD_GUIDE.md](build/BUILD_GUIDE.md)
- **联系方式**: manwjh@126.com

---

**提示**: 这是 MindVoice v1.0 的里程碑基准版本，所有操作均基于统一存储架构设计。


