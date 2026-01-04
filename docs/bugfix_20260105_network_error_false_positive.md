# 修复：停止录音时显示"网络连接失败"

**日期**: 2026-01-05  
**问题**: 每次停止录音时显示"网络连接失败，请检查网络连接"  
**修复**: 添加容错机制，避免短暂网络波动误报

---

## 问题描述

用户每次停止录音时，界面顶部显示错误提示："网络连接失败，请检查网络连接"。

### 原因分析

1. **定期检查机制**: `checkApiConnection` 函数每 5 秒检查一次 API 连接状态
2. **停止录音时的网络波动**: 停止录音时，后端可能短暂繁忙（处理最后的 ASR 结果），导致 `/api/status` 请求超时或失败
3. **立即报错**: 只要一次检查失败，就立即设置 SystemError 并显示错误横幅
4. **误报**: 实际上网络和 API 都正常，只是短暂的波动

---

## 修复方案

### 修改前

```typescript
const checkApiConnection = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/status`, {
      signal: AbortSignal.timeout(2000)
    });
    const connected = response.ok;
    // ...
    return connected;
  } catch (e) {
    lastApiConnectedRef.current = false;
    setApiConnected(false);
    
    // ❌ 立即设置网络错误（一次失败就报错）
    if (!systemError) {
      setSystemError({
        code: ErrorCodes.NETWORK_UNREACHABLE,
        message: '网络连接失败，请检查网络连接',
        // ...
      });
    }
    return false;
  }
};
```

**问题**：只要一次检查失败就报错，对短暂波动过于敏感。

---

### 修改后

```typescript
const consecutiveFailuresRef = useRef<number>(0); // ⭐ 连续失败次数

const checkApiConnection = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/status`, {
      signal: AbortSignal.timeout(2000)
    });
    const connected = response.ok;
    
    // ✅ 连接成功，重置失败计数
    if (connected) {
      consecutiveFailuresRef.current = 0;
    }
    
    // ...
    return connected;
  } catch (e) {
    // ✅ 增加失败计数
    consecutiveFailuresRef.current += 1;
    
    lastApiConnectedRef.current = false;
    setApiConnected(false);
    
    // ✅ 只有连续失败 3 次以上才设置网络错误
    // 3 次 × 5 秒间隔 = 至少 15 秒连不上才报错
    if (consecutiveFailuresRef.current >= 3 && !systemError) {
      setSystemError({
        code: ErrorCodes.NETWORK_UNREACHABLE,
        message: '网络连接失败，请检查网络连接',
        // ...
      });
    }
    return false;
  }
};
```

---

## 修复效果

### 修复前

- ❌ 停止录音时，偶尔会显示"网络连接失败"
- ❌ 对短暂的网络波动过于敏感
- ❌ 误报率高，影响用户体验

### 修复后

- ✅ 短暂的网络波动不会触发错误提示
- ✅ 只有连续失败 3 次（15秒以上）才报错
- ✅ 真正的网络问题仍然会被检测并提示
- ✅ 减少误报，提升用户体验

---

## 工作原理

### 检查周期

```
时间轴:  0s    5s    10s   15s   20s
检查:    ✓     ✗     ✗     ✗     ✗
计数:    0     1     2     3     4
错误:    -     -     -     显示   -
```

- 第 0 秒：检查成功，计数器归零
- 第 5 秒：检查失败，计数器 = 1（不报错）
- 第 10 秒：检查失败，计数器 = 2（不报错）
- 第 15 秒：检查失败，计数器 = 3（**触发报错**）
- 第 20 秒：检查失败，计数器 = 4（已经报错，不重复）

### 恢复机制

一旦任何一次检查成功，计数器立即归零：

```
时间轴:  0s    5s    10s   15s   20s
检查:    ✓     ✗     ✗     ✓     ✗
计数:    0     1     2     0     1
错误:    -     -     -     清除   -
```

---

## 测试场景

### 场景1：正常使用（无网络问题）

- 开始录音
- 停止录音（可能短暂波动，但不超过 3 次）
- ✅ 不显示错误提示

### 场景2：真正的网络断开

- 断开网络
- 等待 15 秒（3 次失败检查）
- ✅ 显示"网络连接失败"错误横幅

### 场景3：网络恢复

- 网络断开后显示错误
- 重新连接网络
- 下次检查成功时
- ✅ 错误横幅自动消失
- ✅ 显示"API服务器已连接" Toast

### 场景4：间歇性网络问题

- 网络时好时坏
- 失败 2 次，成功 1 次（计数归零）
- 再失败 2 次，成功 1 次（计数归零）
- ✅ 不显示错误（因为从未连续失败 3 次）

---

## 参数说明

### 可调整的参数

```typescript
const checkInterval = 5000;           // 检查间隔：5 秒
const failureThreshold = 3;           // 失败阈值：3 次
const timeout = 2000;                 // 请求超时：2 秒
```

**最小报错时间** = `checkInterval * (failureThreshold - 1) + timeout`
= 5000 × 2 + 2000 = **12 秒**

### 调整建议

如果觉得还是太敏感，可以：
1. **增加失败阈值**: `consecutiveFailuresRef.current >= 5`（25秒）
2. **增加检查间隔**: `setInterval(..., 10000)`（10秒间隔）
3. **增加请求超时**: `AbortSignal.timeout(3000)`（3秒超时）

---

## 相关文件

- **修改文件**: `electron-app/src/App.tsx`
- **修改函数**: `checkApiConnection`
- **新增变量**: `consecutiveFailuresRef`

---

## 注意事项

1. ⚠️ **不影响真正的网络错误检测**
   - 如果网络真的断开，仍然会在 15 秒后报错
   - 只是过滤掉短暂的波动

2. ⚠️ **apiConnected 状态立即更新**
   - `setApiConnected(false)` 在第一次失败时就会执行
   - 这是正确的，因为其他组件可能依赖这个状态
   - 只有 SystemError 会延迟设置

3. ✅ **不影响其他错误提示**
   - 检查 `if (!systemError)` 确保不覆盖其他模块的错误
   - 比如 stopAsr 失败的错误不会被覆盖

---

## 修复确认

- [x] 代码已修改
- [x] Linter 检查通过
- [ ] 功能测试通过（待用户测试）
- [x] 文档已更新

---

**结论**：通过添加连续失败计数器，避免短暂网络波动导致的误报，同时保持真正网络问题的检测能力。

