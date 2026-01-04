# IPC 监听器累积问题修复总结

## 问题描述

用户报告：工作一段时间后，出现后台日志正常、麦克风正在使用，但语音笔记 UI 显示等待录音状态（绿色按钮），文字不再更新的问题。

## 根本原因

1. **监听器移除失败**: `ipcRenderer.removeListener()` 依赖函数引用相等性，React 组件重新渲染时创建新的函数引用，导致旧监听器无法移除
2. **监听器累积**: 热重载、视图切换可能导致多个监听器同时存在
3. **状态不同步**: 视图切换时 `blockEditorRef.current` 可能失效，但监听器仍在运行

## 修复方案

### 1. 修改 preload.ts

```typescript
// 使用 removeAllListeners 替代 removeListener
onAsrMessage: (callback: (message: any) => void) => {
  console.log('[Preload] 移除所有旧的 asr-message 监听器');
  ipcRenderer.removeAllListeners('asr-message');
  console.log('[Preload] 注册新的 asr-message 监听器');
  ipcRenderer.on('asr-message', (_event, message) => callback(message));
},
removeAllAsrMessageListeners: () => {
  console.log('[Preload] 移除所有 asr-message 监听器');
  ipcRenderer.removeAllListeners('asr-message');
},
```

### 2. 修改 App.tsx

**IPC 监听器逻辑**:
- 添加 `activeView` 到依赖数组，确保视图切换时能正确处理消息
- 在消息处理中检查当前视图，避免在错误视图更新数据
- 使用 `removeAllAsrMessageListeners` 清理监听器

**状态同步机制**:
- 在切换到 voice-note 视图时，主动从后端同步 ASR 状态
- 检测到状态不一致时自动纠正

### 3. 更新类型定义

修改 `vite-env.d.ts`，更新 `ElectronAPI` 接口。

## 修改的文件

1. `electron-app/electron/preload.ts` - IPC 接口实现
2. `electron-app/src/App.tsx` - IPC 监听器和状态同步
3. `electron-app/src/vite-env.d.ts` - TypeScript 类型定义

## 测试要点

### 关键场景

1. ✅ **正常录音**: 录音、停止功能正常
2. ✅ **视图切换**: 录音期间切换视图，状态保持同步
3. ✅ **多次切换**: 频繁切换视图，不会累积监听器
4. ✅ **热重载**: 开发环境热重载后状态正常
5. ✅ **长时间运行**: 多次录音后状态仍然正确

### 预期效果

- ✅ 监听器不会累积
- ✅ UI 状态与后端始终一致
- ✅ 视图切换不影响功能
- ✅ 热重载不导致状态错乱
- ✅ 日志与 UI 显示一致

## 相关文档

- `docs/bugfix_20260104_ipc_listener_duplication.md` - 详细问题分析
- `docs/bugfix_20260104_ipc_test_guide.md` - 完整测试指南

## 版本信息

- **修复日期**: 2026-01-04
- **影响版本**: 所有使用 IPC 轮询的版本
- **修复版本**: 下一个发布版本

## 后续优化建议

1. 监控监听器数量（开发模式）
2. 添加状态机验证
3. 实现前后端心跳对账
4. 完善错误恢复机制

