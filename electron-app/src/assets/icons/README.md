# 图标资源目录

本目录包含 MindVoice 项目的所有图标资源，按用途分类管理。

## 📁 目录结构

```
icons/
├── ui/              # UI 界面图标（SVG 格式）
│   ├── mic.svg      # 麦克风图标
│   ├── camera.svg   # 相机图标
│   ├── copy.svg     # 复制图标
│   ├── translate.svg # 翻译图标
│   ├── report.svg   # 报告图标
│   └── app-icon.svg # 应用图标
├── tray/            # 系统托盘图标（PNG 格式）
│   ├── default.png  # 默认状态
│   ├── recording.png # 录音状态
│   └── ...
└── app/             # 应用主图标（多格式）
    ├── icon.png     # 通用图标
    └── icon.svg     # 矢量图标
```

## 🎨 图标规范

### UI 图标（ui/）

**用途**: 应用界面中的功能按钮、工具栏图标等

**规范**:
- **格式**: SVG
- **尺寸**: 不限（矢量图，推荐 512x512 画布）
- **颜色**: 使用 `currentColor`，支持动态颜色
- **命名**: kebab-case（如 `mic.svg`，`user-profile.svg`）

**示例**:
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <path fill="currentColor" d="..." />
</svg>
```

### 托盘图标（tray/）

**用途**: macOS/Windows 系统托盘显示

**规范**:
- **格式**: PNG（支持透明）
- **尺寸**: 
  - macOS: 22x22 (标准), 44x44 (Retina)
  - Windows: 16x16, 32x32
- **颜色**: 根据系统主题调整
- **命名**: 描述状态（如 `recording.png`，`idle.png`）

### 应用图标（app/）

**用途**: 应用程序主图标（Dock/任务栏）

**规范**:
- **格式**: 
  - macOS: `.icns`（放在 `build/icons/`）
  - Windows: `.ico`（放在 `build/icons/`）
  - Linux: `.png`（多尺寸）
  - 源文件: `.svg`
- **尺寸**: 1024x1024（最大），包含多尺寸版本

## 🚀 使用方法

### 在代码中使用 UI 图标

**推荐方式** - 使用 Icon 组件:

```tsx
import { Icon } from '@/components/shared/Icon';

// 基础使用
<Icon name="mic" />

// 自定义大小和颜色
<Icon name="mic" size={32} color="#1890ff" />

// 可点击图标
<Icon name="copy" onClick={handleCopy} title="复制" />
```

### 添加新图标

1. **添加 SVG 文件**: 将图标放到 `ui/` 目录
   ```bash
   cp new-icon.svg src/assets/icons/ui/
   ```

2. **注册图标**: 编辑 `components/shared/Icon/iconRegistry.ts`
   ```typescript
   import NewIcon from '@/assets/icons/ui/new-icon.svg?react';
   
   export const iconMap = {
     // ...existing icons
     'new-icon': NewIcon,
   } as const;
   ```

3. **使用图标**: 在组件中使用
   ```tsx
   <Icon name="new-icon" />
   ```

## ⚠️ 注意事项

1. **不要直接使用路径**: 避免 `<img src="/icons/mic.svg" />`，请使用 Icon 组件
2. **保持命名一致**: 使用 kebab-case，语义化命名
3. **SVG 优化**: 添加前使用 SVGO 优化 SVG 文件
4. **颜色控制**: UI 图标使用 `currentColor`，便于主题切换
5. **文件大小**: SVG 文件尽量控制在 5KB 以内

## 🔧 SVG 优化工具

使用 SVGO 优化 SVG 文件：

```bash
npm install -g svgo
svgo input.svg -o output.svg
```

## 📚 更多资源

- [Icon 组件文档](../../components/shared/Icon/README.md)
- [使用指南](../../../docs/ICON_SYSTEM_GUIDE.md)

