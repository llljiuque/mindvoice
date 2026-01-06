# 文档管理指南

## 📁 目标：保持根目录整洁

**核心原则**：根目录只保留 5-8 个核心文档，其他文档分类归档到 `docs/` 目录。

## 🎯 文档分类规则

### ✅ 根目录必留（4-5个）
- `README.md` - 项目介绍
- `CHANGELOG.md` - 版本变更记录
- `CONTRIBUTING.md` - 贡献指南
- `LICENSE` - 许可证

### 📂 docs/ 目录结构
```
docs/
├── guides/              # 用户和开发指南
├── design/              # 架构和技术设计
├── build/               # 构建和部署文档
└── archive/             # 过程性文档归档
    ├── bugfix/          # Bug 修复记录
    ├── refactor/        # 重构记录
    ├── feature/         # 功能实现记录
    └── investigation/   # 系统检查报告
```

### 📦 需要归档的文档

| 类型 | 特征 | 归档位置 |
|------|------|----------|
| Bug修复 | `BUGFIX_*`, `*_FIX_*` | `docs/archive/bugfix/` |
| 重构 | `*_REFACTOR_*`, `CLEANUP_*` | `docs/archive/refactor/` |
| 功能实现 | `*_IMPLEMENTATION_*`, `*_COMPLETE` | `docs/archive/feature/` |
| 系统检查 | `*_CHECK_*`, `*_REPORT`, `*_REVIEW` | `docs/archive/investigation/` |

## 🔧 使用文档管理工具

### 快速开始
```bash
# 分析并归档文档
./scripts/manage_docs.sh
```

### 功能说明
1. **自动分析**：扫描项目文档，分类统计
2. **问题识别**：发现重复、过时的文档
3. **交互式归档**：预览后选择是否执行
4. **自动索引**：归档后生成 README.md

## 🔄 文档工作流

### 开发过程中
```
1. 创建临时文档 → 放在根目录（方便AI访问）
   命名: {TYPE}_{FEATURE}.md
   示例: BUGFIX_IMAGE_UPLOAD.md

2. 开发完成后 → 提取关键信息到 CHANGELOG.md
   
3. 定期归档 → 运行 ./scripts/manage_docs.sh
```

### 版本发布时
```
1. 整理 CHANGELOG.md → 记录本版本所有重要变更

2. 运行文档管理工具 → 归档过程文档
   ./scripts/manage_docs.sh

3. 检查根目录 → 确保只保留核心文档
   ls -la *.md
```

## 📝 文档命名规范

### 临时文档（开发中）
- 格式：`{TYPE}_{TOPIC}.md`
- 示例：
  - `BUGFIX_IMAGE_UPLOAD.md` - Bug修复
  - `REFACTOR_STORAGE_LAYER.md` - 重构
  - `FEATURE_VOICE_TRANSLATION.md` - 新功能

### 正式文档（docs/）
- 格式：`{PURPOSE}_{TOPIC}.md`
- 示例：
  - `QUICK_START_MEMBERSHIP.md` - 快速开始
  - `SYSTEM_ARCHITECTURE.md` - 系统架构
  - `API_REFERENCE.md` - API文档

## 📊 文档保留策略

| 阶段 | 位置 | 保留期 |
|------|------|--------|
| **开发中** | 根目录 | 当前版本周期 |
| **已完成** | `docs/archive/` | 永久（参考价值） |
| **已废弃** | 删除 | 内容已整合或过时 |

### 何时删除文档？
- ✅ 内容已完整整合到 CHANGELOG 或其他正式文档
- ✅ 文档内容已过时且无参考价值
- ✅ 多个相似文档，保留最新/最完整版本
- ❌ 解决了罕见问题的文档（归档，不删除）

## 🤖 与 AI 协作的最佳实践

### ✅ 推荐做法
1. **开发时生成临时文档** - 方便 AI 理解上下文
2. **版本发布前归档** - 保持项目整洁
3. **关键信息写入 CHANGELOG** - 集中记录变更
4. **小改动用 Git commit** - 不需要单独文档

### ❌ 避免做法
1. 不要让 AI 生成大量重复的总结文档
2. 不要保留多个版本的同一内容（如 FINAL、SUMMARY）
3. 不要在根目录堆积超过 20 个文档

## 🎓 常见问题

**Q: 过程文档真的有必要吗？**
A: 有选择地保留：
- ✅ 复杂问题的排查过程（有参考价值）
- ✅ 重要技术决策的推演（供回顾）
- ❌ 简单功能的开发日志（无必要）
- ❌ 已整合到正式文档的内容（可删除）

**Q: 多久归档一次？**
A: 建议：
- 每个版本发布后（必须）
- 根目录文档超过 15 个时（建议）
- 季度性整理（可选）

**Q: 归档的文档会被 Git 追踪吗？**
A: 会。归档到 `docs/archive/` 的文档仍然在版本控制中，可以随时查阅历史。

---

**创建时间**: 2026-01-06  
**维护者**: MindVoice 开发团队  
**工具版本**: v1.0

