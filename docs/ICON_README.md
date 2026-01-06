# 图标系统说明

## 📁 文档位置

本项目的图标系统文档分为三个部分：

1. **[使用指南](ICON_SYSTEM_GUIDE.md)** - 完整的使用文档和 API 说明
2. **[组件文档](../electron-app/src/components/shared/Icon/README.md)** - Icon 组件详细文档
3. **[资源说明](../electron-app/src/assets/icons/README.md)** - 图标文件管理规范

## 🚀 快速开始

```tsx
import { Icon } from '@/components/shared/Icon';

<Icon name="mic" />
<Icon name="mic" size={32} color="#1890ff" />
```

## 📂 目录结构

```
electron-app/src/assets/icons/
├── ui/      # UI 界面图标（27个）
├── tray/    # 系统托盘图标（5个）
└── app/     # 应用主图标（2个）
```

## 🔧 添加新图标

```bash
# 1. 添加 SVG 文件
cp new-icon.svg electron-app/src/assets/icons/ui/

# 2. 注册图标（编辑 iconRegistry.ts）
import NewIcon from '@/assets/icons/ui/new-icon.svg?react';
export const iconMap = { 'new-icon': NewIcon } as const;

# 3. 使用
<Icon name="new-icon" />
```

## 📚 查看详细文档

详细使用方法请查看 [ICON_SYSTEM_GUIDE.md](ICON_SYSTEM_GUIDE.md)

