# Icon 组件使用文档

统一的图标组件系统，提供类型安全的图标使用方式。

## 📚 特性

- ✅ **类型安全**: 完整的 TypeScript 类型支持
- ✅ **动态颜色**: 支持自定义颜色和主题适配
- ✅ **可访问性**: 支持键盘导航和屏幕阅读器
- ✅ **高性能**: SVG 组件化，无需额外 HTTP 请求
- ✅ **易扩展**: 简单的图标注册机制

## 🚀 快速开始

### 基础使用

```tsx
import { Icon } from '@/components/shared/Icon';

function MyComponent() {
  return (
    <div>
      {/* 基础图标 */}
      <Icon name="mic" />
      
      {/* 自定义大小 */}
      <Icon name="camera" size={32} />
      
      {/* 自定义颜色 */}
      <Icon name="copy" color="#1890ff" />
      
      {/* 组合使用 */}
      <Icon name="translate" size={24} color="var(--primary-color)" />
    </div>
  );
}
```

### 可点击图标

```tsx
function Toolbar() {
  const handleCopy = () => {
    navigator.clipboard.writeText('...');
  };

  return (
    <Icon 
      name="copy" 
      onClick={handleCopy}
      title="复制到剪贴板"
      size={20}
    />
  );
}
```

### 禁用状态

```tsx
<Icon 
  name="mic" 
  disabled={!isRecording}
  onClick={handleMicClick}
/>
```

### 在按钮中使用

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

## 📖 API 文档

### IconProps

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | `IconName` | **必需** | 图标名称，必须在 iconRegistry 中注册 |
| `size` | `number` | `24` | 图标大小（像素） |
| `color` | `string` | `'currentColor'` | 图标颜色，支持 CSS 颜色值 |
| `className` | `string` | `''` | 自定义类名 |
| `onClick` | `(e: MouseEvent) => void` | - | 点击事件处理函数 |
| `title` | `string` | - | 鼠标悬停提示 |
| `disabled` | `boolean` | `false` | 是否禁用 |

### IconName 类型

所有可用的图标名称（自动生成类型提示）：

```typescript
type IconName = 
  | 'mic'
  | 'camera'
  | 'copy'
  | 'translate'
  | 'report'
  | 'app';
```

## 🎨 样式自定义

### 使用 className

```tsx
<Icon 
  name="mic" 
  className="my-custom-icon"
/>
```

```css
.my-custom-icon {
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));
  transition: transform 0.3s ease;
}

.my-custom-icon:hover {
  transform: rotate(15deg);
}
```

### 使用内联样式

虽然不推荐，但可以通过父容器控制：

```tsx
<span style={{ opacity: 0.5 }}>
  <Icon name="mic" />
</span>
```

## 🔧 添加新图标

### 步骤 1: 准备 SVG 文件

确保 SVG 文件符合规范：
- 使用 `currentColor` 作为填充/描边颜色
- 移除固定的 `width` 和 `height` 属性
- 优化文件大小（使用 SVGO）

```svg
<!-- ✅ 好的 SVG -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <path fill="currentColor" d="..." />
</svg>

<!-- ❌ 不好的 SVG -->
<svg width="512" height="512">
  <path fill="#000000" d="..." />
</svg>
```

### 步骤 2: 添加到 icons/ui/ 目录

```bash
cp my-icon.svg electron-app/src/assets/icons/ui/
```

### 步骤 3: 注册图标

编辑 `iconRegistry.ts`：

```typescript
// 1. 导入图标
import MyIcon from '@/assets/icons/ui/my-icon.svg?react';

// 2. 添加到 iconMap
export const iconMap = {
  // ...existing icons
  'my-icon': MyIcon,
} as const;
```

### 步骤 4: 使用新图标

```tsx
<Icon name="my-icon" />
```

TypeScript 会自动提供类型提示！

## 🌈 主题适配示例

### 跟随文本颜色

```tsx
<div style={{ color: '#1890ff' }}>
  <Icon name="mic" /> {/* 自动使用蓝色 */}
  录音中
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

### 动态主题切换

```tsx
function ThemedIcon() {
  const theme = useTheme();
  
  return (
    <Icon 
      name="mic" 
      color={theme.primaryColor}
    />
  );
}
```

## 📊 可用图标列表

当前已注册的图标：

| 图标 | 名称 | 用途 |
|------|------|------|
| 🎤 | `mic` | 麦克风/语音输入 |
| 📷 | `camera` | 相机/拍照 |
| 📋 | `copy` | 复制 |
| 🌐 | `translate` | 翻译 |
| 📊 | `report` | 报告 |
| 🔷 | `app` | 应用图标 |

查看所有可用图标：

```tsx
import { getAvailableIcons } from '@/components/shared/Icon';

const icons = getAvailableIcons();
console.log(icons); // ['mic', 'camera', 'copy', ...]
```

## ⚠️ 注意事项

### 不要直接导入 SVG

❌ **错误做法**:
```tsx
import micIcon from '@/assets/icons/ui/mic.svg';
<img src={micIcon} />
```

✅ **正确做法**:
```tsx
import { Icon } from '@/components/shared/Icon';
<Icon name="mic" />
```

### 避免在循环中使用内联事件

❌ **性能不佳**:
```tsx
{items.map(item => (
  <Icon name="copy" onClick={() => handleCopy(item.id)} />
))}
```

✅ **更好的做法**:
```tsx
{items.map(item => (
  <Icon 
    name="copy" 
    onClick={handleCopy}
    data-id={item.id}
  />
))}
```

## 🐛 常见问题

### Q: 图标显示不出来？

检查：
1. 图标名称是否正确（大小写敏感）
2. 图标是否已在 `iconRegistry.ts` 中注册
3. 浏览器控制台是否有警告信息

### Q: 图标颜色无法改变？

确保 SVG 文件中使用 `currentColor`：
```svg
<path fill="currentColor" />
```

### Q: TypeScript 类型提示不工作？

1. 重启 TypeScript 服务器
2. 检查 `vite-env.d.ts` 是否包含 SVG 类型声明
3. 确保使用 `?react` 后缀导入

### Q: 图标太大/太小？

使用 `size` 属性：
```tsx
<Icon name="mic" size={16} /> {/* 小号 */}
<Icon name="mic" size={24} /> {/* 默认 */}
<Icon name="mic" size={32} /> {/* 大号 */}
```

## 📚 相关资源

- [图标资源目录说明](../../../assets/icons/README.md)
- [使用指南](../../../../docs/ICON_SYSTEM_GUIDE.md)

## 🔗 外部资源

- [Iconify](https://iconify.design/) - 图标资源库
- [SVGO](https://github.com/svg/svgo) - SVG 优化工具
- [SVG on MDN](https://developer.mozilla.org/en-US/docs/Web/SVG) - SVG 文档

