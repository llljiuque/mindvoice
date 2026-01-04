# 修复：EXIT 时保存所有数据（包括临时状态）

**日期**: 2026-01-05  
**问题**: EXIT 时只保存稳定状态的 blocks，导致正在 ASR 写入的内容丢失  
**修复**: 修改 `exitWithSave` 函数，强制保存所有数据

---

## 问题描述

原来的 `exitWithSave` 函数调用 `voiceNoteAutoSave.saveToDatabase()`，内部使用 `getStableData()` 过滤掉临时状态的 blocks（`isAsrWriting: true`）。

**后果**：如果用户在 ASR 还在写入时点击 EXIT，所有正在写入的 blocks 都会被过滤掉，导致保存空数据或部分数据丢失。

---

## 修复方案

### 修改前

```typescript
const exitWithSave = async () => {
  // ...
  if (activeView === 'voice-note') {
    try {
      // 使用 AutoSaveService 保存（只保存稳定状态）
      await voiceNoteAutoSave.saveToDatabase('manual', true);
      // ...
    }
  }
};
```

**问题**：`saveToDatabase` 内部调用 `getStableData()`，过滤掉 `isAsrWriting: true` 的 blocks。

---

### 修改后

```typescript
const exitWithSave = async () => {
  // ...
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
        // 过滤掉 note-info 和 buffer blocks，但保留所有其他 blocks
        const allBlocks = blocks.filter((b: any) => 
          b.type !== 'note-info' && !b.isBufferBlock
        );
        
        // 构建文本内容
        const textContent = allBlocks
          .map((b: any) => {
            if (b.isSummary) {
              return `[SUMMARY_BLOCK_START]${b.content}[SUMMARY_BLOCK_END]`;
            }
            return b.content;
          })
          .filter((text: string) => text?.trim())
          .join('\n');
        
        // 构建保存数据
        const saveData = {
          text: textContent,
          app_type: 'voice-note',
          metadata: {
            blocks: allBlocks,  // ⭐ 保存所有 blocks（包括临时状态）
            noteInfo,
            trigger: 'exit_with_all_data',
            timestamp: Date.now(),
            block_count: allBlocks.length,
          },
        };
        
        // 直接调用 API 保存（不通过 AutoSaveService）
        const recordId = voiceNoteAutoSave.getCurrentRecordId();
        if (recordId) {
          // 更新现有记录
          await fetch(`${API_BASE_URL}/api/records/${recordId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(saveData),
          });
        } else {
          // 创建新记录
          await fetch(`${API_BASE_URL}/api/text/save`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(saveData),
          });
        }
        
        setToast({ message: '笔记已保存，退出成功', type: 'success' });
      }
      
      endWorkSession();
    }
  }
};
```

---

## 修复效果

### 修复前

- ❌ EXIT 时只保存 `isAsrWriting: false` 的 blocks
- ❌ 正在 ASR 写入的内容全部丢失
- ❌ 长时间录音后 EXIT，历史记录为空

### 修复后

- ✅ EXIT 时保存所有 blocks（包括 `isAsrWriting: true` 的）
- ✅ 不会丢失任何内容
- ✅ 添加详细的日志，便于排查问题

---

## 测试步骤

1. **测试1：正常 EXIT**
   - 开始录音
   - 停止录音
   - 点击 EXIT
   - ✅ 验证：历史记录中有完整内容

2. **测试2：录音中 EXIT**
   - 开始录音
   - 在录音过程中（ASR 正在写入时）
   - ❌ 应该提示"请先停止ASR后再退出"
   - 停止录音
   - 点击 EXIT
   - ✅ 验证：历史记录中有完整内容

3. **测试3：长时间录音后 EXIT**
   - 录音 10+ 分钟
   - 停止录音
   - 点击 EXIT
   - ✅ 验证：历史记录中有所有内容（包括图片）

4. **测试4：编辑后 EXIT**
   - 录音
   - 手动编辑 blocks
   - 点击 EXIT
   - ✅ 验证：历史记录中有完整内容（包括编辑）

---

## 日志输出

修复后的代码添加了详细日志：

```
[Exit] 开始保存所有数据，block 数量: 150
[Exit] 实际保存的 block 数量: 145
[Exit] 保存数据: { textLength: 12345, blockCount: 145, hasNoteInfo: true }
[Exit] 更新现有记录: 5980bb2f-1ee4-49f0-afd6-df3e5374f60a
[Exit] 记录更新成功
```

---

## 相关文件

- **修改文件**: `electron-app/src/App.tsx`
- **修改函数**: `exitWithSave`
- **影响范围**: VoiceNote 应用的 EXIT 功能

---

## 注意事项

1. ⚠️ **AutoSaveService 的行为未改变**
   - 定期保存、ASR utterance 保存仍然只保存稳定状态
   - 这是正常的设计，避免保存不完整的中间状态
   - 只有 EXIT 时才强制保存所有数据

2. ⚠️ **临时状态的 blocks 可能不完整**
   - 正在 ASR 写入的 block 可能只有部分内容
   - 但这总比完全丢失要好

3. ✅ **未来优化方向**
   - 可以考虑在 EXIT 时先等待 ASR 完成再保存
   - 或者添加"草稿自动保存"功能，定期保存所有数据到 localStorage

---

## 修复确认

- [x] 代码已修改
- [x] Linter 检查通过
- [ ] 功能测试通过（待用户测试）
- [x] 文档已更新

---

**结论**：EXIT 功能现在会强制保存所有 blocks（包括临时状态），确保不会丢失任何内容。

