# AutoSaveService 迁移测试指南

**日期**: 2026-01-05  
**版本**: v1.4.1  
**测试范围**: VoiceNote 自动保存功能

---

## 📋 测试概述

本指南用于验证 VoiceNote 迁移到 AutoSaveService 后的功能完整性。

---

## ✅ 测试前准备

### 1. 启动应用

```bash
cd /Users/wangjunhui/playcode/语音桌面助手
./quick_start.sh
```

### 2. 打开开发者工具

- 按 `Cmd+Option+I` (macOS) 或 `Ctrl+Shift+I` (Windows/Linux)
- 查看 Console 标签页，观察日志输出

### 3. 检查初始状态

在控制台中应该看到：

```
[App] VoiceNote 自动保存服务已启动
[AutoSaveService] voice-note 服务已启动
```

---

## 🧪 测试用例

### 测试 1: localStorage 临时保存

**目的**: 验证正在编辑的 block 会自动保存到 localStorage

**步骤**:
1. 点击"开始工作"按钮
2. 输入一些文字（例如："测试临时保存"）
3. 等待 1-2 秒
4. 打开 DevTools → Application → Local Storage → 查看 `voice-note-volatile-blocks`

**预期结果**:
- ✅ localStorage 中应包含当前正在编辑的 block 数据
- ✅ 控制台输出：`[AutoSaveService] 临时保存 volatile blocks`

---

### 测试 2: ASR 确定 utterance 保存

**目的**: 验证 ASR 确认语句后立即保存到数据库

**步骤**:
1. 点击录音按钮开始录音
2. 说一句话（例如："今天天气真好"）
3. 停止录音
4. 观察控制台输出

**预期结果**:
- ✅ 控制台输出：`[保存触发] ASR 确认 utterance`
- ✅ 控制台输出：`[AutoSaveService] 保存到数据库 (trigger: definite_utterance, immediate: true)`
- ✅ 控制台输出：`[AutoSaveService] 创建记录成功` 或 `[AutoSaveService] 更新记录成功`

---

### 测试 3: 编辑完成保存

**目的**: 验证编辑 block 失焦后防抖保存到数据库

**步骤**:
1. 点击一个 block 开始编辑
2. 输入一些文字（例如："编辑测试内容"）
3. 点击 block 外部区域，使其失焦
4. 等待 3 秒
5. 观察控制台输出

**预期结果**:
- ✅ 控制台输出：`[AutoSaveService] 保存到数据库 (trigger: edit_complete, immediate: false)`
- ✅ 3 秒后控制台输出：`[AutoSaveService] 更新记录成功`

---

### 测试 4: 笔记信息变更保存

**目的**: 验证笔记标题等信息变更后保存

**步骤**:
1. 点击顶部的"无标题笔记"输入框
2. 输入标题（例如："测试笔记"）
3. 点击外部区域
4. 等待 3 秒
5. 观察控制台输出

**预期结果**:
- ✅ 控制台输出：`[保存触发] 笔记信息变更`
- ✅ 控制台输出：`[AutoSaveService] 保存到数据库 (trigger: content_change, immediate: false)`
- ✅ 3 秒后保存成功

---

### 测试 5: 长时间编辑兜底保存

**目的**: 验证长时间编辑（超过30秒）会触发兜底保存

**步骤**:
1. 点击一个 block 开始编辑
2. 持续输入文字，保持编辑状态超过 30 秒
3. 观察控制台输出

**预期结果**:
- ✅ 30 秒后控制台输出：`[AutoSaveService] 长时间编辑兜底保存`
- ✅ 控制台输出：`[AutoSaveService] 保存到数据库 (trigger: edit_complete)`

---

### 测试 6: 定期保存

**目的**: 验证每60秒自动检查并保存

**步骤**:
1. 添加一些内容后不要编辑
2. 等待 60 秒
3. 观察控制台输出

**预期结果**:
- ✅ 60 秒后控制台输出：`[AutoSaveService] 定期保存检查`
- ✅ 如果有内容，输出：`[AutoSaveService] 保存到数据库 (trigger: periodic)`

---

### 测试 7: 数据库恢复

**目的**: 验证应用重启后能从数据库恢复最近的笔记

**步骤**:
1. 在 VoiceNote 中创建一些内容
2. 等待保存完成（观察控制台）
3. 关闭应用
4. 重新启动应用
5. 观察 VoiceNote 是否恢复了之前的内容

**预期结果**:
- ✅ 控制台输出：`[AutoSaveService] 从数据库恢复`
- ✅ 控制台输出：`[AutoSaveService] 恢复记录成功`
- ✅ 界面显示之前的内容
- ✅ Toast 提示：`已恢复最近的笔记`

---

### 测试 8: 临时数据优先恢复

**目的**: 验证 localStorage 临时数据优先于数据库恢复

**步骤**:
1. 在 VoiceNote 中创建一些内容
2. 等待保存到数据库
3. 继续编辑，添加新内容（不要等待保存）
4. 立即刷新页面（按 F5）
5. 观察是否恢复了最新的编辑内容

**预期结果**:
- ✅ 控制台输出：`[AutoSaveService] 检测到更新的临时数据`
- ✅ 控制台输出：`[AutoSaveService] 从 localStorage 恢复 volatile blocks`
- ✅ 界面显示最新的编辑内容（包括未保存到数据库的部分）

---

### 测试 9: 切换应用停止保存服务

**目的**: 验证切换到其他应用时，VoiceNote 保存服务会停止

**步骤**:
1. 在 VoiceNote 中添加内容
2. 点击侧边栏切换到"语音助手"
3. 观察控制台输出

**预期结果**:
- ✅ 控制台输出：`[App] VoiceNote 自动保存服务已停止`
- ✅ 控制台输出：`[AutoSaveService] voice-note 服务已停止`
- ✅ 停止定期保存和临时保存

---

### 测试 10: ASR 录音时阻止切换

**目的**: 验证录音时无法切换应用

**步骤**:
1. 点击录音按钮开始录音
2. 尝试点击侧边栏切换到其他应用
3. 观察是否被阻止

**预期结果**:
- ✅ Toast 警告：`语音笔记正在录音中，请先停止录音再切换界面`
- ✅ 控制台输出：`[导航] 阻止切换：ASR 正在录音中`
- ✅ 应用保持在 VoiceNote 页面

---

### 测试 11: 服务状态同步

**目的**: 验证编辑状态正确同步到 AutoSaveService

**步骤**:
1. 点击一个 block 开始编辑
2. 在控制台执行：
   ```javascript
   // 这需要通过控制台调试来验证内部状态
   ```
3. 观察控制台输出

**预期结果**:
- ✅ 控制台输出显示 `editingBlockId` 已更新
- ✅ 临时保存只保存当前编辑的 block

---

## 🐛 可能的问题和解决方案

### 问题 1: 控制台没有看到日志

**原因**: 日志级别设置或控制台被清空

**解决方案**:
1. 确保控制台 Filter 设置为 "All levels"
2. 检查 Console Preserve log 是否勾选

### 问题 2: localStorage 保存失败

**原因**: localStorage 可能被禁用或已满

**解决方案**:
1. 检查浏览器 localStorage 设置
2. 清除旧的 localStorage 数据

### 问题 3: 数据库保存失败

**原因**: 后端 API 未运行或网络问题

**解决方案**:
1. 检查后端是否运行：`http://127.0.0.1:8765/health`
2. 查看后端日志：`/Users/wangjunhui/playcode/语音桌面助手/logs/`

### 问题 4: 恢复功能不工作

**原因**: 记录时间超过1小时或没有历史记录

**解决方案**:
1. 检查数据库中是否有记录
2. 确保记录时间在1小时内
3. 检查控制台恢复日志

---

## 📊 测试结果记录表

| 测试用例 | 状态 | 备注 |
|---------|------|------|
| 1. localStorage 临时保存 | ⬜ | |
| 2. ASR 确定 utterance 保存 | ⬜ | |
| 3. 编辑完成保存 | ⬜ | |
| 4. 笔记信息变更保存 | ⬜ | |
| 5. 长时间编辑兜底保存 | ⬜ | |
| 6. 定期保存 | ⬜ | |
| 7. 数据库恢复 | ⬜ | |
| 8. 临时数据优先恢复 | ⬜ | |
| 9. 切换应用停止服务 | ⬜ | |
| 10. ASR 录音时阻止切换 | ⬜ | |
| 11. 服务状态同步 | ⬜ | |

**状态图例**:
- ⬜ 待测试
- ✅ 通过
- ❌ 失败
- ⚠️ 部分通过

---

## 📝 测试报告模板

```markdown
## VoiceNote AutoSaveService 测试报告

**测试时间**: YYYY-MM-DD HH:mm
**测试人**: 
**版本**: v1.4.1

### 测试结果

- 总用例数: 11
- 通过: X
- 失败: X
- 通过率: X%

### 发现的问题

1. [问题描述]
   - 严重程度: 高/中/低
   - 重现步骤: ...
   - 预期结果: ...
   - 实际结果: ...

### 建议

1. [建议内容]

### 总结

[测试总结]
```

---

## 🎯 下一步

测试完成后：

1. ✅ 记录测试结果
2. ✅ 修复发现的 bug
3. ✅ 更新测试用例（如有新功能）
4. ✅ 进行 VoiceChat 和 VoiceZen 的迁移

---

## 📚 相关文档

- [统一自动保存架构](./architecture_unified_autosave.md)
- [VoiceNote 迁移文档](./migration_voicenote_autosave.md)
- [智能自动保存功能](./feature_20260105_smart_autosave.md)

---

**祝测试顺利！** 🚀

