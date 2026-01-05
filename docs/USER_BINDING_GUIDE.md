# 用户绑定系统使用指南

## 概述

从本版本开始，**所有本地数据都与用户绑定**，支持：
- ✅ 用户信息管理（昵称、邮箱、头像等）
- ✅ 多设备绑定（一个用户可使用多台设备）
- ✅ 数据隔离（每个用户只能看到自己的数据）
- ✅ 登录统计（登录次数、最后登录时间）
- ✅ 历史数据迁移（自动绑定到用户）

## 数据关系

```
用户 (User)
  ├── 可绑定多个设备 (Device)
  └── 拥有多条记录 (Records)
      ├── 语音笔记 (voice-note)
      ├── 智能对话 (smart-chat)
      └── 心流写作 (voice-zen)
```

## 核心功能

### 1. 创建/更新用户资料

**API端点**: `POST /api/user/profile`

```json
{
  "device_id": "b27c8839-7b75-d875-b364-8eae13c825ac",
  "nickname": "张三",
  "email": "zhangsan@example.com",
  "bio": "这是我的个人简介",
  "avatar_url": "images/xxx.png"
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "nickname": "张三",
    "email": "zhangsan@example.com",
    "bio": "这是我的个人简介",
    "avatar_url": "images/xxx.png",
    "login_count": 1,
    "last_login_at": "2026-01-05 14:00:00",
    "created_at": "2026-01-05 13:00:00",
    "updated_at": "2026-01-05 14:00:00",
    "device_id": "b27c8839-7b75-d875-b364-8eae13c825ac"
  }
}
```

### 2. 用户登录

**API端点**: `POST /api/user/login/{device_id}`

自动更新：
- `login_count` +1
- `last_login_at` 更新为当前时间

```bash
curl -X POST http://127.0.0.1:8765/api/user/login/b27c8839-7b75-d875-b364-8eae13c825ac
```

### 3. 获取用户资料

**API端点**: `GET /api/user/profile/{device_id}`

```bash
curl http://127.0.0.1:8765/api/user/profile/b27c8839-7b75-d875-b364-8eae13c825ac
```

### 4. 绑定设备

**API端点**: `POST /api/user/bind-device`

```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "device_id": "new-device-id",
  "device_name": "我的 MacBook Pro"
}
```

### 5. 解绑设备

**API端点**: `DELETE /api/user/unbind-device/{device_id}`

### 6. 查询用户的所有设备

**API端点**: `GET /api/user/devices/{user_id}`

## 数据存储

### 创建记录（带用户绑定）

```python
from src.providers.storage.sqlite import SQLiteStorageProvider

storage = SQLiteStorageProvider()
storage.initialize(config['storage'])

# 保存记录并绑定用户
record_id = storage.save_record(
    text="这是笔记内容",
    metadata={
        "app_type": "voice-note",
        "blocks": [...]
    },
    user_id="123e4567-e89b-12d3-a456-426614174000",
    device_id="b27c8839-7b75-d875-b364-8eae13c825ac"
)
```

### 查询用户的记录

```python
# 查询指定用户的所有记录
records = storage.list_records(
    user_id="123e4567-e89b-12d3-a456-426614174000",
    app_type="voice-note",  # 可选
    limit=20,
    offset=0
)

# 查询指定设备的记录
records = storage.list_records(
    device_id="b27c8839-7b75-d875-b364-8eae13c825ac",
    limit=20
)

# 统计用户的记录数
count = storage.count_records(
    user_id="123e4567-e89b-12d3-a456-426614174000"
)
```

## 前端集成

### 1. 初始化时获取用户信息

```typescript
// App.tsx - 应用启动时
useEffect(() => {
  const initUser = async () => {
    const deviceId = await getDeviceId();
    
    // 尝试登录（如果已有用户）
    const response = await fetch(`${API_BASE_URL}/api/user/login/${deviceId}`, {
      method: 'POST'
    });
    
    const data = await response.json();
    
    if (data.success) {
      // 用户已存在，保存用户信息到状态
      setUserInfo(data.data);
    } else {
      // 用户不存在，引导创建用户资料
      showUserProfileDialog();
    }
  };
  
  initUser();
}, []);
```

### 2. 保存记录时传递用户信息

```typescript
// VoiceNote.tsx - 保存笔记
const saveNote = async () => {
  const response = await fetch(`${API_BASE_URL}/api/records`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text: noteText,
      metadata: {
        app_type: 'voice-note',
        blocks: blocks,
        user_id: userInfo.user_id,  // ⭐ 添加用户ID
        device_id: deviceId          // ⭐ 添加设备ID
      }
    })
  });
};
```

### 3. 查询记录时按用户筛选

```typescript
// History.tsx - 查询历史记录
const loadHistory = async () => {
  const params = new URLSearchParams({
    limit: '20',
    offset: '0',
    user_id: userInfo.user_id  // ⭐ 只查询当前用户的记录
  });
  
  const response = await fetch(`${API_BASE_URL}/api/records?${params}`);
  const data = await response.json();
  setRecords(data);
};
```

## 数据重置（开发阶段）

如果需要完全清空数据重新开始，可以使用系统复位脚本：

```bash
# 运行系统复位脚本
cd /Users/wangjunhui/playcode/语音桌面助手
./scripts/reset_system.sh
```

**警告**：此操作会删除所有数据，包括：
- 所有用户信息和设备绑定
- 所有历史记录（笔记、对话等）
- 所有上传的图片
- 所有知识库数据

**使用场景**：
- 开发测试阶段需要清空测试数据
- 数据库结构变更后需要重建
- 系统出现严重问题需要重置

## 多设备同步（预留）

当前版本支持多设备绑定，但尚未实现实时同步功能。未来可以基于 `user_id` 实现：

1. **云端同步**：将数据上传到服务器，多设备共享
2. **冲突解决**：基于时间戳的合并策略
3. **增量同步**：只同步变更的数据

数据库结构已为多设备同步预留字段：
- `user_id`：标识数据所有者
- `device_id`：标识数据创建设备
- `created_at`：用于时间戳比对

## 安全和隐私

### 数据隔离
- ✅ 每个用户只能访问自己的数据
- ✅ API 会根据 `device_id` 自动获取 `user_id`
- ✅ 数据库索引确保查询性能

### 敏感信息
- 邮箱等信息仅存储在本地数据库
- 不会上传到任何服务器（除非未来实现云同步功能）
- 可随时删除用户资料（级联删除所有数据）

### 删除账户

```bash
curl -X DELETE http://127.0.0.1:8765/api/user/profile/{user_id}
```

**警告**：删除用户会级联删除：
- 用户的所有设备绑定
- 用户的所有历史记录（`records` 表的数据需手动清理）

## 常见问题

### Q1: 我的历史数据会丢失吗？
**A**: 不会。运行迁移脚本会自动将历史数据绑定到用户，且会创建备份。

### Q2: 可以多个设备使用同一个账户吗？
**A**: 可以。一个用户可以绑定多个设备，所有设备的数据都属于该用户。

### Q3: 设备ID是如何生成的？
**A**: 设备ID在首次运行时自动生成（UUID v4 格式），存储在本地配置中。

### Q4: 如果不创建用户资料会怎样？
**A**: 应用仍可正常使用，但：
- 数据不会绑定到用户（`user_id` 为 NULL）
- 无法使用多设备同步功能（未来）
- 无法查看个人统计信息

### Q5: 如何重置用户信息？
**A**: 通过用户资料页面编辑，或直接调用 API 更新。

## 技术细节

### 数据库表结构

详见：[DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md)

### API参考

详见：[API_REFERENCE.md](./API_REFERENCE.md)

## 快速开始

1. **初始化配置**（首次使用）
   ```bash
   # 确保 config.yml 已正确配置
   # 特别是 storage.data_dir 配置
   ```

2. **启动应用**
   ```bash
   ./quick_start.sh
   ```

3. **首次使用**
   - 应用会自动创建数据库和所有必需的表
   - 首次进入会提示创建用户资料
   - 输入昵称、邮箱等信息（可选）

4. **验证功能**
   - 打开用户资料页面，查看个人信息
   - 创建一条笔记或对话，确认数据保存
   - 查看历史记录，确认数据与用户绑定

## 反馈和支持

如有问题，请联系：
- **开发者**: 深圳王哥 & AI
- **邮箱**: manwjh@126.com
- **GitHub**: [项目地址]

---

**最后更新**: 2026-01-05
**版本**: v1.1.0

