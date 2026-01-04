# 自动保存测试步骤

## 测试目的
检查"语音笔记"应用的自动保存机制是否正常工作，确认 blocks 和 noteInfo 是否被正确保存到数据库。

## 当前状态（测试前）
- ✅ 数据库中有 1 条记录
- ❌ 该记录的 metadata 中**没有 blocks 和 noteInfo**
- ⚠️  只有 text 内容被保存

## 测试步骤

### 1. 打开开发者工具
在 Electron 应用窗口按 `Cmd+Option+I`（macOS）打开开发者工具，查看 Console 标签。

### 2. 创建新笔记
1. 点击"开始工作"按钮
2. 在笔记中输入一些内容（通过键盘输入，不使用语音）
3. 观察控制台日志

### 3. 触发保存
等待以下任一触发器：
- ✏️ **编辑完成**: 点击其他 block 或点击空白处（失焦）
- ✅ **Block 确定**: ASR 识别完成一个句子后
- 🔄 **切换视图**: 切换到其他应用或历史记录
- ⏱️ **定期保存**: 等待 60 秒

### 4. 查看控制台日志
查找以下关键日志：
```
[VoiceNoteAdapter] 🔍 getStableData - allData
[VoiceNoteAdapter] 🔍 getStableData - stableBlocks
[VoiceNoteAdapter] 💾 toSaveData 输入
[VoiceNoteAdapter] 💾 toSaveData 输出
[AutoSave-voice-note] 🔍 stableData 检查
[AutoSave-voice-note] 💾 saveData.metadata
[AutoSave-voice-note] ✅ 更新记录成功 或 ✅ 创建记录成功
```

### 5. 检查数据库
运行以下命令查看数据库中的实际数据：
```bash
cd /Users/wangjunhui/playcode/语音桌面助手
source venv/bin/activate
python -c "
import sqlite3
import json
from pathlib import Path
import yaml

with open('config.yml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

data_dir = Path(config['storage']['data_dir']).expanduser()
db_path = data_dir / config['storage']['database']

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

cursor.execute('''
    SELECT id, text, metadata, created_at 
    FROM records 
    WHERE app_type = 'voice-note'
    ORDER BY created_at DESC 
    LIMIT 1
''')

record = cursor.fetchone()
if record:
    record_id, text, metadata_str, created_at = record
    print(f'最新记录:')
    print(f'  ID: {record_id}')
    print(f'  创建时间: {created_at}')
    print(f'  文本: {text}')
    print()
    
    if metadata_str:
        metadata = json.loads(metadata_str)
        print(f'  元数据字段: {list(metadata.keys())}')
        if 'blocks' in metadata:
            print(f'  ✅ blocks 存在，数量: {len(metadata[\"blocks\"])}')
        else:
            print(f'  ❌ blocks 不存在')
        if 'noteInfo' in metadata:
            print(f'  ✅ noteInfo 存在')
        else:
            print(f'  ❌ noteInfo 不存在')
conn.close()
"
```

## 预期结果
- ✅ 控制台显示完整的保存日志
- ✅ `stableData` 包含 blocks 和 noteInfo
- ✅ `saveData.metadata` 包含 blocks 和 noteInfo
- ✅ 数据库中的记录包含完整的 metadata

## 可能的问题

### 问题1: blocks 为空
**症状**: `getStableData - allData: totalBlocks: 0`
**原因**: `blockEditorRef.current?.getBlocks()` 返回空数组
**解决**: 检查 BlockEditor 的 ref 是否正确绑定

### 问题2: blocks 被过滤掉
**症状**: `stableBlocks: 0` 但 `totalBlocks > 0`
**原因**: 所有 blocks 都被判断为 volatile（临时状态）
**解决**: 检查 `isVolatile()` 的判断逻辑

### 问题3: metadata 未传递到后端
**症状**: 前端日志正常，但数据库中没有 blocks
**解决**: 检查 API 请求和后端保存逻辑

## 调试提示
1. 在保存前，手动调用 `blockEditorRef.current.getBlocks()` 查看 blocks
2. 检查 `editingBlockId` 状态，确认是否有 block 被错误地标记为正在编辑
3. 查看网络请求（Network 标签），确认发送到后端的数据

