# 数据库路径展开Bug修复

**日期**: 2026-01-04  
**问题**: 配置中的 `~/.voice_assistant/history.db` 路径未正确展开  
**状态**: ✅ 已修复

---

## 问题现象

用户界面显示有多条历史记录，但直接查询 `~/.voice_assistant/history.db` 数据库时只有1条记录。

---

## 根本原因

**路径展开Bug**：在 `src/providers/storage/sqlite.py` 中，使用 `Path(db_path)` 不会自动展开 `~` 符号。

```python
# 错误代码
db_path = config.get('path', 'history.db')
self.db_path = Path(db_path)  # 不会展开 ~
```

**后果**：
- 配置文件中的 `~/.voice_assistant/history.db` 被当作相对路径
- 实际创建在：`项目根目录/~/.voice_assistant/history.db`
- 导致存在两个数据库文件：
  1. 正确路径：`/Users/xxx/.voice_assistant/history.db`
  2. 错误路径：`/项目根目录/~/.voice_assistant/history.db` ← 后端实际使用

---

## 修复方案

### 1. 代码修复

```python
# 修复后的代码
db_path = config.get('path', 'history.db')
# 展开用户目录路径（~）
self.db_path = Path(db_path).expanduser()
self.db_path.parent.mkdir(parents=True, exist_ok=True)
```

**关键改动**：使用 `.expanduser()` 方法展开 `~` 为用户主目录。

### 2. 数据迁移

将旧数据库中的记录迁移到正确的数据库：

```bash
# 迁移脚本（已执行）
旧数据库: ./~/.voice_assistant/history.db (4条记录)
新数据库: ~/.voice_assistant/history.db (1条记录)
迁移结果: 4条新记录 + 1条现有记录 = 5条记录
```

### 3. 清理旧文件

```bash
# 删除错误的数据库文件夹
rm -rf ./~
```

---

## 验证结果

✅ 数据库路径正确展开为：`/Users/wangjunhui/.voice_assistant/history.db`  
✅ 所有5条记录已迁移  
✅ 旧的错误数据库已删除  
✅ 后端将使用正确的数据库路径  

---

## 测试步骤

1. **重启后端服务**
2. **检查启动日志**：
   ```
   [语音服务] 初始化存储提供商: path=~/.voice_assistant/history.db
   [Storage] 数据表初始化完成: /Users/xxx/.voice_assistant/history.db
   ```
3. **刷新历史记录**：应该显示5条记录
4. **测试恢复任务**：点击"📝 恢复任务"按钮，验证数据加载正常

---

## 影响范围

- ✅ 修复了数据库路径展开问题
- ✅ 保留了所有历史数据
- ✅ 确保未来使用正确的数据库位置

---

## 相关文件

- `src/providers/storage/sqlite.py` - 修复路径展开
- `config.yml` - 数据库配置（无需修改）
- `~/.voice_assistant/history.db` - 正确的数据库文件

---

## 经验教训

1. **Python 路径处理**：`Path(str)` 不会自动展开 `~`，需要显式调用 `.expanduser()`
2. **测试覆盖**：应该添加单元测试验证路径展开
3. **日志完善**：启动日志应该显示展开后的完整路径，方便调试

---

## 后续改进

- [ ] 添加路径展开的单元测试
- [ ] 改进启动日志，显示展开后的完整路径
- [ ] 考虑添加数据库路径验证逻辑


