# 统一自动保存架构设计文档

**日期**: 2026-01-05  
**版本**: v2.0  
**状态**: 📋 架构设计（待实施）

---

## 🎯 设计目标

为所有应用（VoiceNote, VoiceChat, VoiceZen）提供统一的自动保存服务，同时保持各应用的数据结构独立性。

---

## 📐 架构设计

### 核心理念

**统一接口 + App 特定适配器模式**

```
┌─────────────────────────────────────────────────────────────┐
│                    应用层（App Components）                   │
│                                                              │
│   VoiceNote          VoiceChat           VoiceZen           │
│   (blocks结构)       (messages结构)      (entries结构)        │
└──────┬──────────────────┬──────────────────┬────────────────┘
       │                  │                  │
       ↓                  ↓                  ↓
┌──────────────────────────────────────────────────────────────┐
│         统一保存服务层（AutoSaveService）                      │
│                                                              │
│  • 统一的保存触发逻辑                                         │
│  • 统一的临时/持久化判断                                      │
│  • 统一的数据库交互                                           │
│  • 统一的恢复机制                                             │
└──────┬──────────────────┬──────────────────┬────────────────┘
       │                  │                  │
       ↓                  ↓                  ↓
┌──────────────────────────────────────────────────────────────┐
│             适配器层（App Adapters）                          │
│                                                              │
│  VoiceNoteAdapter   VoiceChatAdapter   VoiceZenAdapter      │
│  • 数据获取          • 数据获取          • 数据获取           │
│  • 临时状态判断      • 临时状态判断      • 临时状态判断        │
│  • 数据转换          • 数据转换          • 数据转换           │
│  • 内容检查          • 内容检查          • 内容检查           │
└──────┬──────────────────┬──────────────────┬────────────────┘
       │                  │                  │
       └──────────────────┴──────────────────┘
                          ↓
              ┌──────────────────────┐
              │   统一 API 接口       │
              │                      │
              │ POST /api/text/save  │
              │ PUT /api/records/:id │
              └──────────────────────┘
                          ↓
              ┌──────────────────────┐
              │   SQLite 数据库       │
              │   records 表          │
              │   (app_type字段区分)  │
              └──────────────────────┘
```

---

## 🔧 核心组件

### 1. AutoSaveService（统一保存服务）

**职责**:
- ✅ 管理保存触发逻辑（定时、事件驱动）
- ✅ 管理 localStorage 临时数据
- ✅ 管理数据库持久化
- ✅ 管理数据恢复
- ✅ 管理会话状态

**关键方法**:
```typescript
class AutoSaveService {
  start()                                    // 启动自动保存
  stop()                                     // 停止自动保存
  saveToDatabase(trigger, immediate)         // 保存到数据库
  recover()                                  // 恢复数据
  reset()                                    // 重置会话
  setEditingItemId(itemId)                   // 设置编辑项（兜底保存）
}
```

### 2. AppAdapter（应用适配器接口）

**职责**:
- ✅ 适配各应用的数据结构
- ✅ 判断临时状态
- ✅ 转换数据格式
- ✅ 检查内容有效性

**接口定义**:
```typescript
interface AppAdapter {
  getAllData(): any;                  // 获取所有数据
  isVolatile(item: any): boolean;     // 判断是否临时状态
  getStableData(): any;               // 获取稳定数据
  toSaveData(data: any): SaveData;    // 转换为保存格式
  hasContent(data: any): boolean;     // 检查是否有内容
}
```

### 3. 各应用适配器

#### VoiceNoteAdapter
```typescript
class VoiceNoteAdapter implements AppAdapter {
  // 数据结构
  data = {
    blocks: Block[],      // 块列表
    noteInfo: NoteInfo    // 笔记信息
  }
  
  // 临时状态判断
  isVolatile(block) {
    return block.isAsrWriting ||      // ASR 正在写入
           block.id === editingBlockId // 用户正在编辑
  }
}
```

#### VoiceChatAdapter
```typescript
class VoiceChatAdapter implements AppAdapter {
  // 数据结构
  data = {
    messages: Message[],           // 消息列表
    conversationContext: Context   // 对话上下文
  }
  
  // 临时状态判断
  isVolatile(message) {
    return message.isStreaming  // AI 正在流式输出
  }
}
```

#### VoiceZenAdapter
```typescript
class VoiceZenAdapter implements AppAdapter {
  // 数据结构
  data = {
    entries: ZenEntry[],  // 禅条目列表
    zenState: State       // 禅状态
  }
  
  // 临时状态判断
  isVolatile(entry) {
    return entry.isWriting  // 正在书写
  }
}
```

---

## 📊 数据流

### 保存流程

```
用户操作/ASR识别
    ↓
触发保存事件（utterance/edit_complete/etc）
    ↓
AutoSaveService.saveToDatabase(trigger)
    ↓
Adapter.getStableData() ← 过滤临时数据
    ↓
Adapter.toSaveData() ← 转换格式
    ↓
POST /api/text/save 或 PUT /api/records/:id
    ↓
SQLite 数据库（app_type 字段区分）
```

### 临时保存流程

```
定时器（每1秒）
    ↓
AutoSaveService.saveVolatileToLocalStorage()
    ↓
Adapter.getAllData() ← 获取所有数据
    ↓
过滤临时状态的数据项
    ↓
localStorage.setItem(`volatile_${appType}`, data)
```

### 恢复流程

```
应用启动
    ↓
AutoSaveService.recover()
    ↓
1. 从数据库获取最近记录（1小时内）
    ↓
2. 检查 localStorage 临时数据（5分钟内）
    ↓
3. 比较时间戳，选择更新的数据
    ↓
4. 恢复数据到应用
    ↓
5. 启动工作会话
```

---

## 🎯 使用示例

### VoiceNote 使用示例

```typescript
import { AutoSaveService } from '@/services/AutoSaveService';
import { VoiceNoteAdapter } from '@/services/adapters/VoiceNoteAdapter';

function VoiceNote() {
  const blockEditorRef = useRef();
  const [editingBlockId, setEditingBlockId] = useState(null);
  
  // 创建适配器
  const adapter = useMemo(() => {
    return new VoiceNoteAdapter(
      () => blockEditorRef.current?.getBlocks?.() || [],
      () => blockEditorRef.current?.getNoteInfo?.()
    );
  }, []);
  
  // 创建自动保存服务
  const autoSaveService = useMemo(() => {
    return new AutoSaveService('voice-note', adapter);
  }, [adapter]);
  
  // 启动自动保存
  useEffect(() => {
    autoSaveService.start();
    return () => autoSaveService.stop();
  }, [autoSaveService]);
  
  // 同步编辑状态
  useEffect(() => {
    adapter.setEditingBlockId(editingBlockId);
    autoSaveService.setEditingItemId(editingBlockId);
  }, [editingBlockId, adapter, autoSaveService]);
  
  // 处理内容变化
  const handleContentChange = (content, isDefiniteUtterance) => {
    if (isDefiniteUtterance) {
      // ASR 确认 utterance 时立即保存
      autoSaveService.saveToDatabase('definite_utterance', true);
    }
  };
  
  // 处理 block 失焦
  const handleBlockBlur = (blockId) => {
    setEditingBlockId(null);
    // 编辑完成时防抖保存
    autoSaveService.saveToDatabase('edit_complete', false);
  };
  
  // 处理笔记信息变更
  const handleNoteInfoChange = (noteInfo) => {
    // 笔记信息变更时防抖保存
    autoSaveService.saveToDatabase('content_change', false);
  };
  
  return (
    <BlockEditor
      onContentChange={handleContentChange}
      onBlockFocus={setEditingBlockId}
      onBlockBlur={handleBlockBlur}
      onNoteInfoChange={handleNoteInfoChange}
    />
  );
}
```

### VoiceChat 使用示例

```typescript
import { AutoSaveService } from '@/services/AutoSaveService';
import { VoiceChatAdapter } from '@/services/adapters/VoiceChatAdapter';

function VoiceChat() {
  const [messages, setMessages] = useState([]);
  const [context, setContext] = useState({});
  
  // 创建适配器
  const adapter = useMemo(() => {
    return new VoiceChatAdapter(
      () => messages,
      () => context
    );
  }, [messages, context]);
  
  // 创建自动保存服务
  const autoSaveService = useMemo(() => {
    return new AutoSaveService('voice-chat', adapter);
  }, [adapter]);
  
  // 启动自动保存
  useEffect(() => {
    autoSaveService.start();
    return () => autoSaveService.stop();
  }, [autoSaveService]);
  
  // 处理消息更新
  const handleMessageUpdate = (newMessage) => {
    setMessages([...messages, newMessage]);
    
    // 如果是完整的用户消息，立即保存
    if (newMessage.role === 'user' && !newMessage.isStreaming) {
      autoSaveService.saveToDatabase('content_change', true);
    }
  };
  
  // 处理 AI 响应完成
  const handleAIResponseComplete = () => {
    // AI 响应完成时立即保存
    autoSaveService.saveToDatabase('content_change', true);
  };
  
  return (
    <ChatInterface
      messages={messages}
      onMessageUpdate={handleMessageUpdate}
      onAIResponseComplete={handleAIResponseComplete}
    />
  );
}
```

### VoiceZen 使用示例

```typescript
import { AutoSaveService } from '@/services/AutoSaveService';
import { VoiceZenAdapter } from '@/services/adapters/VoiceZenAdapter';

function VoiceZen() {
  const [entries, setEntries] = useState([]);
  const [zenState, setZenState] = useState({});
  
  // 创建适配器
  const adapter = useMemo(() => {
    return new VoiceZenAdapter(
      () => entries,
      () => zenState
    );
  }, [entries, zenState]);
  
  // 创建自动保存服务
  const autoSaveService = useMemo(() => {
    return new AutoSaveService('voice-zen', adapter);
  }, [adapter]);
  
  // 启动自动保存
  useEffect(() => {
    autoSaveService.start();
    return () => autoSaveService.stop();
  }, [autoSaveService]);
  
  // 处理书写完成
  const handleWritingComplete = () => {
    // 书写完成时立即保存
    autoSaveService.saveToDatabase('edit_complete', true);
  };
  
  return (
    <ZenInterface
      entries={entries}
      onWritingComplete={handleWritingComplete}
    />
  );
}
```

---

## 🎁 架构优势

### 1. 统一性

| 优势 | 说明 |
|------|------|
| ✅ **统一的保存逻辑** | 所有应用共享相同的保存触发、防抖、兜底机制 |
| ✅ **统一的API接口** | 所有应用使用相同的数据库API |
| ✅ **统一的恢复机制** | 所有应用共享相同的数据恢复逻辑 |
| ✅ **统一的配置** | 保存间隔、防抖延迟等配置统一管理 |

### 2. 灵活性

| 优势 | 说明 |
|------|------|
| ✅ **数据结构独立** | 各应用保持自己的数据结构不变 |
| ✅ **临时状态定制** | 各应用自定义临时状态判断逻辑 |
| ✅ **格式转换自由** | 各应用自定义数据到文本的转换 |
| ✅ **易于扩展** | 新增应用只需实现适配器接口 |

### 3. 可维护性

| 优势 | 说明 |
|------|------|
| ✅ **职责清晰** | 保存服务和适配器职责明确分离 |
| ✅ **代码复用** | 保存逻辑只需实现一次 |
| ✅ **易于测试** | 各组件可独立单元测试 |
| ✅ **易于调试** | 统一的日志输出格式 |

---

## 📝 迁移计划

### 阶段1：创建基础设施（已完成）✅

- [x] 创建 `AutoSaveService` 类
- [x] 创建 `AppAdapter` 接口
- [x] 创建 `VoiceNoteAdapter`
- [x] 创建 `VoiceChatAdapter`
- [x] 创建 `VoiceZenAdapter`

### 阶段2：迁移 VoiceNote（下一步）

- [ ] 重构 `VoiceNote` 使用 `AutoSaveService`
- [ ] 移除旧的保存逻辑
- [ ] 测试保存和恢复功能
- [ ] 验证性能和可靠性

### 阶段3：扩展到其他应用

- [ ] 迁移 `VoiceChat` 使用 `AutoSaveService`
- [ ] 迁移 `VoiceZen` 使用 `AutoSaveService`
- [ ] 统一测试所有应用

### 阶段4：优化和完善

- [ ] 性能优化
- [ ] 错误处理完善
- [ ] 用户体验优化
- [ ] 文档完善

---

## 🔍 对比：统一 vs 分开实现

### 统一接口方案（推荐）✅

**优点**:
- ✅ 代码复用率高（保存逻辑只实现一次）
- ✅ 一致的用户体验（所有应用保存行为一致）
- ✅ 易于维护（修改一处，所有应用受益）
- ✅ 配置统一（保存间隔、防抖等参数统一）
- ✅ 测试成本低（核心逻辑只需测试一次）

**缺点**:
- ⚠️ 初期实现成本高（需要设计适配器系统）
- ⚠️ 需要额外的抽象层

### 分开实现方案

**优点**:
- ✅ 实现简单直接
- ✅ 各应用完全独立

**缺点**:
- ❌ 代码重复（每个应用都要实现保存逻辑）
- ❌ 行为不一致（不同应用保存行为可能不同）
- ❌ 维护成本高（修改需要同步多处）
- ❌ 配置分散（难以统一管理）
- ❌ 测试成本高（每个应用都要测试）

---

## 🎯 总结

**推荐采用统一接口 + 适配器模式**，原因：

1. ✅ **长期收益高**: 虽然初期投入稍高，但长期维护成本大幅降低
2. ✅ **质量保证**: 核心逻辑统一，容易保证质量和一致性
3. ✅ **扩展性好**: 新增应用只需实现适配器，保存逻辑自动获得
4. ✅ **用户体验佳**: 所有应用保存行为一致，用户学习成本低

**这是一个符合软件工程最佳实践的架构设计！** 🚀

