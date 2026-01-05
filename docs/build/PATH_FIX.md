# MindVoice 构建路径问题修复说明

## 问题描述

在构建过程中发现两个路径问题：

### 问题 1: 输出路径错误

**症状**: 安装包输出到了 `/Users/wangjunhui/playcode/release/` 而不是项目目录下的 `release/`

**原因**: `electron-builder.json` 中的相对路径 `../../release/latest` 从 `electron-app/` 目录解析时，会跳到父目录的父目录

**解决方案**: 
```json
{
  "directories": {
    "output": "../release/latest"  // 改为一个 ../
  }
}
```

### 问题 2: .gitignore 不完整

**问题**: `electron-app/build/` 目录（包含复制的资源）未被忽略

**解决方案**: 已添加到 `.gitignore`:
```
electron-app/build/  # 构建时复制的资源文件
```

## 修复步骤

### 1. 更新 electron-builder 配置

**文件**: `build/config/electron-builder.json`

```json
{
  "directories": {
    "output": "../release/latest",  // 修改：从 ../../ 改为 ../
    "buildResources": "build"
  }
}
```

### 2. 更新构建脚本

**文件**: `scripts/build/build-macos.sh`

在 `build_electron_frontend()` 函数中添加：

```bash
# 复制构建资源到 electron-app/build
log_info "准备构建资源..."
mkdir -p build
cp -r "$BUILD_DIR/resources/"* build/ 2>/dev/null || true
```

### 3. 更新 .gitignore

已添加：
```
electron-app/build/  # 构建时复制的资源文件
```

## 验证

构建后检查文件位置：

```bash
# 应该在这里：
ls -lh 语音桌面助手/release/latest/*.dmg

# 而不是这里：
ls -lh /Users/wangjunhui/playcode/release/
```

## 清理旧文件

```bash
# 删除错误位置的文件（如果已经移动）
rm -rf /Users/wangjunhui/playcode/release/

# 确认正确位置有文件
ls -lh 语音桌面助手/release/latest/
```

## 状态

- [x] 识别问题
- [x] 更新 .gitignore
- [x] 移动现有文件到正确位置
- [ ] 更新 electron-builder.json（需要测试）
- [x] 更新构建脚本
- [ ] 重新构建验证

## 后续测试

重新执行完整构建验证路径正确：

```bash
./scripts/build/clean.sh
./scripts/build/build-macos.sh
```

检查输出：
```bash
ls -lh release/latest/
```

---

**修复日期**: 2026-01-05  
**修复人**: AI Assistant  
**状态**: 部分完成（等待测试验证）

