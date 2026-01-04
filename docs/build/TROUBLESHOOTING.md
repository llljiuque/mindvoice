# MindVoice 构建故障排查指南

## 📋 常见问题索引

- [Python 后端打包问题](#python-后端打包问题)
- [Electron 前端构建问题](#electron-前端构建问题)
- [权限和签名问题](#权限和签名问题)
- [运行时问题](#运行时问题)
- [性能和体积问题](#性能和体积问题)

---

## 🐍 Python 后端打包问题

### 问题 1: ModuleNotFoundError

**症状**：
```
ImportError: No module named 'xxx'
ModuleNotFoundError: No module named 'xxx'
```

**原因**：模块被动态导入，PyInstaller 无法自动检测

**解决方案**：
```bash
# 1. 确认模块已安装
source venv/bin/activate
pip show <模块名>

# 2. 添加到 hiddenimports
# 编辑 build/config/pyinstaller.spec
hiddenimports = [
    # ... 现有模块
    'xxx',  # 添加缺失的模块
    'xxx.submodule',  # 如果有子模块
]

# 3. 重新打包
pyinstaller build/config/pyinstaller.spec --noconfirm
```

---

### 问题 2: 打包后可执行文件无法运行

**症状**：
```bash
./python-backend/dist/mindvoice-api
# 没有输出或立即退出
```

**诊断步骤**：
```bash
# 1. 检查文件权限
ls -l python-backend/dist/mindvoice-api
chmod +x python-backend/dist/mindvoice-api  # 如果需要

# 2. 查看详细错误
./python-backend/dist/mindvoice-api --help

# 3. 使用控制台模式查看错误
# 在 pyinstaller.spec 中设置 console=True（已设置）
```

**常见原因**：
- ✅ 缺少必需模块（添加到 hiddenimports）
- ✅ 缺少数据文件（添加到 datas）
- ✅ 依赖系统库未安装

---

### 问题 3: 打包体积过大

**症状**：`mindvoice-api` 超过 200MB

**优化方案**：

#### 方法 1: 排除不需要的模块
编辑 `build/config/pyinstaller.spec`:
```python
excludes = [
    'matplotlib',
    'matplotlib.backends',
    'PIL',
    'tkinter',
    'PyQt5',
    'pandas',
    'scipy',
    'jupyter',
    'notebook',
]
```

#### 方法 2: 使用 UPX 压缩
```python
exe = EXE(
    # ...
    upx=True,  # 已启用
    upx_exclude=[],  # 不排除任何文件
)
```

安装 UPX:
```bash
brew install upx
```

#### 方法 3: 优化依赖
```bash
# 使用轻量级替代品
# 例如：用 orjson 替代 json（如果适用）
```

---

### 问题 4: chromadb 相关错误

**症状**：
```
sqlite3.OperationalError: unable to open database file
```

**解决方案**：
```python
# 在 pyinstaller.spec 中添加
datas = [
    ('config.yml.example', '.'),
    # 如果需要，添加 chromadb 数据目录
]

# 或在代码中设置数据目录为用户目录
```

---

## ⚡ Electron 前端构建问题

### 问题 1: 找不到 dist 目录

**症状**：
```
Error: Cannot find module './dist/index.html'
```

**解决方案**：
```bash
# 1. 确保前端已构建
cd electron-app
npm run build:vite
ls -la dist/  # 应该看到 index.html 和资源文件

# 2. 检查 vite.config.ts 输出目录
# 确认 build.outDir 是 'dist'
```

---

### 问题 2: Electron 主进程未编译

**症状**：
```
Error: Cannot find module 'dist-electron/main.js'
```

**解决方案**：
```bash
cd electron-app
npm run build:electron
ls -la dist-electron/  # 应该看到 main.js 和 preload.js

# 如果失败，检查 TypeScript 错误
npx tsc -p electron --noEmit  # 只检查不输出
```

---

### 问题 3: electron-builder 找不到 Python 后端

**症状**：
```
Error: file python-backend/dist/mindvoice-api not found
```

**解决方案**：
```bash
# 1. 确认 Python 后端已打包
ls -la python-backend/dist/mindvoice-api

# 2. 检查 electron-builder.json 路径
# extraResources[0].from 应该指向正确位置
{
  "from": "../../python-backend/dist/",
  "to": "python-backend/"
}

# 3. 注意工作目录
# electron-builder 从 electron-app 目录运行
# 所以需要 ../.. 回到项目根目录
```

---

### 问题 4: node_modules 问题

**症状**：构建卡住或失败

**解决方案**：
```bash
cd electron-app

# 清理并重新安装
rm -rf node_modules package-lock.json
npm cache clean --force
npm install

# 如果问题持续，尝试
npm ci  # 使用 package-lock.json 精确版本
```

---

## 🔐 权限和签名问题

### 问题 1: 麦克风权限未生效

**症状**：安装后无法使用麦克风

**解决方案**：

#### 1. 检查 entitlements 文件
`build/resources/entitlements/mac.plist` 必须包含：
```xml
<key>com.apple.security.device.audio-input</key>
<true/>
```

#### 2. 检查 Info.plist
应用应该自动生成请求麦克风权限的提示。

#### 3. 手动授权
```
系统偏好设置 → 安全性与隐私 → 隐私 → 麦克风
找到 MindVoice 并勾选
```

---

### 问题 2: "已损坏，无法打开"

**症状**：
```
"MindVoice.app" 已损坏，无法打开。您应该将它移到废纸篓。
```

**原因**：未签名或 Gatekeeper 阻止

**临时解决方案**（用户侧）：
```bash
# 方法 1: 右键打开
# 右键点击应用 → 打开 → 打开

# 方法 2: 移除隔离属性
xattr -cr /Applications/MindVoice.app

# 方法 3: 绕过 Gatekeeper
sudo spctl --master-disable  # 不推荐
```

**永久解决方案**（开发者）：

#### 1. 代码签名
```bash
# 需要 Apple Developer 账号 ($99/年)
codesign --deep --force --verify --verbose \
  --sign "Developer ID Application: Your Name" \
  MindVoice.app
```

#### 2. 公证 (Notarization)
```bash
# 打包为 DMG
# 提交公证
xcrun notarytool submit MindVoice.dmg \
  --apple-id your@email.com \
  --team-id TEAMID \
  --password app-specific-password

# 等待结果（通常 5-15 分钟）
xcrun notarytool wait <submission-id> \
  --apple-id your@email.com \
  --team-id TEAMID

# 订书钉（Staple）
xcrun stapler staple MindVoice.dmg
```

---

### 问题 3: Python 后端无法执行

**症状**：
```
dyld: Library not loaded
```

**解决方案**：

确保 entitlements 包含：
```xml
<key>com.apple.security.cs.allow-unsigned-executable-memory</key>
<true/>
<key>com.apple.security.cs.disable-library-validation</key>
<true/>
```

---

## 🚀 运行时问题

### 问题 1: Python 后端启动失败

**诊断**：查看日志
```bash
# 启动应用时查看控制台
# macOS: Console.app
# 搜索 "MindVoice" 或 "Electron"
```

**常见原因**：
1. **端口被占用**
   ```bash
   lsof -ti :8765  # 查看占用进程
   kill -9 $(lsof -ti :8765)  # 终止进程
   ```

2. **配置文件缺失**
   - 首次启动应显示配置向导
   - 或手动创建 `~/Library/Application Support/MindVoice/config.yml`

3. **模型文件未下载**
   - Embedding 模型需要从 HuggingFace 下载
   - 检查网络连接

---

### 问题 2: 前后端通信失败

**症状**：前端显示"连接失败"

**诊断步骤**：
```bash
# 1. 检查后端是否运行
ps aux | grep mindvoice-api

# 2. 检查端口
lsof -i :8765

# 3. 测试 API
curl http://localhost:8765/api/status
```

**解决方案**：
- 确保防火墙未阻止本地连接
- 检查 Electron 主进程日志

---

## 📊 性能和体积问题

### 问题 1: 安装包超过 500MB

**诊断**：
```bash
# 查看各部分大小
du -sh release/latest/MindVoice.app
du -sh release/latest/MindVoice.app/Contents/Resources/python-backend
```

**优化**：参见上面的"打包体积过大"部分

---

### 问题 2: 启动缓慢

**原因**：首次启动需要加载模型

**优化方案**：
1. 添加启动画面显示加载进度
2. 模型懒加载（使用时才加载）
3. 使用更小的模型

---

## 🔧 调试技巧

### 启用详细日志

#### Electron
```javascript
// 在 main.ts 中
if (!app.isPackaged) {
  console.log('开发模式');
} else {
  console.log('生产模式');
}
```

#### Python
```python
# 在 api_server.py 中
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 查看打包内容

```bash
# macOS
open -a "Show Package Contents" MindVoice.app

# 查看文件列表
find MindVoice.app -type f
```

### 测试打包但不分发

```bash
# 构建应用但不创建 DMG
npx electron-builder --mac --dir

# 输出在 electron-app/dist/mac/
```

---

## 📞 获取帮助

如果以上方法都无法解决问题：

1. **查看日志**
   - macOS Console.app
   - `~/Library/Logs/MindVoice/`

2. **检查 GitHub Issues**
   - 搜索类似问题

3. **提交 Issue**
   - 包含完整错误信息
   - 系统版本
   - 构建日志

---

**最后更新**: 2026-01-04  
**维护者**: 深圳王哥 & AI

