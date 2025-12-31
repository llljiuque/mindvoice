# 版本管理指南

## 概述

本项目采用集中式版本管理，所有版本信息都从 `electron-app/src/version.ts` 统一获取。

## 版本号规范

### 语义化版本 (Semantic Versioning)

版本号格式：`MAJOR.MINOR.PATCH`

- **MAJOR**: 重大更新，可能包含不兼容的 API 变更
- **MINOR**: 新增功能，向后兼容
- **PATCH**: 问题修复，向后兼容

示例：
- `1.0.0` → `1.0.1`: 修复bug
- `1.0.1` → `1.1.0`: 新增功能
- `1.1.0` → `2.0.0`: 重大更新

## 版本信息配置

### 主配置文件

**文件位置**: `electron-app/src/version.ts`

```typescript
export const APP_VERSION = {
  version: '1.0.0',           // 版本号
  releaseDate: '2025-12-31',  // 发布日期 (YYYY-MM-DD)
  name: 'MindVoice',          // 应用名称
  description: 'AI驱动的语音桌面助手'  // 应用描述
} as const;
```

### 同步配置文件

版本号还需要同步更新到：
- `electron-app/package.json` 的 `version` 字段

## 版本更新流程

### 方法一：使用自动化脚本（推荐）

```bash
# 自动使用当前日期作为发布日期
./update_version.sh 1.1.0

# 或手动指定发布日期
./update_version.sh 1.1.0 2025-12-31
```

脚本会自动更新：
1. `electron-app/src/version.ts` 中的 `version` 和 `releaseDate`
2. `electron-app/package.json` 中的 `version`

### 方法二：手动更新

1. **更新 version.ts**
   ```typescript
   // electron-app/src/version.ts
   export const APP_VERSION = {
     version: '1.1.0',          // 更新版本号
     releaseDate: '2025-12-31', // 更新发布日期（使用当前日期）
     name: 'MindVoice',
     description: 'AI驱动的语音桌面助手'
   } as const;
   ```

2. **更新 package.json**
   ```json
   {
     "name": "mindvoice",
     "version": "1.1.0",  // 保持与 version.ts 一致
     ...
   }
   ```

3. **（可选）更新 CHANGELOG**
   记录本次版本的主要变更

## 版本号使用

### 在 TypeScript/React 中使用

```typescript
import { APP_VERSION } from './version';

// 获取版本号
const version = APP_VERSION.version;

// 获取发布日期
const releaseDate = APP_VERSION.releaseDate;

// 获取应用名称
const appName = APP_VERSION.name;
```

### 示例：在组件中使用

```typescript
import { APP_VERSION } from '../../version';

export const AboutView: React.FC = () => {
  const { version, releaseDate } = APP_VERSION;
  
  return (
    <div>
      <p>版本号: {version}</p>
      <p>发布日期: {releaseDate}</p>
    </div>
  );
};
```

## 时间和日期规范

### 日期格式

- **显示格式**: `YYYY-MM-DD` (如 2025-12-31)
- **时间戳格式**: ISO 8601 格式
- **时区**: 默认使用本地时区

### 重要原则

1. **使用当前时间**: 必须使用系统提供的当前日期，不要硬编码过期日期
2. **发布日期准确性**: 版本发布日期应该是实际发布的日期
3. **避免硬编码**: 不要在代码中硬编码具体日期，使用相对时间或动态获取

### 示例

```typescript
// ✅ 正确：动态获取当前日期
const today = new Date().toISOString().split('T')[0];

// ✅ 正确：使用相对时间
const yesterday = new Date(Date.now() - 86400000);

// ❌ 错误：硬编码过期日期
const date = '2025-01-01'; // 这个日期可能已经过期
```

## 版本发布检查清单

发布新版本前，请确认：

- [ ] 更新了 `electron-app/src/version.ts` 中的版本号
- [ ] 更新了 `electron-app/src/version.ts` 中的发布日期（使用当前日期）
- [ ] 同步更新了 `electron-app/package.json` 中的版本号
- [ ] （可选）在 CHANGELOG 中记录了主要变更
- [ ] 测试了应用的关于页面显示正确的版本信息
- [ ] 提交代码时使用了正确的 commit 格式

## Git 提交规范

版本更新的提交信息格式：

```bash
# 版本更新
git commit -m "chore(version): 更新版本号到 1.1.0"

# 带变更说明
git commit -m "chore(version): 更新版本号到 1.1.0

- 新增语音助手功能
- 优化ASR性能
- 修复若干bug"
```

## 常见问题

### Q: 为什么要集中管理版本号？

A: 集中管理避免了多处维护版本号导致的不一致问题，确保整个应用使用统一的版本信息。

### Q: 可以只更新 package.json 吗？

A: 不可以。必须同时更新 `version.ts` 和 `package.json`，因为应用界面从 `version.ts` 读取版本信息。

### Q: 发布日期可以使用未来的日期吗？

A: 不建议。发布日期应该是实际发布的日期，使用未来日期会造成混淆。

### Q: 如何查看当前版本？

A: 
1. 在应用中：点击侧边栏的"关于"按钮
2. 在代码中：查看 `electron-app/src/version.ts`
3. 在 package.json 中：查看 `version` 字段

## 自动化工具

### update_version.sh

版本更新脚本，自动化更新版本号和发布日期。

**用法**:
```bash
./update_version.sh <版本号> [发布日期]
```

**示例**:
```bash
# 使用当前日期
./update_version.sh 1.2.0

# 指定发布日期
./update_version.sh 1.2.0 2025-12-31
```

**功能**:
- 自动更新 `version.ts` 中的版本号和发布日期
- 自动更新 `package.json` 中的版本号
- 显示更新结果和需要检查的文件

---

**最后更新**: 2025-12-31

