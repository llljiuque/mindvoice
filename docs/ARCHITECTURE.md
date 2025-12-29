# 架构设计文档

## 项目结构

```
语音桌面助手/
├── src/
│   ├── core/                     # 核心模块
│   │   ├── base.py              # 抽象基类定义
│   │   ├── config.py            # 配置管理
│   │   └── plugin_manager.py    # 插件管理器
│   ├── providers/                # 提供商实现
│   │   ├── asr/                 # ASR 提供商
│   │   │   ├── volcano.py       # 火山引擎 ASR
│   │   │   └── example.py      # 示例 ASR
│   │   └── storage/             # 存储提供商
│   │       └── sqlite.py        # SQLite 存储
│   ├── services/                 # 服务层
│   │   └── voice_service.py     # 语音服务（整合录音、ASR、存储）
│   ├── api/                      # API 服务层
│   │   └── server.py            # FastAPI 服务器
│   └── utils/                    # 工具模块
│       └── audio_recorder.py     # 音频录制器
├── electron-app/                 # Electron前端
│   ├── electron/                # 主进程代码
│   ├── src/                     # React前端代码
│   └── package.json             # Node.js依赖
├── api_server.py                 # API服务器入口
├── requirements.txt              # Python依赖列表
├── config.yml.example           # 配置示例
└── README.md                     # 项目说明
```

## 核心设计原则

### 1. 前后端分离

- **后端**: Python API服务器（FastAPI）
- **前端**: Electron + React
- **通信**: HTTP REST API + WebSocket

### 2. 可扩展性

- **抽象基类**: 使用 ABC 定义接口，所有提供商必须实现这些接口
- **插件系统**: 通过 `PluginManager` 动态加载和注册提供商
- **配置驱动**: 通过配置文件和环境变量管理不同提供商的配置

### 3. 模块化

- **分层架构**: 
  - Core: 核心抽象和基础设施
  - Providers: 提供商实现（ASR、存储）
  - Services: 业务逻辑封装
  - API: HTTP/WebSocket接口
  - Utils: 工具函数

## API架构

详见 [ARCHITECTURE_API.md](ARCHITECTURE_API.md)

## 扩展开发

### 添加新的 ASR 提供商

1. 在 `src/providers/asr/` 下创建新文件
2. 继承 `ASRProvider` 并实现所有方法
3. 在 `src/api/server.py` 中加载：`plugin_manager.load_plugin_module('src.providers.asr.your_provider')`

### 添加新的存储提供商

1. 在 `src/providers/storage/` 下创建新文件
2. 继承 `StorageProvider` 并实现所有方法
3. 在配置中设置 `storage.provider` 为你的提供商名称

### 替换前端框架

由于采用前后端分离架构，可以轻松替换前端：
- 使用相同的 API 接口（HTTP/WebSocket）
- 修改前端代码即可
- 后端代码无需改动
