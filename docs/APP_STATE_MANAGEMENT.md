# App 级状态管理设计文档

## 概述

本文档描述了 MindVoice 的应用级状态管理系统，该系统用于防止不合适的应用切换，确保用户不会丢失工作中的数据。

## 设计原则

### 核心理念
- **单应用工作原则**：同一时间只允许一个应用处于"工作中"状态
- **数据保护优先**：在切换应用时，必须处理当前工作中的数据
- **用户友好体验**：提供明确的状态提示和灵活的操作选项

### 应用分类

系统将视图分为两类：

1. **工作应用** (Working Apps)
   - `voice-note` (语音笔记)
   - `voice-chat` (语音助手)
   - 特点：有明确的工作会话，会产生需要保存的数据

2. **工具视图** (Utility Views)
   - `history` (历史记录)
   - `settings` (设置)
   - `about` (关于)
   - 特点：只读或配置性质，不产生需要保存的数据

## 架构设计

### 全局状态

在 `App.tsx` 中维护以下全局状态：

```typescript
// 当前工作中的应用
const [activeWorkingApp, setActiveWorkingApp] = useState<AppView | null>(null);

// 切换确认对话框
const [showSwitchConfirm, setShowSwitchConfirm] = useState(false);
const [pendingView, setPendingView] = useState<AppView | null>(null);

// 工作会话是否激活
const [isWorkSessionActive, setIsWorkSessionActive] = useState(false);
```

### 核心函数

#### 1. 工作状态检查 `isAppWorking()`

```typescript
const isAppWorking = (app: AppView): boolean => {
  switch (app) {
    case 'voice-note':
      return asrState === 'recording' || text.trim().length > 0 || isWorkSessionActive;
    case 'voice-chat':
      // TODO: 实现 VoiceChat 的工作状态检查
      return false;
    default:
      return false;
  }
};
```

**判断标准**：
- **VoiceNote**: ASR 正在录音 OR 有未保存文本 OR 工作会话已激活
- **VoiceChat**: (待实现) 有未完成的对话会话

#### 2. 应用切换处理 `handleViewChange()`

```typescript
const handleViewChange = (newView: AppView) => {
  // 如果切换到工具视图，检查是否有工作中的应用
  if (newView === 'history' || newView === 'settings' || newView === 'about') {
    if (activeWorkingApp && isAppWorking(activeWorkingApp)) {
      setPendingView(newView);
      setShowSwitchConfirm(true);
      return;
    }
    setActiveView(newView);
    return;
  }
  
  // 如果有应用在工作
  if (activeWorkingApp && activeWorkingApp !== newView) {
    if (isAppWorking(activeWorkingApp)) {
      setPendingView(newView);
      setShowSwitchConfirm(true);
      return;
    }
  }
  
  // 切换到新应用
  setActiveView(newView);
};
```

**切换规则**：
1. 工具视图之间可以自由切换
2. 工作应用 → 工具视图：需要确认
3. 工作应用 → 另一个工作应用：需要确认
4. 空闲状态下：自由切换

#### 3. 工作会话管理

```typescript
// 开始工作会话
const startWorkSession = (app: AppView): boolean => {
  if (activeWorkingApp && activeWorkingApp !== app) {
    setToast({ 
      message: `${getAppName(activeWorkingApp)} 正在工作中，请先完成当前工作`, 
      type: 'warning' 
    });
    return false;
  }
  setActiveWorkingApp(app);
  setIsWorkSessionActive(true);
  return true;
};

// 结束工作会话
const endWorkSession = () => {
  setActiveWorkingApp(null);
  setIsWorkSessionActive(false);
};
```

## 用户交互流程

### 流程 1: 正常工作流程

```
1. 用户打开 VoiceNote → 状态：空闲
2. 点击"开始"按钮 → 启动工作会话
3. 输入/语音录制内容 → 自动保存草稿（每3秒）
4. 点击"保存" → 保存到历史记录 → 结束工作会话 → 清除草稿
```

### 流程 2: 切换应用（有未保存内容）

```
1. 用户在 VoiceNote 中有未保存内容
2. 尝试切换到 VoiceChat 或 History
3. 系统弹出确认对话框：
   - "保存并切换"：保存当前内容 → 结束会话 → 切换
   - "放弃内容"：清空内容和草稿 → 结束会话 → 切换
   - "取消"：留在当前应用
```

### 流程 3: 侧边栏锁定提示

```
1. VoiceNote 有工作会话时
2. Sidebar 中其他应用按钮显示 🔒 图标
3. 按钮变为半透明且禁用
4. 鼠标悬停时不会高亮（通过 CSS 实现）
```

## VoiceNote 工作会话定义

### 会话开始时机

以下任一条件满足时，VoiceNote 进入工作状态：

1. **显式开始**：用户点击"开始"按钮
2. **隐式开始**：用户开始输入文本（自动触发）
3. **ASR 启动**：ASR 开始录音时

### 会话结束时机

以下操作会结束工作会话：

1. **保存成功**：内容保存到历史记录
2. **清空内容**：用户点击"清空"按钮
3. **放弃内容**：在切换确认对话框中选择"放弃"

### 工作状态判断

```typescript
// VoiceNote 被视为"工作中"的条件（任一满足）：
isWorking = 
  asrState === 'recording' ||           // ASR 正在录音
  text.trim().length > 0 ||             // 有未保存文本
  isWorkSessionActive;                   // 工作会话已激活
```

## 自动草稿保存

### 功能特性

- **自动保存频率**：文本变化后 3 秒自动保存
- **保存位置**：浏览器 localStorage
- **有效期**：24 小时
- **恢复时机**：应用启动时自动检查并恢复

### 实现细节

```typescript
// 自动保存
useEffect(() => {
  if (text.trim() && isWorkSessionActive && activeView === 'voice-note') {
    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
    }
    
    autoSaveTimerRef.current = setTimeout(() => {
      const draft = {
        text,
        app: activeView,
        timestamp: Date.now(),
      };
      localStorage.setItem('voiceNoteDraft', JSON.stringify(draft));
    }, 3000);
  }
  
  return () => {
    if (autoSaveTimerRef.current) {
      clearTimeout(autoSaveTimerRef.current);
    }
  };
}, [text, isWorkSessionActive, activeView]);

// 恢复草稿
useEffect(() => {
  const savedDraft = localStorage.getItem('voiceNoteDraft');
  if (savedDraft) {
    const draft = JSON.parse(savedDraft);
    const oneDayAgo = Date.now() - 24 * 60 * 60 * 1000;
    if (draft.timestamp > oneDayAgo && draft.text) {
      setText(draft.text);
      setToast({ message: '已恢复上次未保存的草稿', type: 'info' });
    } else {
      localStorage.removeItem('voiceNoteDraft');
    }
  }
}, []);
```

### 草稿清除时机

- 保存成功后
- 清空内容时
- 放弃并切换应用时
- 草稿过期时（>24小时）

## 确认对话框设计

### 组件：ConfirmDialog

```typescript
interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  type?: 'info' | 'warning' | 'danger';
  actions: DialogAction[];
  onClose?: () => void;
}
```

### 三种操作按钮

1. **保存并切换** (Success 样式)
   - 保存当前内容到历史记录
   - 清除草稿
   - 结束工作会话
   - 切换到目标应用

2. **放弃内容** (Danger 样式)
   - 清空当前内容
   - 清除草稿
   - 结束工作会话
   - 切换到目标应用

3. **取消** (Ghost 样式)
   - 关闭对话框
   - 保持在当前应用
   - 继续工作

### 视觉设计

- **背景遮罩**：半透明黑色，带模糊效果
- **对话框**：居中显示，带阴影和圆角
- **类型指示**：顶部带颜色条，配合图标
  - Warning: 🟡 黄色
  - Info: 🔵 蓝色
  - Danger: 🔴 红色
- **动画效果**：淡入 + 上滑动画

## Sidebar 锁定状态

### 锁定规则

```typescript
const isLocked = (view: AppView): boolean => {
  if (!activeWorkingApp) return false;
  
  const workingApps: AppView[] = ['voice-note', 'voice-chat'];
  const utilityViews: AppView[] = ['history', 'settings', 'about'];
  
  if (workingApps.includes(view) && workingApps.includes(activeWorkingApp)) {
    // 工作应用之间互锁
    return view !== activeWorkingApp;
  }
  
  if (utilityViews.includes(view) && workingApps.includes(activeWorkingApp)) {
    // 有工作应用在运行时，工具视图被锁定
    return true;
  }
  
  return false;
};
```

### 视觉反馈

```css
.nav-item.locked {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}

.nav-lock-icon {
  font-size: 12px;
  opacity: 0.6;
}
```

- 锁定的按钮变为半透明（50% 透明度）
- 显示 🔒 图标
- 禁用鼠标交互
- 鼠标样式变为 `not-allowed`

## 最佳实践

### 对于开发者

1. **添加新应用时**：
   - 定义应用的"工作状态"判断逻辑
   - 实现 `onStartWork` 和 `onEndWork` 回调
   - 在 `isAppWorking()` 中添加判断逻辑

2. **数据保护**：
   - 任何可能丢失用户数据的操作都应该触发确认
   - 使用 localStorage 保存草稿作为备份

3. **用户体验**：
   - 提供明确的状态指示
   - 自动保存应该静默进行，不打扰用户
   - 恢复草稿时给出提示

### 对于用户

1. **正常工作流程**：
   - 打开应用 → 开始工作 → 保存/完成
   - 系统会自动保存草稿，防止意外丢失

2. **切换应用**：
   - 如果有未保存内容，会提示确认
   - 可以选择保存、放弃或取消

3. **草稿恢复**：
   - 重新打开应用时会自动恢复草稿
   - 草稿有效期 24 小时

## 技术栈

- **React Hooks**: useState, useEffect, useRef, useCallback
- **TypeScript**: 类型安全的状态管理
- **localStorage**: 浏览器本地存储（草稿保存）
- **CSS3**: 视觉效果和动画

## 未来扩展

### 计划功能

1. **VoiceChat 工作状态**
   - 定义对话会话的开始和结束
   - 实现未完成对话的保护

2. **多窗口支持**
   - 跨窗口的工作状态同步
   - 使用 BroadcastChannel API

3. **云端草稿同步**
   - 将草稿保存到服务器
   - 支持跨设备恢复

4. **撤销/重做**
   - 本地历史记录栈
   - 支持 Ctrl+Z / Ctrl+Y

## 相关文档

- [应用布局指南](./APP_LAYOUT_GUIDE.md)
- [多应用架构](./MULTI_APP_ARCHITECTURE.md)
- [系统架构](./ARCHITECTURE.md)

---

**版本**: v1.0  
**最后更新**: 2025-12-31  
**作者**: 深圳王哥 & AI

