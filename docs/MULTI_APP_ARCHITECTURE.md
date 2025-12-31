# 多应用架构说明

## 概述

系统已从单一"工作区"模式升级为**多应用架构**，支持轻松添加新的语音应用。

## 架构变更

### 前端目录结构

```
electron-app/src/components/
├── apps/                    # 应用目录
│   ├── VoiceNote/          # 语音笔记应用
│   │   ├── VoiceNote.tsx
│   │   ├── VoiceNote.css
│   │   ├── BlockEditor.tsx
│   │   ├── BlockEditor.css
│   │   ├── Block.css
│   │   ├── FormatToolbar.tsx
│   │   └── FormatToolbar.css
│   └── VoiceChat/          # 语音助手应用（新增）
│       ├── VoiceChat.tsx
│       └── VoiceChat.css
└── shared/                  # 共享组件
    ├── Sidebar.tsx
    ├── Sidebar.css
    ├── HistoryView.tsx
    ├── HistoryView.css
    ├── SettingsView.tsx
    ├── SettingsView.css
    ├── Toast.tsx
    └── Toast.css
```

### 应用类型

新增 `AppView` 类型定义：

```typescript
type AppView = 'voice-note' | 'voice-chat' | 'history' | 'settings';
```

### 侧边栏更新

侧边栏现在分为两个分组：

**应用分组：**
- 📝 语音笔记 (`voice-note`)
- 💬 语音助手 (`voice-chat`)

**通用功能：**
- 📚 历史记录 (`history`)
- ⚙️ 设置 (`settings`)

## 现有应用

### 1. 语音笔记 (VoiceNote)

**功能：** 语音转文字，实时记录和编辑

**特点：**
- 实时ASR识别
- 块编辑器（BlockEditor）
- 支持暂停/恢复
- 保存到历史记录

**位置：** `electron-app/src/components/apps/VoiceNote/`

### 2. 语音助手 (VoiceChat) - 新增

**功能：** 语音输入 → LLM → 文本回答

**当前状态：** 占位界面，待实现核心功能

**待开发功能：**
1. ✅ UI界面（已完成）
2. ⏳ 集成ASR服务
3. ⏳ 集成LLM服务
4. ⏳ 对话历史管理
5. ⏳ 会话保存

**位置：** `electron-app/src/components/apps/VoiceChat/`

## 添加新应用指南

### 步骤 1: 创建应用目录

```bash
cd electron-app/src/components/apps
mkdir YourNewApp
```

### 步骤 2: 创建应用组件

```typescript
// YourNewApp/YourNewApp.tsx
import React from 'react';
import './YourNewApp.css';

interface YourNewAppProps {
  apiConnected: boolean;
  // 其他需要的 props
}

export const YourNewApp: React.FC<YourNewAppProps> = ({ apiConnected }) => {
  return (
    <div className="your-new-app">
      <div className="your-new-app-header">
        <h2>Your App Title</h2>
      </div>
      <div className="your-new-app-content">
        {/* 应用内容 */}
      </div>
    </div>
  );
};
```

### 步骤 3: 更新类型定义

在 `Sidebar.tsx` 中添加新的视图类型：

```typescript
export type AppView = 'voice-note' | 'voice-chat' | 'your-new-app' | 'history' | 'settings';
```

### 步骤 4: 更新侧边栏

在 `Sidebar.tsx` 的应用分组中添加新按钮：

```tsx
<button
  className={`nav-item ${activeView === 'your-new-app' ? 'active' : ''}`}
  onClick={() => onViewChange('your-new-app')}
  aria-label="Your App Name"
>
  <span className="nav-icon">🎨</span>
  <span className="nav-text">Your App Name</span>
</button>
```

### 步骤 5: 更新 App.tsx

```typescript
// 导入新应用
import { YourNewApp } from './components/apps/YourNewApp/YourNewApp';

// 在渲染部分添加路由
{activeView === 'your-new-app' && (
  <YourNewApp apiConnected={apiConnected} />
)}
```

## 后端API扩展建议

为了支持新应用，建议添加以下API：

### VoiceChat 相关接口

```python
# 语音对话相关
POST /api/apps/voice-chat/send          # 发送消息（语音或文本）
POST /api/apps/voice-chat/stream        # 流式对话
GET  /api/apps/voice-chat/sessions      # 获取会话列表
GET  /api/apps/voice-chat/sessions/{id} # 获取会话详情
DELETE /api/apps/voice-chat/sessions/{id} # 删除会话
```

### 通用应用接口模式

```python
# 推荐的应用接口结构
/api/apps/{app_name}/
  - action1
  - action2
  - sessions (会话管理)
  - config (应用配置)
```

## 共享服务

所有应用可以共享以下服务：

1. **ASR服务** - 语音识别 (`VoiceService`)
2. **LLM服务** - 大语言模型 (`LLMService`)
3. **存储服务** - 历史记录 (`StorageProvider`)
4. **WebSocket** - 实时通信

## 配置文件扩展

在 `config.yml` 中可以添加应用级配置：

```yaml
apps:
  voice_note:
    enabled: true
    name: "语音笔记"
  voice_chat:
    enabled: true
    name: "语音助手"
    system_prompt: "你是一个友好的语音助手..."
  your_new_app:
    enabled: true
    name: "Your App"
    # 应用特定配置
```

## 数据库扩展

为支持多应用，建议在 `records` 表添加字段：

```sql
-- 添加应用类型字段
ALTER TABLE records ADD COLUMN app_type TEXT DEFAULT 'voice-note';

-- 添加应用特定元数据
ALTER TABLE records ADD COLUMN app_metadata JSON;
```

## 设计原则

1. **应用独立性** - 每个应用是独立的功能模块
2. **服务共享** - ASR、LLM、存储等服务可被所有应用使用
3. **组件复用** - 通用组件放在 `shared/` 目录
4. **清晰命名** - 使用描述性的应用名称和图标
5. **一致体验** - 保持UI/UX的一致性

## 开发建议

### VoiceChat 实现优先级

**Phase 1: 基础功能**
1. 集成现有的 ASR 服务
2. 集成现有的 LLM 服务（已有 `LLMService`）
3. 实现基本对话流程

**Phase 2: 增强功能**
1. 添加对话历史持久化
2. 支持多轮对话上下文
3. 优化流式响应体验

**Phase 3: 高级功能**
1. 支持多个对话会话
2. 会话导出/分享
3. 自定义 system prompt

### 代码示例：VoiceChat 核心逻辑

```typescript
const handleVoiceInput = async () => {
  // 1. 启动 ASR
  await fetch(`${API_BASE_URL}/api/recording/start`, { method: 'POST' });
  setIsListening(true);
  
  // 2. 等待用户说话，WebSocket 接收识别结果
  // （通过 WebSocket 监听 text_final 事件）
  
  // 3. 停止 ASR，获取完整文本
  const response = await fetch(`${API_BASE_URL}/api/recording/stop`, { method: 'POST' });
  const { final_text } = await response.json();
  setIsListening(false);
  
  // 4. 发送到 LLM
  setIsProcessing(true);
  const llmResponse = await fetch(`${API_BASE_URL}/api/llm/simple-chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: final_text }),
  });
  const { message: aiReply } = await llmResponse.json();
  setIsProcessing(false);
  
  // 5. 显示对话
  setMessages([
    ...messages,
    { id: uuid(), role: 'user', content: final_text, timestamp: Date.now() },
    { id: uuid(), role: 'assistant', content: aiReply, timestamp: Date.now() },
  ]);
};
```

## 迁移说明

### 从旧架构到新架构

**自动完成：**
- ✅ Workspace → VoiceNote
- ✅ 共享组件移至 `shared/`
- ✅ 侧边栏更新为分组模式
- ✅ 路由逻辑更新

**需要注意：**
- 历史记录中的 `app_type` 字段暂时为空，默认属于 `voice-note`
- 用户偏好设置保持不变
- WebSocket 连接逻辑无变化

## 测试清单

### 基础功能测试
- [ ] 侧边栏应用切换正常
- [ ] VoiceNote 应用功能正常
- [ ] VoiceChat 占位界面显示正常
- [ ] 历史记录查看正常
- [ ] 设置界面正常

### 数据测试
- [ ] 新记录保存正常
- [ ] 历史记录加载正常
- [ ] 记录删除正常

### UI/UX测试
- [ ] 分组标题显示正常
- [ ] 应用切换动画流畅
- [ ] 响应式布局正常

## 相关文档

- [系统架构说明](./ARCHITECTURE.md)
- [LLM集成指南](./LLM_INTEGRATION.md)
- [优化指南](./OPTIMIZATION_GUIDE.md)

---

**版本:** 2.0.0  
**更新日期:** 2024-12-31  
**作者:** AI Assistant

