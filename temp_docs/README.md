# 临时文档目录

本目录用于存放开发过程中的临时文档，**不会上传到 GitHub**。

## 📝 使用说明

### 适合放在这里的文档
- 带日期的开发记录（如 `BUGFIX_XXX_20260106.md`）
- 草稿文档
- 个人笔记和想法
- 临时测试记录
- 未完成的文档

### 完成后如何处理
1. **重要内容** → 提取精华到 `CHANGELOG.md` 或正式文档
2. **过程文档** → 移动到 `docs/archive/` 对应目录
3. **无价值内容** → 直接删除

## 🔄 工作流程

```bash
# 开发时：创建临时文档
temp_docs/BUGFIX_IMAGE_UPLOAD_20260106.md

# 完成后：归档或删除
mv temp_docs/BUGFIX_IMAGE_UPLOAD_20260106.md docs/archive/bugfix/
# 或
rm temp_docs/BUGFIX_IMAGE_UPLOAD_20260106.md
```

## 💡 提示

本目录在 `.gitignore` 中，Git 会自动忽略这里的所有文件（除了本 README）。
