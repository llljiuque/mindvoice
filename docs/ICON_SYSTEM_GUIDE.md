# 图标系统使用指南

**MindVoice 项目统一图标管理方案**

## 📚 概述

MindVoice 使用统一的 Icon 组件管理所有图标，提供类型安全、易用的图标使用方式。

## 🚀 快速开始

### 基础使用

```tsx
import { Icon } from '@/components/shared/Icon';

// 最简单的用法
<Icon name="mic" />

// 自定义大小和颜色
<Icon name="mic" size={32} color="#1890ff" />

// 可点击图标
<Icon name="copy" onClick={handleCopy} title="复制" />
```

## 📖 完整 API

### IconProps

```typescript
interface IconProps {
  name: IconName;           // 必需，图标名称
  size?: number;            // 可选，默认 24px
  color?: string;           // 可选，默认 currentColor
  className?: string;       // 可选，自定义类名
  onClick?: (e) => void;    // 可选，点击事件
  title?: string;           // 可选，悬停提示
  disabled?: boolean;       // 可选，禁用状态
}
```

### 可用图标

| 图标名称 | 用途 | 示例 |
|---------|------|------|
| `mic` | 麦克风/语音输入 | `<Icon name="mic" />` |
| `camera` | 相机/拍照 | `<Icon name="camera" />` |
| `copy` | 复制 | `<Icon name="copy" />` |
| `translate` | 翻译 | `<Icon name="translate" />` |
| `report` | 报告 | `<Icon name="report" />` |
| `app` | 应用图标 | `<Icon name="app" />` |

## 🎨 使用示例

### 1. 在按钮中使用

```tsx
function VoiceButton() {
  return (
    <button className="voice-button">
      <Icon name="mic" size={20} />
      <span>开始录音</span>
    </button>
  );
}
```

### 2. 工具栏图标

```tsx
function Toolbar() {
  return (
    <div className="toolbar">
      <Icon name="mic" size={24} onClick={handleMic} />
      <Icon name="camera" size={24} onClick={handleCamera} />
      <Icon name="copy" size={24} onClick={handleCopy} />
    </div>
  );
}
```

### 3. 动态颜色

```tsx
function StatusIcon({ isActive }: { isActive: boolean }) {
  return (
    <Icon 
      name="mic" 
      color={isActive ? '#52c41a' : '#999'}
      size={24}
    />
  );
}
```

### 4. 禁用状态

```tsx
function ActionButton({ disabled }: { disabled: boolean }) {
  return (
    <Icon 
      name="copy" 
      disabled={disabled}
      onClick={handleCopy}
    />
  );
}
```

## 🔧 添加新图标

### 步骤 1: 准备 SVG 文件

确保 SVG 文件符合规范：

```svg
<!-- ✅ 正确的 SVG -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <path fill="currentColor" d="..." />
</svg>

<!-- ❌ 错误的 SVG -->
<svg width="512" height="512">
  <path fill="#000000" d="..." />
</svg>
```

**要求**:
- 使用 `currentColor` 作为颜色值
- 移除固定的 `width` 和 `height`
- 使用 `viewBox` 定义画布大小
- 优化文件大小（使用 SVGO）

### 步骤 2: 添加文件

```bash
# 将 SVG 文件放到 ui/ 目录
cp my-icon.svg electron-app/src/assets/icons/ui/
```

### 步骤 3: 注册图标

编辑 `src/components/shared/Icon/iconRegistry.ts`：

```typescript
// 1. 导入图标（注意 ?react 后缀）
import MyIcon from '@/assets/icons/ui/my-icon.svg?react';

// 2. 添加到 iconMap
export const iconMap = {
  // ...existing icons
  'my-icon': MyIcon,  // 添加这一行
} as const;
```

### 步骤 4: 使用新图标

```tsx
<Icon name="my-icon" size={24} />
```

TypeScript 会自动提供类型提示！

## 🎯 主题适配

### 跟随文本颜色

```tsx
<div style={{ color: '#1890ff' }}>
  <Icon name="mic" />  {/* 自动使用蓝色 */}
  <span>录音中</span>
</div>
```

### 使用 CSS 变量

```tsx
<Icon name="mic" color="var(--primary-color)" />
```

```css
:root {
  --primary-color: #1890ff;
}

.dark-theme {
  --primary-color: #40a9ff;
}
```

### 动态主题

```tsx
function ThemedIcon() {
  const isDark = useTheme();
  
  return (
    <Icon 
      name="mic" 
      color={isDark ? '#fff' : '#333'}
    />
  );
}
```

## 📏 尺寸规范

| 场景 | 推荐尺寸 | 示例 |
|------|---------|------|
| 小图标 | 16px | 内联文本中 |
| 默认 | 24px | 按钮、列表项 |
| 中等 | 32px | 工具栏 |
| 大图标 | 48px+ | 空状态、引导页 |

```tsx
<Icon name="mic" size={16} />  {/* 小 */}
<Icon name="mic" size={24} />  {/* 默认 */}
<Icon name="mic" size={32} />  {/* 中 */}
<Icon name="mic" size={48} />  {/* 大 */}
```

## ⚠️ 注意事项

### ✅ 应该做的

1. **使用 Icon 组件**
   ```tsx
   <Icon name="mic" size={24} />
   ```

2. **利用类型提示**
   ```tsx
   import { IconName } from '@/components/shared/Icon';
   const iconName: IconName = 'mic';
   ```

3. **使用语义化颜色**
   ```tsx
   <Icon name="mic" color="var(--primary-color)" />
   ```

4. **提供无障碍支持**
   ```tsx
   <Icon name="copy" onClick={...} title="复制到剪贴板" />
   ```

### ❌ 不应该做的

1. **直接使用 img 标签**
   ```tsx
   ❌ <img src="/icons/mic.svg" />
   ```

2. **硬编码路径**
   ```tsx
   ❌ import icon from '@/assets/icons/ui/mic.svg';
   ```

3. **使用内联样式**
   ```tsx
   ❌ <Icon name="mic" style={{ ... }} />
   ```

4. **忽略类型检查**
   ```tsx
   ❌ <Icon name={"wrong" as any} />
   ```

## 🐛 常见问题

### Q: 图标不显示？

**检查**:
1. 图标名称拼写是否正确
2. 图标是否已在 `iconRegistry.ts` 中注册
3. 查看浏览器控制台错误信息

### Q: 颜色无法改变？

**原因**: SVG 文件未使用 `currentColor`

**解决**:
```svg
<!-- 将固定颜色 -->
<path fill="#000000" />

<!-- 改为 -->
<path fill="currentColor" />
```

### Q: TypeScript 报错？

**解决**:
1. 重启 TypeScript 服务器（VSCode: Cmd+Shift+P → "TypeScript: Restart TS Server"）
2. 确认 `vite-env.d.ts` 包含 SVG 类型声明
3. 检查导入是否使用 `?react` 后缀

### Q: 图标太大/太小？

**解决**: 使用 `size` 属性调整
```tsx
<Icon name="mic" size={16} />  {/* 调整为 16px */}
```

## 📚 更多资源

- **[Icon 组件 README](../electron-app/src/components/shared/Icon/README.md)** - 详细文档
- **[图标资源说明](../electron-app/src/assets/icons/README.md)** - 资源管理

## 🎉 开始使用

现在你可以在项目中自由使用图标了！

```tsx
import { Icon } from '@/components/shared/Icon';

function MyComponent() {
  return (
    <div>
      <Icon name="mic" size={24} color="#1890ff" />
      <span>欢迎使用统一图标系统！</span>
    </div>
  );
}
```

Happy coding! 🚀

