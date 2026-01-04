# MindVoice 构建系统 README

## 🎯 快速开始

### 一键构建
```bash
./scripts/build/build-macos.sh
```

### 清理构建
```bash
./scripts/build/clean.sh
```

---

## 📚 文档

完整的构建文档位于 `docs/build/` 目录：

- **[BUILD_GUIDE.md](BUILD_GUIDE.md)** - 完整构建指南
  - 前置要求
  - 详细构建步骤
  - 构建产物说明

- **[PACKAGING.md](PACKAGING.md)** - 打包配置详解
  - Electron Builder 配置
  - PyInstaller 配置
  - 自定义打包选项

- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - 故障排查
  - 常见问题解决
  - 调试技巧
  - 性能优化

---

## 📁 构建系统结构

```
build/
├── config/                          # 构建配置
│   ├── electron-builder.json       # Electron 打包配置
│   └── pyinstaller.spec            # Python 打包配置
├── resources/                       # 构建资源
│   ├── icons/                      # 应用图标（自动生成）
│   ├── installer/                  # 安装器资源
│   └── entitlements/               # macOS 权限配置
└── scripts/                         # 构建脚本（已弃用，使用 ../scripts/build/）

scripts/build/                       # 实际构建脚本位置
├── build-macos.sh                  # macOS 主构建脚本
├── prepare-icons.sh                # 图标准备脚本
└── clean.sh                        # 清理脚本

release/                            # 构建产物（自动生成）
└── latest/
    ├── *.dmg                       # macOS 安装包
    ├── *.zip                       # 压缩包
    └── *.sha256                    # 校验和

python-backend/                     # Python 打包产物（自动生成）
├── dist/
│   └── mindvoice-api              # 打包后的可执行文件
└── build/                          # 临时构建文件
```

---

## ⚡ 构建流程

### 完整构建
```bash
./scripts/build/build-macos.sh
```

自动执行：
1. 环境检查
2. 清理旧文件
3. 打包 Python 后端
4. 构建 Electron 前端
5. 打包应用
6. 生成校验和

### 分步构建

#### 1. 准备图标（仅首次）
```bash
./scripts/build/prepare-icons.sh
```

#### 2. 打包 Python 后端
```bash
source venv/bin/activate
pyinstaller build/config/pyinstaller.spec
```

#### 3. 构建 Electron 前端
```bash
cd electron-app
npm run build
cd ..
```

#### 4. 打包应用
```bash
cd electron-app
npx electron-builder --mac --config ../build/config/electron-builder.json
cd ..
```

---

## 🎓 配置修改

### 修改应用信息

编辑 `build/config/electron-builder.json`:
```json
{
  "appId": "com.mindvoice.app",
  "productName": "MindVoice",
  "copyright": "Copyright © 2026 ..."
}
```

### 添加 Python 模块

编辑 `build/config/pyinstaller.spec`:
```python
hiddenimports = [
    # 添加新模块
    'your_module',
]
```

### 修改权限

编辑 `build/resources/entitlements/mac.plist`

---

## 🔍 故障排查

### 常见问题

1. **Python 打包失败**
   - 检查虚拟环境：`source venv/bin/activate`
   - 查看日志：`python-backend/build/`

2. **Electron 构建失败**
   - 确认 dist/ 目录存在
   - 重新安装依赖：`cd electron-app && npm ci`

3. **找不到 Python 后端**
   - 先运行 Python 打包步骤
   - 验证：`ls -la python-backend/dist/mindvoice-api`

详细故障排查请查看 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

## 📦 构建产物

成功构建后：
```
release/latest/
├── MindVoice-1.4.1-mac-x64.dmg
├── MindVoice-1.4.1-mac-x64.dmg.sha256
├── MindVoice-1.4.1-mac-arm64.dmg
└── MindVoice-1.4.1-mac-arm64.dmg.sha256
```

---

## 🚀 CI/CD 集成

构建系统已为 CI/CD 做好准备：

```yaml
# GitHub Actions 示例
- name: Build macOS
  run: ./scripts/build/build-macos.sh

- name: Upload artifacts
  uses: actions/upload-artifact@v3
  with:
    name: macos-installers
    path: release/latest/*.dmg
```

---

## 📄 许可证

MIT License - 详见项目根目录 LICENSE 文件

---

**版本**: 1.0.0  
**最后更新**: 2026-01-04  
**维护者**: 深圳王哥 & AI

