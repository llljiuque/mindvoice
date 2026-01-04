# MindVoice 打包配置说明

## 📋 目录
- [配置文件概览](#配置文件概览)
- [Electron Builder 配置](#electron-builder-配置)
- [PyInstaller 配置](#pyinstaller-配置)
- [macOS 权限配置](#macos-权限配置)
- [自定义配置](#自定义配置)

---

## 📁 配置文件概览

```
build/
├── config/
│   ├── electron-builder.json    # Electron 打包配置
│   └── pyinstaller.spec         # Python 后端打包配置
└── resources/
    ├── entitlements/
    │   ├── mac.plist           # macOS 权限配置
    │   └── mac.inherit.plist   # 继承权限配置
    └── icons/
        ├── icon.icns           # macOS 图标
        ├── icon.ico            # Windows 图标
        └── icon.png            # Linux 图标
```

---

## ⚙️ Electron Builder 配置

### 配置文件位置
`build/config/electron-builder.json`

### 主要配置项

#### 基础配置
```json
{
  "appId": "com.mindvoice.app",        // 应用唯一标识
  "productName": "MindVoice",          // 产品名称
  "copyright": "Copyright © 2026 ...", // 版权信息
}
```

#### 目录配置
```json
{
  "directories": {
    "output": "../../release/latest",  // 输出目录
    "buildResources": "../resources"   // 构建资源目录
  }
}
```

#### 文件包含
```json
{
  "files": [
    "dist/**/*",           // Vite 构建输出
    "dist-electron/**/*",  // Electron 主进程
    "package.json"         // 包信息
  ]
}
```

#### 额外资源（重要）
```json
{
  "extraResources": [
    {
      "from": "../../python-backend/dist/",  // Python 后端
      "to": "python-backend/",
      "filter": ["**/*"]
    },
    {
      "from": "../../config.yml.example",    // 示例配置
      "to": "config/config.yml.example"
    }
  ]
}
```

#### macOS 特定配置
```json
{
  "mac": {
    "category": "public.app-category.productivity",
    "icon": "../resources/icons/icon.icns",
    "target": [
      {
        "target": "dmg",
        "arch": ["x64", "arm64"]  // 支持 Intel 和 Apple Silicon
      }
    ],
    "hardenedRuntime": true,      // 启用硬化运行时
    "gatekeeperAssess": false,    // 绕过 Gatekeeper 评估
    "entitlements": "...",        // 权限文件
    "minimumSystemVersion": "10.14.0"  // 最低系统版本
  }
}
```

### 自定义安装包名称

修改 `artifactName`：
```json
{
  "mac": {
    "artifactName": "${productName}-${version}-mac-${arch}.${ext}"
  }
}
```

格式变量：
- `${productName}`: 产品名称
- `${version}`: 版本号
- `${arch}`: 架构 (x64, arm64)
- `${ext}`: 扩展名 (dmg, zip)

---

## 🐍 PyInstaller 配置

### 配置文件位置
`build/config/pyinstaller.spec`

### 关键配置

#### 隐藏导入（最重要）
```python
hiddenimports = [
    # 动态导入的模块必须显式声明
    'litellm',
    'litellm.llms',
    'chromadb',
    'sentence_transformers',
    # ... 更多
]
```

**添加新模块**：
1. 如果运行时报错 `ModuleNotFoundError`
2. 将模块名添加到 `hiddenimports` 列表
3. 重新运行 PyInstaller

#### 数据文件
```python
datas = [
    ('config.yml.example', '.'),  # 包含配置示例
]
```

#### 排除模块（优化体积）
```python
excludes = [
    'matplotlib',  # 不需要的大型库
    'PIL',
    'tkinter',
]
```

#### 可执行文件配置
```python
exe = EXE(
    # ...
    name='mindvoice-api',  # 输出文件名
    debug=False,           # 生产模式
    console=True,          # 保留控制台输出
    upx=True,             # 启用 UPX 压缩
)
```

---

## 🔐 macOS 权限配置

### 主权限文件
`build/resources/entitlements/mac.plist`

### 必需权限

#### 麦克风权限
```xml
<key>com.apple.security.device.audio-input</key>
<true/>
```

#### 网络权限
```xml
<key>com.apple.security.network.client</key>
<true/>
<key>com.apple.security.network.server</key>
<true/>
```

#### Python 后端权限
```xml
<!-- 允许执行动态代码 -->
<key>com.apple.security.cs.allow-unsigned-executable-memory</key>
<true/>

<!-- 允许 JIT 编译 -->
<key>com.apple.security.cs.allow-jit</key>
<true/>

<!-- 禁用库验证 -->
<key>com.apple.security.cs.disable-library-validation</key>
<true/>
```

### 继承权限文件
`build/resources/entitlements/mac.inherit.plist`

子进程（Python 后端）继承相同权限。

---

## 🎨 自定义配置

### 修改应用图标

1. **准备图标**：1024x1024 PNG 文件
2. **替换源文件**：`electron-app/assets/ico.png`
3. **重新生成**：
   ```bash
   ./scripts/build/prepare-icons.sh
   ```

### 修改 DMG 外观

编辑 `electron-builder.json`：
```json
{
  "dmg": {
    "title": "MindVoice ${version}",
    "background": "resources/installer/background.png",  // 自定义背景
    "window": {
      "width": 540,
      "height": 380
    },
    "contents": [
      {
        "x": 130,
        "y": 220  // 应用图标位置
      },
      {
        "x": 410,
        "y": 220,
        "type": "link",
        "path": "/Applications"  // 快捷方式位置
      }
    ]
  }
}
```

### 添加许可协议

1. **创建许可文件**：`build/resources/installer/license.txt`
2. **更新配置**：
   ```json
   {
     "dmg": {
       "license": "resources/installer/license.txt"
     }
   }
   ```

---

## 🔄 多平台配置

### Windows 配置

```json
{
  "win": {
    "target": [
      {
        "target": "nsis",  // NSIS 安装器
        "arch": ["x64", "ia32"]
      }
    ],
    "icon": "../resources/icons/icon.ico"
  },
  "nsis": {
    "oneClick": false,                           // 允许自定义安装
    "allowToChangeInstallationDirectory": true,  // 允许选择目录
    "createDesktopShortcut": true,              // 创建桌面快捷方式
    "createStartMenuShortcut": true             // 创建开始菜单快捷方式
  }
}
```

### Linux 配置

```json
{
  "linux": {
    "target": ["AppImage", "deb", "rpm"],
    "icon": "../resources/icons/icon.png",
    "category": "Utility"
  }
}
```

---

## 📝 配置最佳实践

### 1. 版本管理

使用单一版本来源：
```bash
# electron-app/src/version.ts
export const APP_VERSION = {
  version: '1.4.1',
  // ...
};
```

构建时自动从 `package.json` 读取版本号。

### 2. 环境变量

开发和生产环境分离：
```javascript
// 在 Electron 主进程中
const isProd = process.env.NODE_ENV === 'production';
const pythonPath = isProd 
  ? path.join(process.resourcesPath, 'python-backend', 'mindvoice-api')
  : path.join(__dirname, '../../api_server.py');
```

### 3. 路径管理

使用相对路径确保跨平台兼容：
```json
{
  "extraResources": [
    {
      "from": "../../python-backend/dist/",
      "to": "python-backend/"
    }
  ]
}
```

### 4. 压缩优化

启用最大压缩：
```json
{
  "compression": "maximum"
}
```

启用 UPX（PyInstaller）：
```python
exe = EXE(
    # ...
    upx=True,
)
```

---

## 🐛 调试配置

### 启用详细日志

Electron Builder:
```bash
DEBUG=electron-builder npx electron-builder --mac
```

PyInstaller:
```bash
pyinstaller build/config/pyinstaller.spec --log-level DEBUG
```

### 检查打包内容

macOS:
```bash
# 查看 app 内容
open -a "Show Package Contents" release/latest/MindVoice.app

# 查看资源
ls -la release/latest/MindVoice.app/Contents/Resources/
```

---

## 📚 参考资料

- [Electron Builder 文档](https://www.electron.build/)
- [PyInstaller 文档](https://pyinstaller.org/)
- [macOS Entitlements](https://developer.apple.com/documentation/bundleresources/entitlements)

---

**最后更新**: 2026-01-04  
**维护者**: 深圳王哥 & AI

