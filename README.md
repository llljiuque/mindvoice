# 语音桌面助手 (MindVoice)

一个基于AI的跨平台桌面语音助手，支持语音转文字、语音笔记和翻译功能。

**English**: [README_EN.md](README_EN.md) | **项目英文名**: MindVoice

**架构**: Electron前端 + Python API后端（前后端分离，便于替换前端框架）

## 功能特性

- 🎤 语音转文字（使用第三方 ASR 服务）
- 📝 语音笔记记录
- 🌐 多语言翻译（待实现）
- 💾 历史记录存储
- 📋 一键复制文本
- 🎯 系统托盘图标
- 🔌 可扩展的插件架构

## 架构设计

本项目采用前后端分离的架构设计：

- **后端**: Python API服务器（FastAPI + WebSocket）
- **前端**: Electron + React + TypeScript
- **通信**: HTTP REST API + WebSocket实时推送

详细架构说明请参考 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) 和 [docs/ARCHITECTURE_API.md](docs/ARCHITECTURE_API.md)

## 快速开始

### 前置要求

- Python 3.9+
- Node.js 18+
- npm 或 yarn

### 安装步骤

1. **安装Python依赖**：
```bash
pip install -r requirements.txt
```

2. **安装Electron前端依赖**：
```bash
cd electron-app
npm install
```

3. **配置 ASR 服务**（可选）：

**方式一：使用配置助手脚本（推荐）**
```bash
python setup_asr.py
```

**方式二：手动配置**
```bash
# 复制示例配置文件
cp config.yml.example config.yml

# 编辑配置文件，填入你的 API 密钥
nano config.yml
```

**重要：** 配置文件 `config.yml` 包含敏感信息，已添加到 `.gitignore`，不会被提交到版本控制系统。

详细配置说明请参考 [docs/CONFIG.md](docs/CONFIG.md)

4. **运行应用**：

**方式一：使用 Electron（推荐）**
```bash
# 终端1：启动API服务器
python api_server.py

# 终端2：启动Electron前端
cd electron-app
npm run dev
```

**方式二：仅运行API服务器（用于开发或Web前端）**
```bash
python api_server.py
# API服务器将在 http://127.0.0.1:8765 运行
```

**停止应用**：
```bash
# 使用停止脚本（推荐）
./stop.sh

# 或手动停止
# 按 Ctrl+C 停止当前终端中的进程
# 如果进程在后台运行，使用：
# kill $(pgrep -f api_server.py)
```

## 项目结构

```
src/
├── core/              # 核心模块（抽象接口、配置、插件管理）
├── providers/         # 提供商实现（ASR、存储）
├── services/          # 服务层（业务逻辑）
├── api/               # API服务层（FastAPI）
└── utils/             # 工具模块

electron-app/          # Electron前端（React + TypeScript）
```

## 扩展开发

### 添加新的 ASR 提供商

1. 在 `src/providers/asr/` 下创建新文件
2. 继承 `ASRProvider` 并实现所有方法
3. 在 `src/api/server.py` 中加载：`plugin_manager.load_plugin_module('src.providers.asr.your_provider')`

### 添加新的存储提供商

1. 在 `src/providers/storage/` 下创建新文件
2. 继承 `StorageProvider` 并实现所有方法
3. 在配置中设置 `storage.provider` 为你的提供商名称

## 使用说明

- 启动应用后，点击系统托盘图标显示/隐藏窗口
- 点击"开始"按钮开始语音识别
- 点击"暂停"暂停识别
- 点击"停止"停止并保存
- 识别结果会自动显示，可一键复制

## 开发状态

当前版本已完成：
- ✅ 核心架构设计（前后端分离）
- ✅ 插件系统
- ✅ 配置管理
- ✅ 火山引擎 ASR 提供商集成
- ✅ 音频录制器（基于 sounddevice）
- ✅ Electron前端界面（React + TypeScript）
- ✅ API服务层（FastAPI + WebSocket）
- ✅ SQLite 存储提供商
- ✅ 录音控制（开始/暂停/停止）
- ✅ 实时文本显示和复制功能
- ✅ 历史记录存储

待实现：
- ⏳ 翻译功能
- ⏳ 更多 ASR 提供商（百度、讯飞等）
- ⏳ 历史记录查看界面

## 技术栈

### 后端
- **Python 3.9+**
- **FastAPI**: API 服务器框架
- **sounddevice**: 音频录制
- **aiohttp**: 异步 HTTP/WebSocket 客户端
- **SQLite**: 数据存储

### 前端
- **Electron**: 跨平台桌面应用框架
- **React**: UI 框架
- **TypeScript**: 类型安全
- **Vite**: 构建工具

## 扩展性

项目采用插件化架构，可以轻松添加：

1. **新的 ASR 提供商**: 继承 `ASRProvider`，实现 `recognize` 方法
2. **新的存储提供商**: 继承 `StorageProvider`，实现存储接口
3. **新的前端框架**: 使用相同的 API 接口（HTTP/WebSocket）

## API接口

- HTTP REST API: `http://127.0.0.1:8765/api/`
- WebSocket: `ws://127.0.0.1:8765/ws`

详细API文档请参考 [docs/ARCHITECTURE_API.md](docs/ARCHITECTURE_API.md)
