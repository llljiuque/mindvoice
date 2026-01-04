# AutoSaveService 快速参考

**版本**: v1.4.1  
**更新**: 2026-01-05

---

## 🚀 快速开始

### 为新应用添加自动保存（3步）

```typescript
// 1️⃣ 创建适配器类
class MyAppAdapter implements IAutoSaveAdapter {
  isVolatileItem(item: any): boolean { /* 判断是否临时 */ }
  getStableItems(): any[] { /* 获取稳定数据 */ }
  getVolatileItems(): any[] { /* 获取临时数据 */ }
  convertToSaveData(items: any[]): { text: string; metadata: any } { /* 转换 */ }
  // ... 其他方法
}

// 2️⃣ 在 App.tsx 中创建实例
const myAppAdapter = useMemo(() => new MyAppAdapter(...), []);
const myAppAutoSave = useMemo(() => 
  new AutoSaveService('my-app', myAppAdapter), [myAppAdapter]);

// 3️⃣ 启动服务
useEffect(() => {
  if (isWorkSessionActive && activeView === 'my-app') {
    myAppAutoSave.start();
    return () => myAppAutoSave.stop();
  }
}, [isWorkSessionActive, activeView]);
```

---

## 📋 AutoSaveService API

### 核心方法

```typescript
// 生命周期
service.start()                    // 启动服务
service.stop()                     // 停止服务

// 保存操作
service.save()                     // 手动保存
service.saveToDatabase(            // 保存到数据库
  trigger: SaveTrigger,            // 触发器类型
  immediate: boolean               // 是否立即保存
)

// 恢复操作
service.recover()                  // 自动恢复（数据库+localStorage）

// 状态管理
service.setEditingItemId(id)      // 设置当前编辑项ID
service.setAsrWritingItemId(id)   // 设置ASR写入项ID
```

### 触发器类型

```typescript
type SaveTrigger = 
  | 'definite_utterance'   // ASR 确认语句（立即保存）
  | 'edit_complete'        // 编辑完成（3秒防抖）
  | 'content_change'       // 内容变更（3秒防抖）
  | 'manual'               // 手动保存（立即）
  | 'periodic'             // 定期保存（60秒）
  | 'backup';              // 兜底保存（30秒）
```

---

## 🔌 适配器接口

### 必须实现的方法

```typescript
interface IAutoSaveAdapter {
  // 判断数据项状态
  isVolatileItem(item: any): boolean;
  
  // 获取数据
  getStableItems(): any[];
  getVolatileItems(): any[];
  getAllItems(): any[];
  
  // 数据转换
  convertToSaveData(items: any[]): { text: string; metadata: any };
  convertToLocalStorageData(items: any[]): any;
  
  // 恢复数据
  recoverFromDatabase(data: any): any;
  recoverFromLocalStorage(data: any): any;
  
  // 状态设置
  setEditingItemId(id: string | null): void;
  setAsrWritingItemId(id: string | null): void;
}
```

---

## ⏱️ 保存时机

| 事件 | 触发器 | 延迟 | 说明 |
|------|--------|------|------|
| ASR 确认语句 | `definite_utterance` | 立即 | 防止语音输入丢失 |
| 编辑失焦 | `edit_complete` | 3秒 | 防抖，避免频繁保存 |
| 内容变更 | `content_change` | 3秒 | 标题、信息等变更 |
| 手动保存 | `manual` | 立即 | 用户点击保存按钮 |
| 定期检查 | `periodic` | 60秒 | 自动检查并保存 |
| 长时间编辑 | `backup` | 30秒 | 兜底保护 |

---

## 💾 保存策略

### localStorage（临时保存）

- ⏱️ **间隔**: 每1秒
- 📦 **内容**: 只保存 volatile items（正在编辑/ASR写入）
- 🎯 **目的**: 快速恢复未完成的输入
- ⚡ **优先级**: 高（5分钟内优先于数据库）

### Database（持久化保存）

- ⏱️ **间隔**: 根据触发器
- 📦 **内容**: 只保存 stable items（已完成）
- 🎯 **目的**: 长期存储
- 🔄 **策略**: 优先更新现有记录，避免重复

---

## 🔧 配置参数

```typescript
// AutoSaveService 内置配置
const CONFIG = {
  localStorageInterval: 1000,      // localStorage 保存间隔（1秒）
  periodicSaveInterval: 60000,     // 定期保存间隔（60秒）
  editingBackupDelay: 30000,       // 长时间编辑兜底（30秒）
  databaseSaveDebounce: 3000,      // 数据库保存防抖（3秒）
  recoverTimeWindow: 3600000,      // 恢复时间窗口（1小时）
  volatileDataWindow: 300000,      // 临时数据窗口（5分钟）
};
```

---

## 📝 使用示例

### VoiceNote 示例

```typescript
// 1. 创建适配器
const voiceNoteAdapter = useMemo(() => {
  return new VoiceNoteAdapter(
    () => blockEditorRef.current?.getBlocks?.() || [],
    () => blockEditorRef.current?.getNoteInfo?.()
  );
}, []);

// 2. 创建服务
const voiceNoteAutoSave = useMemo(() => {
  return new AutoSaveService('voice-note', voiceNoteAdapter);
}, [voiceNoteAdapter]);

// 3. 同步编辑状态
useEffect(() => {
  voiceNoteAdapter.setEditingBlockId(editingBlockId);
  voiceNoteAutoSave.setEditingItemId(editingBlockId);
}, [editingBlockId]);

// 4. 启动服务
useEffect(() => {
  if (isWorkSessionActive && activeView === 'voice-note') {
    voiceNoteAutoSave.start();
    return () => voiceNoteAutoSave.stop();
  }
}, [isWorkSessionActive, activeView]);

// 5. 在回调中触发保存
<VoiceNote
  onBlockBlur={() => 
    voiceNoteAutoSave.saveToDatabase('edit_complete', false)
  }
  onContentChange={(content, isUtterance) => {
    if (isUtterance) {
      voiceNoteAutoSave.saveToDatabase('definite_utterance', true);
    }
  }}
  onNoteInfoChange={() => 
    voiceNoteAutoSave.saveToDatabase('content_change', false)
  }
/>
```

---

## 🐛 常见问题

### Q1: 为什么有些内容没有保存到数据库？

**A**: 检查是否是 volatile item（正在编辑或 ASR 写入中）。只有 stable items 会保存到数据库。

### Q2: localStorage 中的数据什么时候会被清除？

**A**: 
- 当没有 volatile items 时自动清除
- 数据保存到数据库后会清除
- 应用启动后恢复完成会清除

### Q3: 如何禁用某个保存触发器？

**A**: 在适配器中返回空数组或不调用 `saveToDatabase` 方法。

### Q4: 数据库保存失败怎么办？

**A**: 
1. 检查后端是否运行（http://127.0.0.1:8765/health）
2. 查看控制台错误日志
3. localStorage 中仍有临时数据，不会丢失

### Q5: 如何测试自动保存？

**A**: 参考 [测试文档](./test_autosave_migration.md) 中的11个测试用例。

---

## 📊 日志格式

```
[AutoSaveService] <消息>
[AutoSaveService] 临时保存 volatile items: { count: 1 }
[AutoSaveService] 保存到数据库 (trigger: definite_utterance, immediate: true)
[AutoSaveService] 创建记录成功: abc123
[AutoSaveService] 更新记录成功: abc123
[AutoSaveService] 从数据库恢复: { recordId: abc123, blocks: 5 }
[AutoSaveService] 从 localStorage 恢复 volatile items
```

---

## 🔗 相关文档

- [架构文档](./architecture_unified_autosave.md) - 详细架构说明
- [功能文档](./feature_20260105_smart_autosave.md) - 功能详细说明
- [迁移文档](./migration_voicenote_autosave.md) - VoiceNote 迁移示例
- [测试文档](./test_autosave_migration.md) - 测试用例和指南
- [总结文档](./summary_autosave_migration_20260105.md) - 迁移总结

---

## 💡 提示

- ✅ 始终实现所有适配器接口方法
- ✅ 在 `start()` 后才会开始自动保存
- ✅ 记得在组件卸载时调用 `stop()`
- ✅ 使用 `useMemo` 避免重复创建实例
- ✅ 观察控制台日志来调试保存逻辑

---

**快速参考完毕！开始使用 AutoSaveService 吧！** 🚀

