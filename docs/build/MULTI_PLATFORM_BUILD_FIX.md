# 多平台构建冲突问题修复

**修复日期**: 2026-01-05  
**问题**: macOS 和 Windows 打包脚本在操作 `release/latest` 目录时存在冲突

---

## 🔍 问题分析

### 冲突场景

两个脚本都操作同一个 `release/latest` 目录：

1. **macOS 脚本** (`build-macos.sh`)
   - `clean_build()`: 删除整个 `release/latest` 目录 ❌
   - `post_build()`: 清理 macOS 中间文件

2. **Windows 脚本** (`build-windows.sh`)
   - `clean_build()`: 删除整个 `release/latest` 目录 ❌
   - `post_build()`: 清理 Windows 中间文件

### 冲突后果

- 如果先构建 macOS，再构建 Windows → Windows 脚本会删除 macOS 安装包
- 如果先构建 Windows，再构建 macOS → macOS 脚本会删除 Windows 安装包
- 无法同时保留两个平台的安装包

---

## ✅ 修复方案

### 1. 修改 `clean_build()` 函数

**原则**: 只清理当前平台的产物，保留其他平台的文件

#### macOS 脚本

```bash
clean_build() {
    # 清理 Python 和 Electron 构建文件（共享）
    rm -rf "$PYTHON_BACKEND_DIR/dist"
    rm -rf "$PYTHON_BACKEND_DIR/build"
    rm -rf "$ELECTRON_DIR/dist"
    rm -rf "$ELECTRON_DIR/dist-electron"
    
    # 只清理 macOS 相关的构建产物
    rm -rf "$RELEASE_DIR/latest/mac"
    rm -rf "$RELEASE_DIR/latest/mac-arm64"
    rm -f "$RELEASE_DIR/latest"/*-mac-*.dmg
    rm -f "$RELEASE_DIR/latest"/*-mac-*.zip
    rm -f "$RELEASE_DIR/latest"/*-mac-*.blockmap
    # 保留 Windows 文件 ✅
}
```

#### Windows 脚本

```bash
clean_build() {
    # 清理 Python 和 Electron 构建文件（共享）
    rm -rf "$PYTHON_BACKEND_DIR/dist"
    rm -rf "$PYTHON_BACKEND_DIR/build"
    rm -rf "$ELECTRON_DIR/dist"
    rm -rf "$ELECTRON_DIR/dist-electron"
    
    # 只清理 Windows 相关的构建产物
    rm -rf "$RELEASE_DIR/latest/win"
    rm -rf "$RELEASE_DIR/latest/win-unpacked"
    rm -f "$RELEASE_DIR/latest"/*-windows-*.exe
    rm -f "$RELEASE_DIR/latest"/*-windows-*.zip
    rm -f "$RELEASE_DIR/latest"/*-windows-*.blockmap
    # 保留 macOS 文件 ✅
}
```

### 2. 优化 `post_build()` 函数

使用平台特定的文件模式，避免误删其他平台文件：

#### macOS

```bash
# 只匹配 macOS 文件
rm -f "$RELEASE_DIR/latest"/*-mac-*.blockmap
rm -f "$RELEASE_DIR/latest"/*-mac-*.zip
```

#### Windows

```bash
# 只匹配 Windows 文件
rm -f "$RELEASE_DIR/latest"/*-windows-*.blockmap
rm -f "$RELEASE_DIR/latest"/*-windows-*.zip
```

---

## 📦 修复后的目录结构

```
release/latest/
├── MindVoice-1.7.0-mac-arm64.dmg           ✅ macOS
├── MindVoice-1.7.0-mac-arm64.dmg.sha256
├── MindVoice-1.7.0-windows-x64.exe         ✅ Windows
├── MindVoice-1.7.0-windows-x64.exe.sha256
└── builder-effective-config.yaml           (共享，保留)
```

两个平台的安装包可以**共存**！

---

## 🎯 清理逻辑对比

### 修复前 ❌

| 操作 | macOS 脚本 | Windows 脚本 | 结果 |
|------|-----------|-------------|------|
| `clean_build()` | 删除整个 `release/latest` | 删除整个 `release/latest` | 互相删除 |
| `post_build()` | 清理 `*.blockmap`, `*.zip` | 清理 `*.blockmap`, `*.zip` | 可能误删 |

### 修复后 ✅

| 操作 | macOS 脚本 | Windows 脚本 | 结果 |
|------|-----------|-------------|------|
| `clean_build()` | 只清理 `*-mac-*` 文件 | 只清理 `*-windows-*` 文件 | 互不干扰 |
| `post_build()` | 只清理 `*-mac-*` 文件 | 只清理 `*-windows-*` 文件 | 互不干扰 |

---

## 🚀 使用场景

### 场景 1: 分别构建

```bash
# macOS 上构建
./scripts/build/build-macos.sh

# Windows 上构建（或通过 CI）
./scripts/build/build-windows.sh

# 两个安装包都保留在 release/latest/
```

### 场景 2: CI/CD 多平台构建

```yaml
# GitHub Actions 示例
jobs:
  build-macos:
    runs-on: macos-latest
    steps:
      - run: ./scripts/build/build-macos.sh
      - uses: actions/upload-artifact@v3
        with:
          name: macos-installer
          path: release/latest/*-mac-*.dmg

  build-windows:
    runs-on: windows-latest
    steps:
      - run: ./scripts/build/build-windows.sh
      - uses: actions/upload-artifact@v3
        with:
          name: windows-installer
          path: release/latest/*-windows-*.exe
```

---

## ⚠️ 注意事项

### 共享文件

以下文件是**共享**的，不会被删除：

- `builder-effective-config.yaml` - electron-builder 配置
- `builder-debug.yml` - 调试配置

### 文件命名规范

确保文件命名遵循平台规范：

- **macOS**: `MindVoice-{version}-mac-{arch}.{ext}`
- **Windows**: `MindVoice-{version}-windows-{arch}.{ext}`
- **Linux**: `MindVoice-{version}-linux-{arch}.{ext}`

这样清理逻辑才能正确识别。

---

## ✅ 验证

### 测试多平台构建

```bash
# 1. 构建 macOS
./scripts/build/build-macos.sh
ls -lh release/latest/*-mac-*.dmg

# 2. 构建 Windows（在 Windows 机器上）
./scripts/build/build-windows.sh
ls -lh release/latest/*-windows-*.exe

# 3. 验证两个平台文件都存在
ls -lh release/latest/
```

---

## 📝 相关文件

- `scripts/build/build-macos.sh` - macOS 构建脚本
- `scripts/build/build-windows.sh` - Windows 构建脚本
- `build/config/electron-builder.json` - 打包配置

---

**修复完成时间**: 2026-01-05  
**状态**: ✅ 完成  
**测试**: 建议在不同平台分别测试构建

