# 会员系统重新设计方案

**日期**: 2026-01-05  
**版本**: v1.2.1  
**原因**: 会员系统应以用户为中心，而不是设备

---

## 🎯 设计原则

### 核心理念
- **会员权益属于用户**，而不是设备
- 一个用户可以有多个设备
- 所有设备共享同一会员等级和额度
- 但消费记录按设备区分（便于统计）

---

## 📊 表结构调整

### 1. memberships 表（重大变更）

#### 旧结构（❌ 错误）
```sql
CREATE TABLE memberships (
    device_id TEXT PRIMARY KEY,  -- ❌ 以设备为主键
    tier TEXT NOT NULL DEFAULT 'free',
    ...
)
```

#### 新结构（✅ 正确）
```sql
CREATE TABLE memberships (
    user_id TEXT PRIMARY KEY,  -- ✅ 以用户为主键
    tier TEXT NOT NULL DEFAULT 'free',
    status TEXT NOT NULL DEFAULT 'active',
    subscription_period INTEGER,
    activated_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP,
    auto_renew INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    CHECK (subscription_period IS NULL OR (subscription_period >= 1 AND subscription_period <= 120)),
    CHECK (tier IN ('free', 'vip', 'pro', 'pro_plus')),
    CHECK (status IN ('active', 'expired', 'pending'))
)
```

### 2. monthly_consumption 表（调整）

#### 旧结构
```sql
PRIMARY KEY (device_id, year, month)  -- 按设备统计
```

#### 新结构（保留 device_id，但添加 user_id）
```sql
CREATE TABLE monthly_consumption (
    user_id TEXT NOT NULL,  -- ✅ 新增：关联用户
    device_id TEXT NOT NULL,  -- 保留：区分设备
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    asr_duration_ms INTEGER NOT NULL DEFAULT 0,
    llm_prompt_tokens INTEGER NOT NULL DEFAULT 0,
    llm_completion_tokens INTEGER NOT NULL DEFAULT 0,
    llm_total_tokens INTEGER NOT NULL DEFAULT 0,
    record_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    PRIMARY KEY (user_id, device_id, year, month),  -- 用户+设备+月份
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (device_id) REFERENCES devices(device_id)
)
```

### 3. consumption_records 表（调整）

#### 新增 user_id 字段
```sql
CREATE TABLE consumption_records (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,  -- ✅ 新增：关联用户
    device_id TEXT NOT NULL,  -- 保留：区分设备
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    type TEXT NOT NULL,
    amount REAL NOT NULL,
    unit TEXT NOT NULL,
    model_source TEXT DEFAULT 'vendor',
    details TEXT,
    session_id TEXT,
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (device_id) REFERENCES devices(device_id)
)
```

### 4. devices 表（保持不变）
```sql
-- 仅作为设备注册表，不直接关联会员信息
CREATE TABLE devices (
    device_id TEXT PRIMARY KEY,
    machine_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    first_registered_at TIMESTAMP NOT NULL,
    last_active_at TIMESTAMP NOT NULL,
    UNIQUE(machine_id, platform)
)
```

---

## 🔄 新的初始化流程

### 1. 用户首次打开应用

```
┌──────────────────┐
│  打开应用         │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  检查 user_id    │  ← 从本地存储读取
└────────┬─────────┘
         │
    ┌────┴────┐
    │ 存在？   │
    └────┬────┘
         │
    ┌────┴────────────────┐
    │                     │
   否                    是
    │                     │
    ▼                     ▼
┌──────────────────┐  ┌──────────────────┐
│ 显示用户注册页面  │  │  直接进入主界面   │
└────────┬─────────┘  └──────────────────┘
         │
         ▼
┌──────────────────┐
│ 用户填写信息      │
│ - 昵称           │
│ - 邮箱（可选）    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 生成 user_id     │  ← UUID v4
│ 保存到本地        │  ← localStorage/file
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 后端创建用户      │  ← POST /api/user/register
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 获取 device_id   │  ← 系统函数
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 绑定设备          │  ← user_id + device_id
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 授权免费会员      │  ← memberships(user_id, 'free')
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 进入主界面        │
└──────────────────┘
```

### 2. 后端初始化逻辑（新）

```python
# 新的初始化API
@app.post("/api/user/register")
async def register_user(request: UserRegisterRequest):
    """用户注册并自动开通免费会员
    
    流程：
    1. 创建用户（users表）
    2. 注册设备（devices表）
    3. 绑定设备（user_devices表）
    4. 授权会员（memberships表，user_id为主键）
    """
    # 1. 创建用户
    user_id = user_storage.create_user(
        nickname=request.nickname,
        email=request.email
    )
    
    # 2. 注册设备
    device_id = request.device_id
    membership_service.register_device(
        device_id=device_id,
        machine_id=request.machine_id,
        platform=request.platform
    )
    
    # 3. 绑定设备
    user_storage.bind_device(
        user_id=user_id,
        device_id=device_id,
        device_name=request.device_name
    )
    
    # 4. 授权免费会员（✅ 关键变化：绑定到 user_id）
    membership_service.create_membership(
        user_id=user_id,  # ← 不是 device_id！
        tier='free'
    )
    
    return {
        'success': True,
        'user_id': user_id,
        'device_id': device_id,
        'membership': {
            'tier': 'free',
            'status': 'active'
        }
    }
```

---

## 🔧 代码修改清单

### 1. 数据库表结构（src/providers/storage/sqlite.py）

- [ ] 修改 `memberships` 表：user_id 替代 device_id
- [ ] 修改 `monthly_consumption` 表：添加 user_id，联合主键
- [ ] 修改 `consumption_records` 表：添加 user_id
- [ ] 更新索引

### 2. 会员服务（src/services/membership_service.py）

- [ ] 修改 `register_device()` - 不再自动创建会员
- [ ] 新增 `create_membership(user_id, tier)` - 为用户创建会员
- [ ] 修改 `get_membership(device_id)` → `get_membership_by_user(user_id)`
- [ ] 修改 `check_quota(device_id)` → `check_quota(user_id)`
- [ ] 修改 `upgrade_membership()` - 使用 user_id

### 3. 消费服务（src/services/consumption_service.py）

- [ ] 修改 `record_consumption()` - 同时记录 user_id 和 device_id
- [ ] 修改 `get_monthly_consumption()` - 按 user_id 聚合
- [ ] 新增 `get_device_consumption()` - 按设备查询

### 4. 用户API（src/api/user_api.py）

- [ ] 新增 `/api/user/register` - 完整注册流程
- [ ] 修改 `/api/user/login/{device_id}` - 检查用户是否存在

### 5. 会员API（src/api/membership_api.py）

- [ ] 修改所有接口，从 device_id 改为 user_id
- [ ] `/api/membership/info` - 需要 user_id
- [ ] `/api/membership/quota` - 需要 user_id

### 6. 前端（electron-app）

- [ ] 新增用户注册页面
- [ ] 本地存储 user_id
- [ ] 启动时检查 user_id，不存在则引导注册

---

## 📋 迁移策略

### 对于已有数据

由于当前处于开发阶段，建议：

#### 方案一：清空重建（推荐）
```bash
./scripts/reset_system.sh
```
- 优点：干净、简单
- 缺点：丢失测试数据

#### 方案二：数据迁移（如需保留数据）
```python
# 迁移脚本：从 device_id 迁移到 user_id
def migrate_memberships():
    # 1. 为每个 device_id 创建一个临时 user
    # 2. 将 memberships.device_id 转换为 user_id
    # 3. 更新 consumption_records 和 monthly_consumption
```

---

## 🎯 新的数据关系图

```
┌─────────────┐
│   users     │  ← 用户信息（主体）
│  user_id PK │
└──────┬──────┘
       │
       │ 1:1
       ▼
┌─────────────┐
│ memberships │  ← 会员等级（属于用户）
│  user_id PK │
└─────────────┘
       │
       │ 1:N
       ▼
┌─────────────────┐
│  user_devices   │  ← 设备绑定（一个用户多个设备）
│  user_id FK     │
│  device_id FK   │
└────────┬────────┘
         │
         │ N:1
         ▼
┌─────────────┐
│   devices   │  ← 设备信息（独立）
│ device_id PK│
└──────┬──────┘
       │
       │ 1:N
       ▼
┌───────────────────────┐
│ consumption_records   │  ← 消费记录（按设备记录，按用户统计）
│  user_id FK           │
│  device_id FK         │
└───────────────────────┘
```

---

## ✅ 验证要点

### 功能验证

1. **首次安装**
   - [ ] 强制用户注册
   - [ ] 自动绑定设备
   - [ ] 自动授权免费会员

2. **多设备场景**
   - [ ] 同一用户在新设备登录
   - [ ] 会员等级在所有设备生效
   - [ ] 消费额度在所有设备共享

3. **会员升级**
   - [ ] 升级后所有设备生效
   - [ ] 额度按用户统计，不是设备

4. **消费记录**
   - [ ] 能区分哪个设备消耗
   - [ ] 能统计用户总消耗

---

## 📝 总结

### 核心变化

| 项目 | 旧设计 | 新设计 |
|-----|-------|-------|
| 会员主体 | device_id | user_id ✅ |
| 初始化流程 | 注册设备 → 授权会员 | 注册用户 → 绑定设备 → 授权会员 ✅ |
| 多设备 | 每个设备独立会员 ❌ | 所有设备共享会员 ✅ |
| 消费统计 | 按设备 | 按用户（但保留设备明细）✅ |

### 优势

1. ✅ **逻辑清晰**：会员属于用户，而不是设备
2. ✅ **多设备支持**：一个账号，多设备同步
3. ✅ **灵活扩展**：未来支持云端同步
4. ✅ **商业合理**：会员权益绑定到人，而不是机器

---

© 2026 MindVoice 深圳王哥 & AI

