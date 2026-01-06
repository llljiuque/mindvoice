# 数据库版本信息

## 当前版本：v1.2.1（会员系统重构）

**发布日期**: 2026-01-05

### v1.2.1 核心变化
**会员系统重构** - 会员等级从设备迁移到用户：
- ✅ `memberships` 表：主键从 `device_id` 改为 `user_id`
- ✅ `consumption_records` 表：新增 `user_id` 字段
- ✅ `monthly_consumption` 表：联合主键 `(user_id, device_id, year, month)`
- ✅ 一个用户的所有设备共享会员权益
- ✅ 消费记录区分设备，但额度按用户统计
- ✅ 新增完整的用户注册流程：用户注册→设备绑定→授权会员

## 数据库设计

### 核心特性

本版本为**基准版本**，数据库设计包含完整的用户管理和高级功能：

✅ **用户管理**
- 用户信息存储（昵称、邮箱、头像等）
- 登录统计（登录次数、最后登录时间）
- 软删除支持（可恢复）
- 注册时间记录

✅ **多设备支持**
- 一个用户可绑定多个设备
- 一个设备只能绑定一个用户
- 设备绑定时间记录

✅ **数据绑定**
- 所有记录绑定到用户和设备
- 按用户隔离数据
- 支持多设备数据共享（预留）

✅ **高级功能**
- 软删除（记录和用户）
- 收藏和归档
- 全文搜索（FTS5）
- 标签系统
- 使用统计
- 备份记录

✅ **会员系统**
- 设备注册和管理
- 会员等级（免费/VIP/Pro/Pro+）
- 消费记录追踪（ASR/LLM）
- 月度消费统计
- 激活码管理

### 表结构

#### 1. `users` 表
- 用户基本信息
- 登录统计数据
- 注册和更新时间

#### 2. `user_devices` 表
- 用户与设备的绑定关系
- 支持多设备管理

#### 3. `records` 表
- 历史记录（笔记、对话等）
- 绑定到用户和设备
- 支持按用户/设备筛选

详细结构请参考：[DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md)

## 版本历史

### v1.2.0 - 完整功能基准版本（2026-01-05）⭐

**新增功能**：
- ✅ 软删除机制（记录和用户）
- ✅ 收藏和归档功能
- ✅ 全文搜索（FTS5，10-100倍性能提升）
- ✅ 标签系统（创建、管理、关联）
- ✅ 使用统计表（按日统计）
- ✅ 备份记录表（追踪备份操作）
- ✅ 数据库版本管理

**数据库变更**：
- `users` 表：添加 `is_deleted`、`deleted_at` 字段
- `records` 表：添加 `is_deleted`、`deleted_at`、`is_starred`、`is_archived`、`updated_at` 字段
- 新增 `records_fts` 虚拟表（FTS5全文搜索）
- 新增 `tags` 表（标签管理）
- 新增 `record_tags` 表（标签关联）
- 新增 `daily_stats` 表（使用统计）
- 新增 `backup_logs` 表（备份日志）
- 新增 `schema_versions` 表（版本管理）
- 添加8个新索引和3个FTS5触发器

**API变更**：
- 新增标签管理API（9个端点）
- 新增搜索API
- 增强用户管理API（软删除/恢复）

**性能优化**：
- FTS5 全文搜索：10-100倍性能提升
- 部分索引优化（减少索引大小）
- 查询优化（软删除默认过滤）

**兼容性**：
- 作为新基准版本，不考虑向后兼容
- 使用 `reset_system.sh` 全新初始化

### v1.1.0 - 用户绑定系统（已废弃）

**注意**：v1.1.0 已被 v1.2.0 取代，作为基准版本。

### v1.0.0 - 初始版本（已废弃）

**注意**：v1.0.0 已被完全重构。

## 开发指南

### 初次启动

```bash
# 1. 确保配置文件正确
cat config.yml

# 2. 启动应用
./quick_start.sh

# 3. 应用会自动创建数据库和所有表
```

### 重置系统（开发阶段）

```bash
# 完全清空所有数据，重新初始化
./scripts/reset_system.sh
```

**警告**：此操作会删除所有数据！

### 数据库位置

数据库路径由 `config.yml` 配置决定：

```yaml
storage:
  data_dir: ~/Library/Application Support/MindVoice  # macOS
  database: database/history.db
```

完整路径：`~/Library/Application Support/MindVoice/database/history.db`

### 查看数据库

```bash
# 获取数据库路径
DATA_DIR=$(grep 'data_dir:' config.yml | awk '{print $2}' | sed 's/~/$HOME/g')
DB_PATH="$DATA_DIR/database/history.db"

# 查看表结构
sqlite3 "$DB_PATH" ".schema users"
sqlite3 "$DB_PATH" ".schema user_devices"
sqlite3 "$DB_PATH" ".schema records"

# 查看数据
sqlite3 "$DB_PATH" "SELECT * FROM users;"
sqlite3 "$DB_PATH" "SELECT * FROM user_devices;"
sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM records;"
```

## 未来规划

### v1.2.0（计划中）
- 用户偏好设置表
- 登录历史表
- 设备管理增强
- 数据统计功能

### v2.0.0（长期规划）
- 云端同步支持
- 多设备实时同步
- 冲突解决机制
- 数据导出/导入

## 注意事项

### 开发阶段

当前处于**开发阶段**，数据库设计可能会继续调整：

1. 使用 `./scripts/reset_system.sh` 清空测试数据
2. 不需要迁移脚本（当前版本是基准）
3. 数据库会自动创建所有必需的表和字段

### 生产环境（未来）

生产环境部署时需要注意：

1. 备份现有数据库
2. 检查数据库版本
3. 运行必要的迁移脚本（如果有）
4. 验证数据完整性

## 相关文档

- [数据库表结构](./DATABASE_SCHEMA.md) - 详细的表结构说明
- [用户绑定指南](./USER_BINDING_GUIDE.md) - 用户系统使用指南
- [API参考](./API_REFERENCE.md) - API接口文档

---

**维护者**: 深圳王哥 & AI  
**联系方式**: manwjh@126.com  
**最后更新**: 2026-01-05

