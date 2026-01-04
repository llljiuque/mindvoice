# UI 优化更新 - 2026-01-03

## 📋 更新概述

本次更新对 VoiceNote 应用的按钮布局和交互设计进行了全面优化，并添加了翻译语言选择功能。

## ✨ 主要改进

### 1. 按钮布局重构

#### 顶部操作栏（Header Actions）
**之前**：🎤 启动 | 💾 保存 | 📝 新笔记 | 📋 复制 | 🚪 退出

**现在**：🌐 翻译 (下拉) | 💾 保存 | 📝 新笔记 | 🚪 退出

- ✅ 移除了 ASR 控制按钮（启动/停止）
- ✅ 移除了复制按钮
- ✅ 新增翻译语言选择器
- ✅ 保留文档管理相关操作

#### 底部工具栏（Bottom Toolbar）
**之前**：📊 小结

**现在**：🎤 启动/停止 | 📋 复制 | 📊 小结

- ✅ 新增 ASR 控制按钮（启动/停止/停止中）
- ✅ 新增复制按钮
- ✅ 保留小结生成功能
- ✅ 采用三栏布局（左对齐-居中-右对齐）

### 2. 翻译语言选择器

#### 功能特性
- **支持的语言**：
  - 📄 原文（默认）
  - 🇬🇧 英文
  - 🇯🇵 日文
  - 🇰🇷 韩文

#### UI 特性
- ✅ 下拉菜单设计，点击展开/收起
- ✅ 当前选中语言显示在按钮上
- ✅ 选中项带有 ✓ 标记
- ✅ 点击外部自动关闭
- ✅ 无内容时禁用（disabled）
- ✅ 平滑的展开/收起动画

#### 交互设计
```
┌─────────────────────────────┐
│ 🌐 翻译 | 📄 原文 ▼        │  ← 触发按钮
└─────────────────────────────┘
        ↓ 点击展开
┌─────────────────────────────┐
│ 📄 原文              ✓     │  ← 选中项
│ 🇬🇧 英文                    │
│ 🇯🇵 日文                    │
│ 🇰🇷 韩文                    │
└─────────────────────────────┘
```

### 3. 按钮尺寸优化（符合 WCAG 2.1 标准）

#### 之前
```css
small:  8px 14px, height ≈ 34px  ❌
medium: 10px 18px, height ≈ 38px ❌
large:  12px 24px, height ≈ 42px ❌
```

#### 现在
```css
small:  10px 16px, min-height: 44px ✅
medium: 12px 20px, min-height: 48px ✅
large:  14px 28px, min-height: 54px ✅
```

**优势**：
- ✅ 符合费茨定律（Fitts's Law）
- ✅ 满足 WCAG 2.1 可访问性标准（≥44×44px）
- ✅ 更容易点击，减少误触

### 4. 间距优化

```css
/* 按钮组主间距 */
gap: 16px (从 12px 增加)

/* 组内按钮间距 */
gap: 10px

/* 分隔线高度 */
height: 28px (从 24px 增加)
```

### 5. 响应式设计

#### 小屏幕适配（≤768px）
- 底部工具栏自动切换为垂直布局
- 所有按钮居中对齐
- 语言选择器自动缩小尺寸

## 📁 文件变更

### 新增文件
```
electron-app/src/components/shared/
├── LanguageSelector.tsx   (翻译语言选择器组件)
└── LanguageSelector.css   (样式文件)
```

### 修改文件
```
electron-app/src/components/
├── apps/VoiceNote/
│   ├── VoiceNote.tsx          (集成语言选择器，调整按钮布局)
│   ├── BottomToolbar.tsx      (新增 ASR 控制和复制按钮)
│   └── BottomToolbar.css      (三栏布局样式)
└── shared/
    ├── AppButton.css          (优化按钮尺寸和间距)
    └── AppLayout.css          (优化按钮容器间距)
```

## 🎯 设计原则

### 1. 按钮功能分层
- **顶部**：文档级操作（保存、新建、退出、翻译）
- **底部**：内容级操作（ASR 控制、复制、小结）

### 2. 视觉层级
- **主要操作**（启动/停止）：`large` + 鲜明颜色
- **次要操作**（保存、小结）：`medium` + info/success
- **辅助操作**（复制、新笔记、退出）：`medium` + ghost

### 3. 操作就近原则
- 编辑操作（ASR、复制）靠近内容区域（底部）
- 管理操作（保存、退出）远离内容区域（顶部）
- 减少鼠标移动距离，提升效率

## 🔧 技术实现

### LanguageSelector 组件

#### Props
```typescript
interface LanguageSelectorProps {
  value: LanguageType;              // 当前选中的语言
  onChange: (language: LanguageType) => void;  // 语言切换回调
  disabled?: boolean;               // 是否禁用
}

type LanguageType = 'original' | 'en' | 'ja' | 'ko';
```

#### 使用示例
```tsx
import { LanguageSelector, LanguageType } from '../../shared/LanguageSelector';

const [selectedLanguage, setSelectedLanguage] = useState<LanguageType>('original');

<LanguageSelector
  value={selectedLanguage}
  onChange={(lang) => setSelectedLanguage(lang)}
  disabled={!hasContent()}
/>
```

### BottomToolbar 组件

#### Props（更新后）
```typescript
interface BottomToolbarProps {
  // ASR 控制
  asrState: 'idle' | 'recording' | 'stopping';
  onAsrStart?: () => void;
  onAsrStop?: () => void;
  // 复制功能
  onCopy: () => void;
  hasContent: boolean;
  // 生成小结
  onSummary: () => void;
  isSummarizing?: boolean;
  // 连接状态
  apiConnected: boolean;
}
```

## 🚀 待实现功能

### 翻译功能（TODO）
```typescript
// VoiceNote.tsx 中的占位处理
const handleLanguageChange = (language: LanguageType) => {
  setSelectedLanguage(language);
  console.log('[VoiceNote] 切换翻译语言:', language);
  // TODO: 实现翻译功能
  // - 调用翻译 API
  // - 更新 BlockEditor 内容显示
  // - 支持切换回原文
};
```

**建议实现方式**：
1. 创建翻译服务 API（backend）
2. 在 BlockEditor 中添加翻译内容缓存
3. 支持原文/译文切换显示
4. 翻译时显示 loading 状态

## 📊 用户体验提升

### 1. 视觉清晰度
- ✅ 顶部更简洁，用户视线更集中在内容区
- ✅ 操作分层明确，减少认知负担

### 2. 操作效率
- ✅ 频繁操作（ASR 控制）靠近内容区
- ✅ 符合费茨定律，更大的点击目标
- ✅ 减少鼠标移动距离

### 3. 可访问性
- ✅ 所有按钮 ≥ 44px，符合 WCAG 2.1 标准
- ✅ 清晰的 aria-label 和 title 属性
- ✅ 键盘导航友好（ESC 关闭下拉菜单）

### 4. 视觉反馈
- ✅ 按钮 hover 效果（transform + shadow）
- ✅ 下拉菜单平滑动画
- ✅ 选中状态清晰标识（✓）
- ✅ 禁用状态明确（opacity: 0.5）

## 🎨 设计规范遵循

- ✅ **Fitts's Law**（费茨定律）：更大的点击目标
- ✅ **WCAG 2.1 Level AA**：≥44×44px 点击目标
- ✅ **Material Design**：阴影层级、动画时长
- ✅ **Apple HIG**：间距规范、视觉层级

## 📝 备注

- 翻译功能目前为 UI 占位，具体功能待实现
- 语言选择器可复用于其他应用（SmartChat、VoiceZen）
- 底部工具栏三栏布局为后续扩展预留空间

---

**更新日期**：2026-01-03  
**版本**：UI v2.0  
**维护者**：深圳王哥 & AI

