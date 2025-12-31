# 应用布局规范

## 概述

为确保所有应用保持一致的视觉风格和用户体验，我们提供了统一的布局组件系统。所有应用都应该使用 `AppLayout` 作为主容器。

## 布局结构

```
┌─────────────────────────────────────────────────────┐
│  顶栏 (Header)                                       │
│  ┌────────────────┬──────────────────────────────┐  │
│  │ 左侧           │ 右侧                          │  │
│  │ - 图标         │ - 功能按钮                    │  │
│  │ - 标题/副标题  │ - 操作按钮组                  │  │
│  │ - 状态指示器   │                              │  │
│  └────────────────┴──────────────────────────────┘  │
├─────────────────────────────────────────────────────┤
│  内容区域 (Content)                                  │
│  - 可滚动                                           │
│  - 应用主要内容                                     │
│                                                     │
│                                                     │
├─────────────────────────────────────────────────────┤
│  底部区域 (Footer) - 可选                            │
│  - 固定在底部                                       │
│  - 适合放置输入框、提交按钮等                        │
└─────────────────────────────────────────────────────┘
```

## 核心组件

### 1. AppLayout

主布局容器，提供统一的应用结构。

**位置：** `src/components/shared/AppLayout.tsx`

**属性：**

```typescript
interface AppLayoutProps {
  // 必填
  title: string;              // 应用标题
  children: ReactNode;        // 主内容区域
  
  // 可选
  subtitle?: string;          // 副标题（显示在标题下方）
  icon?: string;              // 应用图标（emoji）
  statusIndicator?: ReactNode; // 状态指示器
  actions?: ReactNode;        // 功能按钮区域
  footer?: ReactNode;         // 底部区域
  className?: string;         // 自定义类名
}
```

**使用示例：**

```tsx
import { AppLayout } from '../../shared/AppLayout';

export const MyApp = () => {
  return (
    <AppLayout
      title="我的应用"
      subtitle="应用描述"
      icon="🎨"
      statusIndicator={<StatusIndicator status="connected" />}
      actions={
        <>
          <AppButton onClick={handleAction}>操作</AppButton>
        </>
      }
    >
      {/* 应用主内容 */}
      <div>内容区域</div>
    </AppLayout>
  );
};
```

### 2. StatusIndicator

状态指示器组件，显示应用当前状态。

**位置：** `src/components/shared/StatusIndicator.tsx`

**状态类型：**

```typescript
type StatusType = 
  | 'idle'         // 空闲
  | 'recording'    // 录音中
  | 'paused'       // 已暂停
  | 'stopping'     // 正在停止
  | 'processing'   // 处理中
  | 'connected'    // 已连接
  | 'disconnected' // 未连接
```

**使用示例：**

```tsx
import { StatusIndicator } from '../../shared/StatusIndicator';

// 基础使用
<StatusIndicator status="recording" />

// 自定义文本
<StatusIndicator status="processing" text="正在分析..." />

// 不显示状态点
<StatusIndicator status="connected" showDot={false} />
```

**视觉效果：**
- `recording/connected`: 绿色闪烁点
- `paused`: 黄色点
- `stopping/processing`: 紫色闪烁点
- `disconnected`: 红色点
- `idle`: 灰色点

### 3. AppButton

统一的按钮组件，提供多种样式变体。

**位置：** `src/components/shared/AppButton.tsx`

**变体样式：**

```typescript
type ButtonVariant = 
  | 'primary'    // 主要操作（紫色）
  | 'secondary'  // 次要操作（灰色）
  | 'success'    // 成功/启动（绿色）
  | 'warning'    // 警告/暂停（橙色）
  | 'danger'     // 危险/停止（红色）
  | 'info'       // 信息/保存（蓝色）
  | 'ghost'      // 幽灵按钮（透明边框）
```

**尺寸：**

```typescript
type ButtonSize = 'small' | 'medium' | 'large';
```

**使用示例：**

```tsx
import { AppButton, ButtonGroup } from '../../shared/AppButton';

// 基础按钮
<AppButton onClick={handleClick} variant="primary" size="large">
  点击我
</AppButton>

// 带图标的按钮
<AppButton 
  onClick={handleStart}
  variant="success"
  icon="🎤"
  title="开始录音"
  ariaLabel="开始录音"
>
  开始
</AppButton>

// 按钮组（自动添加分隔线）
<ButtonGroup>
  <AppButton variant="ghost" icon="🗑">删除</AppButton>
  <AppButton variant="ghost" icon="📋">复制</AppButton>
</ButtonGroup>
```

## 实际应用示例

### 示例 1: VoiceNote（带工具栏）

```tsx
import { AppLayout } from '../../shared/AppLayout';
import { StatusIndicator } from '../../shared/StatusIndicator';
import { AppButton, ButtonGroup } from '../../shared/AppButton';

export const VoiceNote = ({ asrState, apiConnected, onStart, onPause, onSave }) => {
  return (
    <AppLayout
      title="语音笔记"
      subtitle="语音转文字，实时记录"
      icon="📝"
      statusIndicator={
        apiConnected ? <StatusIndicator status={asrState} /> : null
      }
      actions={
        <>
          {/* 主操作按钮 */}
          <AppButton
            onClick={onStart}
            disabled={asrState !== 'idle'}
            variant="success"
            size="large"
            icon="🎤"
          >
            ASR
          </AppButton>

          <AppButton
            onClick={onPause}
            disabled={asrState !== 'recording'}
            variant="warning"
            icon="⏸"
          >
            PAUSE
          </AppButton>

          <AppButton
            onClick={onSave}
            variant="info"
            size="large"
            icon="💾"
          >
            SAVE
          </AppButton>

          {/* 工具按钮组 */}
          <ButtonGroup>
            <AppButton variant="ghost" icon="🗑">清空</AppButton>
            <AppButton variant="ghost" icon="📋">复制</AppButton>
          </ButtonGroup>
        </>
      }
    >
      {/* 主内容：编辑器 */}
      <BlockEditor content={content} />
    </AppLayout>
  );
};
```

### 示例 2: VoiceChat（带底部输入）

```tsx
import { AppLayout } from '../../shared/AppLayout';
import { StatusIndicator } from '../../shared/StatusIndicator';
import { AppButton } from '../../shared/AppButton';

export const VoiceChat = ({ apiConnected, isListening, onVoiceInput }) => {
  return (
    <AppLayout
      title="语音助手"
      subtitle="语音输入 → AI 回答"
      icon="💬"
      statusIndicator={
        <StatusIndicator 
          status={apiConnected ? 'connected' : 'disconnected'} 
        />
      }
      footer={
        <div className="footer-content">
          <AppButton
            onClick={onVoiceInput}
            disabled={!apiConnected}
            variant={isListening ? 'danger' : 'primary'}
            size="large"
            icon={isListening ? '⏹️' : '🎤'}
            className="voice-btn"
          >
            {isListening ? '停止录音' : '开始录音'}
          </AppButton>
          <div className="hint">点击麦克风开始对话</div>
        </div>
      }
    >
      {/* 主内容：对话列表 */}
      <ChatMessages messages={messages} />
    </AppLayout>
  );
};
```

### 示例 3: 简单应用（最小配置）

```tsx
import { AppLayout } from '../../shared/AppLayout';

export const SimpleApp = () => {
  return (
    <AppLayout
      title="简单应用"
      icon="🎨"
    >
      <div>应用内容</div>
    </AppLayout>
  );
};
```

## 样式定制

### 内容区域样式

内容区域默认可滚动，如需定制：

```css
/* 在你的应用 CSS 中 */
.my-app-content {
  padding: 24px;
  /* 其他样式 */
}
```

### 底部区域样式

```css
.my-app-footer-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}
```

### 按钮定制

```css
/* 覆盖按钮样式 */
.my-custom-btn {
  min-width: 200px;
  border-radius: 999px !important;
}
```

```tsx
<AppButton className="my-custom-btn">自定义按钮</AppButton>
```

## 响应式设计

布局组件已内置响应式支持：

- **桌面 (>768px)**: 顶栏横向布局，左右分布
- **移动 (<768px)**: 顶栏纵向布局，自动换行

## 设计原则

### 1. 一致性
- 所有应用使用相同的布局结构
- 统一的状态指示器样式
- 统一的按钮样式和行为

### 2. 清晰的信息层级
```
图标 + 标题 + 副标题 → 识别应用
状态指示器 → 了解当前状态
功能按钮 → 执行操作
```

### 3. 按钮组织规则

**左侧（顶栏左侧）：**
- 应用标识（图标、标题）
- 状态信息

**右侧（顶栏右侧）：**
- 主要操作按钮（大尺寸，鲜艳颜色）
- 次要操作按钮（中等尺寸）
- 工具按钮组（小尺寸，ghost 样式）

**底部（可选）：**
- 输入控件
- 提交按钮
- 辅助信息

### 4. 按钮颜色语义

| 变体 | 颜色 | 用途 | 示例 |
|------|------|------|------|
| `success` | 绿色 | 开始、启动 | 开始录音、启动服务 |
| `warning` | 橙色 | 暂停、警告 | 暂停录音、谨慎操作 |
| `danger` | 红色 | 停止、删除 | 停止录音、删除记录 |
| `info` | 蓝色 | 保存、信息 | 保存文件、查看详情 |
| `primary` | 紫色 | 主要操作 | 确认、提交 |
| `secondary` | 灰色 | 次要操作 | 取消、返回 |
| `ghost` | 透明 | 工具按钮 | 复制、清空、编辑 |

## 最佳实践

### ✅ 推荐做法

```tsx
// 1. 使用语义化的变体
<AppButton variant="success" icon="🎤">开始</AppButton>

// 2. 提供无障碍标签
<AppButton ariaLabel="开始录音" title="点击开始录音">开始</AppButton>

// 3. 合理使用按钮组
<ButtonGroup>
  <AppButton variant="ghost">操作1</AppButton>
  <AppButton variant="ghost">操作2</AppButton>
</ButtonGroup>

// 4. 状态管理
<AppButton disabled={!isReady}>操作</AppButton>
```

### ❌ 避免做法

```tsx
// 1. 不要混用不同尺寸的主按钮
<AppButton size="large">操作1</AppButton>
<AppButton size="small">操作2</AppButton>  // ❌

// 2. 不要过度使用 danger 变体
<AppButton variant="danger">普通操作</AppButton>  // ❌

// 3. 不要在顶栏放置过多按钮（>6个）
// 应该使用下拉菜单或移到其他位置
```

## 迁移指南

### 从旧布局迁移到新布局

**步骤 1: 替换导入**

```tsx
// 旧代码
import './MyApp.css';

// 新代码
import { AppLayout } from '../../shared/AppLayout';
import { StatusIndicator } from '../../shared/StatusIndicator';
import { AppButton, ButtonGroup } from '../../shared/AppButton';
```

**步骤 2: 重构 JSX 结构**

```tsx
// 旧代码
<div className="my-app">
  <div className="my-app-header">
    <h2>标题</h2>
    <button onClick={handler}>操作</button>
  </div>
  <div className="my-app-content">内容</div>
</div>

// 新代码
<AppLayout
  title="标题"
  icon="🎨"
  actions={<AppButton onClick={handler}>操作</AppButton>}
>
  内容
</AppLayout>
```

**步骤 3: 清理 CSS**

移除不再需要的样式（header、footer 等由 AppLayout 提供）。

## 组件清单

| 组件 | 路径 | 用途 |
|------|------|------|
| `AppLayout` | `shared/AppLayout.tsx` | 应用主容器 |
| `StatusIndicator` | `shared/StatusIndicator.tsx` | 状态指示器 |
| `AppButton` | `shared/AppButton.tsx` | 统一按钮 |
| `ButtonGroup` | `shared/AppButton.tsx` | 按钮分组 |

## 完整示例代码

查看以下文件获取完整示例：
- `electron-app/src/components/apps/VoiceNote/VoiceNote.tsx`
- `electron-app/src/components/apps/VoiceChat/VoiceChat.tsx`

## 常见问题

### Q: 如何自定义顶栏高度？

A: 顶栏高度由内容自动决定，最小高度为 64px。如需调整，在应用 CSS 中覆盖：

```css
.app-layout-header {
  min-height: 80px;
}
```

### Q: 如何禁用滚动？

A: 在内容区域设置 `overflow: hidden`：

```tsx
<AppLayout {...props}>
  <div style={{ overflow: 'hidden', height: '100%' }}>
    内容
  </div>
</AppLayout>
```

### Q: 底部区域可以固定高度吗？

A: 底部区域高度由内容决定，通过 padding 控制。如需固定高度：

```css
.app-layout-footer {
  height: 100px;
  padding: 0;
}
```

### Q: 按钮太多放不下怎么办？

A: 考虑以下方案：
1. 使用 `ButtonGroup` 分组
2. 将次要操作移到下拉菜单
3. 将工具按钮放到底部或侧边

---

**版本:** 1.0.0  
**更新日期:** 2025-12-31  
**维护者:** 开发团队

