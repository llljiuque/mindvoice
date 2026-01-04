# MindVoice 构建指南

## 📋 目录
- [前置要求](#前置要求)
- [快速开始](#快速开始)
- [详细构建流程](#详细构建流程)
- [构建产物](#构建产物)
- [故障排查](#故障排查)

---

## 🎯 前置要求

### 系统要求
- **macOS**: 10.14+ (Mojave)
- **Python**: 3.9+
- **Node.js**: 18+
- **Xcode Command Line Tools**: 已安装

### 检查环境
```bash
# 检查 Python
python3 --version  # 应该 >= 3.9

# 检查 Node.js
node --version     # 应该 >= 18.0

# 检查 Xcode Command Line Tools
xcode-select -p    # 应该输出路径
```

### 安装依赖

#### 1. Python 依赖
```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

#### 2. Node.js 依赖
```bash
cd electron-app
npm install
cd ..
```

#### 3. 构建工具
```bash
# 安装 PyInstaller
source venv/bin/activate
pip install pyinstaller
```

---

## 🚀 快速开始

### 一键构建（推荐）

```bash
# 构建 macOS 版本
./scripts/build/build-macos.sh
```

这个脚本会自动执行：
1. ✅ 环境检查
2. ✅ 清理旧文件
3. ✅ 打包 Python 后端
4. ✅ 构建 Electron 前端
5. ✅ 打包应用
6. ✅ 生成校验和

---

## 📖 详细构建流程

### 步骤 1：准备图标（仅首次）

```bash
./scripts/build/prepare-icons.sh
```

这会生成：
- `build/resources/icons/icon.icns` (macOS)
- `build/resources/icons/icon.ico` (Windows)
- `build/resources/icons/icon.png` (Linux)

### 步骤 2：清理旧构建（可选）

```bash
./scripts/build/clean.sh
```

### 步骤 3：打包 Python 后端

```bash
source venv/bin/activate
pyinstaller build/config/pyinstaller.spec \
    --distpath python-backend/dist \
    --workpath python-backend/build \
    --noconfirm
```

验证打包：
```bash
./python-backend/dist/mindvoice-api --help
```

### 步骤 4：构建 Electron 前端

```bash
cd electron-app

# 构建 Vite 前端
npm run build:vite

# 构建 Electron 主进程
npm run build:electron

cd ..
```

### 步骤 5：打包应用

```bash
cd electron-app
npx electron-builder \
    --mac \
    --config ../build/config/electron-builder.json \
    --publish never
cd ..
```

---

## 📦 构建产物

构建成功后，安装包位于：

```
release/latest/
├── MindVoice-1.4.1-mac-x64.dmg          # Intel Mac 安装包
├── MindVoice-1.4.1-mac-x64.dmg.sha256   # 校验和
├── MindVoice-1.4.1-mac-arm64.dmg        # Apple Silicon 安装包
├── MindVoice-1.4.1-mac-arm64.dmg.sha256 # 校验和
├── MindVoice-1.4.1-mac-x64.zip          # Intel Mac ZIP
└── MindVoice-1.4.1-mac-arm64.zip        # Apple Silicon ZIP
```

### 产物说明

| 文件类型 | 说明 | 用途 |
|---------|------|------|
| `.dmg` | 磁盘镜像 | macOS 标准安装包，推荐分发 |
| `.zip` | 压缩包 | 无需安装，解压即用 |
| `.sha256` | SHA256 校验和 | 验证文件完整性 |

---

## 🔧 故障排查

### Python 打包失败

**问题**：PyInstaller 报错找不到模块

**解决方案**：
```bash
# 1. 检查虚拟环境
source venv/bin/activate
pip list | grep <模块名>

# 2. 如果模块存在但仍失败，添加到 hiddenimports
# 编辑 build/config/pyinstaller.spec
# 在 hiddenimports 列表中添加该模块

# 3. 查看详细日志
pyinstaller build/config/pyinstaller.spec --log-level DEBUG
```

**常见问题**：
- `litellm` 相关错误：确保所有子模块都在 `hiddenimports` 中
- `chromadb` 相关错误：可能需要添加数据文件到 `datas`
- 运行时错误：检查 `python-backend/build/` 目录的日志

---

### Electron 打包失败

**问题**：electron-builder 报错

**解决方案**：
```bash
# 1. 检查前端是否构建成功
ls -la electron-app/dist
ls -la electron-app/dist-electron

# 2. 检查 Python 后端是否存在
ls -la python-backend/dist/mindvoice-api

# 3. 清理 node_modules 重新安装
cd electron-app
rm -rf node_modules package-lock.json
npm install
cd ..

# 4. 查看详细日志
cd electron-app
DEBUG=electron-builder npx electron-builder --mac
```

**常见问题**：
- 找不到 Python 后端：先运行 Python 打包步骤
- 路径错误：检查 `electron-builder.json` 中的相对路径
- 权限错误：确保 `entitlements` 文件存在

---

### 图标问题

**问题**：图标未正确显示

**解决方案**：
```bash
# 重新生成图标
./scripts/build/prepare-icons.sh

# 检查图标文件
ls -lh build/resources/icons/
```

---

### 权限错误

**问题**：macOS 安装后无法录音

**解决方案**：
1. 检查 `build/resources/entitlements/mac.plist` 是否包含麦克风权限
2. 首次启动时系统会提示授权，必须允许
3. 如果已拒绝，在"系统偏好设置 → 安全性与隐私 → 隐私 → 麦克风"中手动添加

---

### 打包体积过大

**问题**：安装包超过 500MB

**优化方案**：
```bash
# 1. 排除不需要的模块
# 编辑 build/config/pyinstaller.spec
# 在 excludes 列表中添加：
excludes=[
    'matplotlib',
    'PIL',
    'tkinter',
    'PyQt5',
    'pandas',
]

# 2. 启用 UPX 压缩（已启用）
# 确保 pyinstaller.spec 中 upx=True

# 3. 使用 maximum 压缩
# 已在 electron-builder.json 中设置 compression: "maximum"
```

---

## 🎓 高级选项

### 仅打包 Python 后端

```bash
source venv/bin/activate
pyinstaller build/config/pyinstaller.spec
```

### 仅构建 Electron 前端

```bash
cd electron-app
npm run build
```

### 构建但不打包

```bash
cd electron-app
npm run build
# 不运行 electron-builder
```

### 指定架构

```bash
# 仅构建 Intel 版本
npx electron-builder --mac --x64

# 仅构建 Apple Silicon 版本
npx electron-builder --mac --arm64
```

---

## 📊 构建时间估算

| 步骤 | 首次 | 增量 |
|------|------|------|
| Python 打包 | 5-10分钟 | 2-3分钟 |
| Electron 构建 | 2-3分钟 | 1分钟 |
| 应用打包 | 3-5分钟 | 2-3分钟 |
| **总计** | **10-18分钟** | **5-7分钟** |

---

## 🔗 相关文档

- [打包说明](PACKAGING.md) - 详细的打包配置说明
- [发布流程](RELEASE_PROCESS.md) - 如何发布新版本
- [故障排查](TROUBLESHOOTING.md) - 详细的故障排查指南

---

## 💡 提示

1. **首次构建较慢**：PyInstaller 需要分析所有依赖
2. **增量构建更快**：只修改前端代码时，无需重新打包 Python 后端
3. **使用 clean 脚本**：遇到奇怪问题时先清理再构建
4. **保存构建日志**：构建失败时日志很有用

---

**最后更新**: 2026-01-04  
**维护者**: 深圳王哥 & AI

