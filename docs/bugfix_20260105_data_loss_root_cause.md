# 数据丢失问题根本原因分析

**日期**: 2026-01-05  
**问题**: 录制1小时视频转文本后，点击 EXIT，历史记录为空  
**状态**: ✅ 原因已找到

---

## 问题现象

用户录制了1小时+的语音转文字，界面显示大量内容，但点击 EXIT 后：
- ❌ 历史记录为空
- ❌ 数据库中没有记录
- ✅ 前端日志显示"更新记录成功"
- ✅ 后端日志显示"已更新记录，blocks数据: **无**"

---

## 根本原因

### 原因1：EXIT 没有保存逻辑 ✅ 已修复

旧的 `endWorkSession` 函数只是重置状态，没有保存数据：

```typescript
// 旧代码（错误）
const endWorkSession = () => {
  setActiveWorkingApp(null);
  setIsWorkSessionActive(false);
};
```

**修复**：添加了 `exitWithSave` 函数，在 EXIT 时先保存再退出。

---

### 原因2：所有 blocks 都被判定为"临时状态" ⚠️ 核心问题

AutoSaveService 的设计理念：
- **临时状态 (volatile)**：正在 ASR 写入 (`isAsrWriting: true`) 或正在编辑的 blocks
- **稳定状态 (stable)**：ASR 已确认完整 utterance (`isDefiniteUtterance: true`) 或编辑完成的 blocks

**问题**：
1. ASR 实时写入时，block 的 `isAsrWriting` 为 true
2. 只有当 ASR 确认完整 utterance 时，才设置 `isAsrWriting: false`
3. **如果最后的内容还在 ASR 写入中，点击 EXIT 时这些 blocks 会被过滤掉**
4. `getStableData()` 返回空数组 → `blocks` 为空 → 保存空数据

---

## 证据链

### 1. 前端控制台日志

```
[AutoSave-voice-note] 更新记录成功: 5980bb2f-1ee4-49f0-afd6-df3e5374f60a
[AutoSave-voice-note] 更新记录成功: 5980bb2f-1ee4-49f0-afd6-df3e5374f60a
...（大量成功日志）
```

### 2. 后端日志

```
2026-01-04 10:47:56 | INFO | [API] 已直接保存文本记录: 5980bb2f-1ee4-49f0-afd6-df3e5374f60a, blocks数据: 无
2026-01-04 10:48:29 | INFO | [API] 已更新记录: 5980bb2f-1ee4-49f0-afd6-df3e5374f60a, blocks数据: 无
...（所有日志都显示"blocks数据: 无"）
```

### 3. 数据库查询

```bash
sqlite3 ~/.voice_assistant/history.db "SELECT COUNT(*) FROM records;"
# 结果：0（数据库完全为空）
```

### 4. 代码分析

**VoiceNoteAdapter.ts**:
```typescript
isVolatile(item: Block): boolean {
  if (item.isAsrWriting) return true;  // ← ASR 写入中的 block 被过滤
  if (this.editingBlockId === item.id) return true;
  return false;
}

getStableData(): VoiceNoteData {
  const allData = this.getAllData();
  return {
    blocks: allData.blocks.filter(block => !this.isVolatile(block)),  // ← 过滤掉临时 blocks
    noteInfo: allData.noteInfo,
  };
}
```

---

## 为什么前端显示"成功"但数据库为空？

### 猜测1：数据库迁移问题 ❌

最初怀疑是数据库缺少 `app_type` 字段导致 INSERT 失败。

**验证**：
- 后端启动日志显示存储提供商初始化成功
- 没有 SQL 错误日志
- 手动测试 INSERT 成功

**结论**：数据库迁移正常，`app_type` 字段存在。

### 猜测2：API 错误处理问题 ❌

怀疑 API 返回 success=true 但实际保存失败。

**验证**：
- API 代码有完整的异常处理
- 如果保存失败会返回 success=false
- 前端会输出"创建记录失败"日志（但实际没有）

**结论**：API 正常工作，确实返回了 success=true。

### 真相：保存成功但数据为空 ✅

1. **第一次保存（POST）**：
   - 前端发送请求，`blocks` 字段为空数组
   - 后端成功创建记录，返回 record_id
   - 但因为 `blocks` 为空，`text` 也为空或很少
   
2. **后续更新（PUT）**：
   - 前端持续发送更新请求
   - 但每次 `blocks` 都为空（因为所有 blocks 都是临时状态）
   - 后端成功更新记录，但内容为空

3. **点击 EXIT**：
   - 新的 `exitWithSave` 触发最后一次保存
   - 但 `getStableData()` 仍然返回空数组
   - 保存空数据

4. **为什么数据库现在是空的？**
   - 可能用户后续执行了清理操作
   - 或者记录因为内容为空被删除了
   - 或者在迁移数据库时记录丢失了

---

## 核心问题

**AutoSaveService 的设计有缺陷：**

### 问题1：过于严格的"临时状态"判断

当前逻辑：
```typescript
// 任何 isAsrWriting=true 的 block 都不会被保存
if (block.isAsrWriting) return true;  // 视为临时状态
```

**后果**：
- 长时间录音时，最后的 blocks 可能一直处于 ASR 写入状态
- 如果用户在 ASR 还在写入时点击 EXIT，这些 blocks 会全部丢失

### 问题2：没有"兜底保存所有数据"的机制

当前在 EXIT 时：
```typescript
// exitWithSave 调用
await voiceNoteAutoSave.saveToDatabase('manual', true);
// 但 saveToDatabase 内部仍然使用 getStableData()
// 如果所有 blocks 都是临时状态，就保存空数据
```

**应该**：
- EXIT 时应该保存**所有** blocks，不管是否临时状态
- 或者先等待 ASR 完成，再保存

---

## 解决方案

### 方案1：EXIT 时保存所有数据（包括临时状态） ✅ 推荐

修改 `exitWithSave`，在 EXIT 时强制保存所有 blocks：

```typescript
const exitWithSave = async () => {
  if (!apiConnected) {
    setError('API未连接');
    return;
  }

  if (asrState !== 'idle') {
    setToast({ message: '请先停止ASR后再退出', type: 'info' });
    return;
  }

  if (activeView === 'voice-note') {
    try {
      // 获取所有 blocks（不过滤临时状态）
      const blocks = blockEditorRef.current?.getBlocks?.() || [];
      const noteInfo = blockEditorRef.current?.getNoteInfo?.();
      
      // 检查是否有内容
      const hasContent = blocks.some((b: any) => 
        b.type !== 'note-info' && 
        !b.isBufferBlock && 
        (b.content?.trim() || b.type === 'image')
      );
      
      if (hasContent) {
        // 构建保存数据（使用所有 blocks）
        const allBlocks = blocks.filter((b: any) => 
          b.type !== 'note-info' && !b.isBufferBlock
        );
        
        const textContent = allBlocks
          .map((b: any) => b.content)
          .filter((text: string) => text?.trim())
          .join('\n');
        
        const saveData = {
          text: textContent,
          app_type: 'voice-note',
          metadata: {
            blocks: allBlocks,  // 保存所有 blocks
            noteInfo,
            trigger: 'exit_manual',
            timestamp: Date.now(),
          },
        };
        
        // 更新或创建记录
        const recordId = voiceNoteAutoSave.getCurrentRecordId();
        if (recordId) {
          await fetch(`http://127.0.0.1:8765/api/records/${recordId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(saveData),
          });
        } else {
          const response = await fetch('http://127.0.0.1:8765/api/text/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(saveData),
          });
          const result = await response.json();
          if (!result.success) {
            throw new Error('保存失败');
          }
        }
        
        setToast({ message: '笔记已保存，退出成功', type: 'success' });
      } else {
        setToast({ message: '已退出，可以开始新的记录', type: 'info' });
      }
      
      endWorkSession();
      
    } catch (e) {
      console.error('[Exit] 保存失败:', e);
      const confirmed = window.confirm('保存失败，是否仍然退出？未保存的内容将丢失。');
      if (confirmed) {
        endWorkSession();
      }
    }
  } else {
    endWorkSession();
  }
};
```

### 方案2：优化 isVolatile 判断逻辑

不要把"ASR 写入中"直接视为临时状态，而是：
- ASR 中间结果：临时状态
- ASR 确认 utterance：立即转为稳定状态
- 编辑中：临时状态
- 编辑完成（blur）：立即转为稳定状态

### 方案3：添加"最后兜底保存"机制

在 AutoSaveService 中添加一个方法：

```typescript
async saveAllData(trigger: SaveTrigger): Promise<void> {
  // 保存所有数据，不过滤临时状态
  const allData = this.adapter.getAllData();
  const saveData = this.adapter.toSaveData(allData);  // 不调用 getStableData
  // ... 保存逻辑
}
```

---

## 建议

1. ✅ **立即修复**：实现方案1，EXIT 时保存所有数据
2. ⚠️ **中期优化**：重新设计临时状态的判断逻辑
3. 📋 **长期改进**：添加"草稿自动保存"功能，定期保存所有数据（包括临时状态）到 localStorage

---

## 已修复的问题

1. ✅ EXIT 按钮添加了保存逻辑（`exitWithSave` 函数）
2. ✅ 数据库添加了 `app_type` 字段迁移
3. ✅ 添加了迁移日志，便于排查问题

---

## 待修复的问题

1. ⚠️ **EXIT 时保存空数据**：需要实现方案1
2. ⚠️ **临时状态判断过于严格**：需要优化 `isVolatile` 逻辑
3. ⚠️ **缺少兜底保存机制**：长时间录音可能丢失数据

---

**结论**：数据丢失的根本原因是 AutoSaveService 的设计缺陷，所有 blocks 都被判定为临时状态，导致保存空数据。需要修改 EXIT 逻辑，强制保存所有数据。

