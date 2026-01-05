# MindVoice 系统全面检查报告

## 执行时间
2026-01-06

## 检查范围
由于系统经历了数据库重构（以 user_id 为主，device_id 为消费产生地），需要全面检查相关部分。

---

## 1. 数据库表结构检查 ✅

### 1.1 records 表（历史记录）
```sql
CREATE TABLE records (
    id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    metadata TEXT,
    app_type TEXT NOT NULL DEFAULT 'voice-note',
    user_id TEXT,                    -- ⚠️ 可选字段
    device_id TEXT,                  -- ⚠️ 可选字段
    is_deleted INTEGER DEFAULT 0,
    deleted_at TIMESTAMP,
    is_starred INTEGER DEFAULT 0,
    is_archived INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP
);
```

**索引**：
- `idx_records_user_id` ON `records(user_id)`
- `idx_records_device_id` ON `records(device_id)`
- `idx_records_user_created` ON `records(user_id, created_at DESC)`
- `idx_records_app_type` ON `records(app_type, user_id, created_at DESC)`

**问题**：
- ❌ `user_id` 和 `device_id` 是可选字段，可能导致部分记录没有关联到用户
- ❌ 查询历史记录时可能无法正确按 user_id 筛选

### 1.2 consumption_records 表（消费记录明细）
```sql
CREATE TABLE consumption_records (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,           -- ✅ 必需字段
    device_id TEXT NOT NULL,         -- ✅ 必需字段
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    type TEXT NOT NULL,              -- 'asr' | 'llm'
    amount REAL NOT NULL,
    unit TEXT NOT NULL,              -- 'ms' | 'tokens'
    model_source TEXT DEFAULT 'vendor',
    details TEXT,
    session_id TEXT,
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (device_id) REFERENCES devices(device_id)
);
```

**索引**：
- `idx_consumption_user_time` ON `consumption_records(user_id, year, month, timestamp DESC)`
- `idx_consumption_device_time` ON `consumption_records(device_id, year, month, timestamp DESC)`
- `idx_consumption_type` ON `consumption_records(user_id, type)`

**状态**：✅ 结构正确

### 1.3 monthly_consumption 表（月度消费汇总）
```sql
CREATE TABLE monthly_consumption (
    user_id TEXT NOT NULL,           -- ✅ 聚合主键
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    asr_duration_ms INTEGER NOT NULL DEFAULT 0,
    llm_prompt_tokens INTEGER NOT NULL DEFAULT 0,
    llm_completion_tokens INTEGER NOT NULL DEFAULT 0,
    llm_total_tokens INTEGER NOT NULL DEFAULT 0,
    record_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    PRIMARY KEY (user_id, year, month),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
```

**状态**：✅ 结构正确（仅按 user_id 聚合，device_id 不在主键中）

### 1.4 其他相关表
- **devices 表**：存储设备信息
- **users 表**：存储用户信息
- **user_devices 表**：绑定用户和设备
- **memberships 表**：会员信息（以 user_id 为主键）

**状态**：✅ 结构正确

---

## 2. 设备注册流程检查 ❌

### 2.1 前端设备注册
**位置**：`electron-app/electron/main.ts`

```typescript
// 问题：端点路径错误
const response = await fetch(`${API_URL}/api/device/register`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    device_id: deviceInfo.deviceId,
    machine_id: deviceInfo.machineId,
    platform: deviceInfo.platform,
  }),
});
```

**实际端点**：`POST /api/user/register`（在 `user_api.py` 中）

**问题**：
- ❌ 端点路径错误，导致 404
- ❌ 设备注册失败，全局 `device_id` 未设置
- ❌ `device_id` 未传递到 `voice_service`

### 2.2 设备 ID 设置
```typescript
// 在设备注册成功后
const setDeviceIdResponse = await fetch(`${API_URL}/api/voice/set-device-id`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ device_id: deviceInfo.deviceId }),
});
```

**状态**：✅ 端点正确，但因为设备注册失败而未执行

---

## 3. 历史记录保存逻辑检查 ❌

### 3.1 保存 API
**端点**：`POST /api/text/save`

```python
record_id = voice_service.storage_provider.save_record(request.text, metadata)
```

**问题**：
- ❌ 未传递 `user_id` 参数
- ❌ 未传递 `device_id` 参数
- ❌ 保存的记录没有关联到用户和设备

**期望行为**：
```python
# 应该从 request 或全局变量获取 user_id 和 device_id
user_id = get_user_id_from_device(device_id)
record_id = voice_service.storage_provider.save_record(
    request.text, 
    metadata,
    user_id=user_id,
    device_id=device_id
)
```

### 3.2 更新 API
**端点**：`POST /api/text/update`

```python
success = voice_service.storage_provider.update_record(
    request.record_id, 
    request.text, 
    metadata
)
```

**问题**：
- ❌ 未传递 `user_id` 参数
- ❌ 未传递 `device_id` 参数

### 3.3 查询 API
**端点**：`GET /api/records`

```python
@app.get("/api/records")
async def list_records(limit: int = 50, offset: int = 0, app_type: str = None):
    records = voice_service.storage_provider.list_records(
        limit=limit,
        offset=offset,
        app_type=app_type
    )
```

**问题**：
- ❌ 未按 `user_id` 筛选
- ❌ 可能返回其他用户的记录

**期望行为**：
```python
# 应该从 device_id 获取 user_id，然后筛选
user_id = get_user_id_from_device(device_id)
records = voice_service.storage_provider.list_records(
    limit=limit,
    offset=offset,
    app_type=app_type,
    user_id=user_id  # 按用户筛选
)
```

---

## 4. 消费记录保存逻辑检查 ❌

### 4.1 ASR 消费记录
**位置**：`src/services/voice_service.py::_record_asr_consumption()`

```python
def _record_asr_consumption(self):
    if not MEMBERSHIP_AVAILABLE or not self.consumption_service or not self._device_id:
        return
    
    # 获取 user_id
    user_id = None
    if self.user_storage and self._device_id:
        user_info = self.user_storage.get_user_by_device(self._device_id)
        if user_info:
            user_id = user_info['user_id']
    
    if not user_id:
        logger.warning(f"[语音服务] 无法获取user_id，跳过ASR消费记录")
        return
    
    self.consumption_service.record_asr_consumption(
        user_id=user_id,
        device_id=self._device_id,
        ...
    )
```

**问题**：
- ⚠️ `_device_id` 未设置（因为设备注册失败）
- ⚠️ `_asr_session_start_time` 可能未记录

### 4.2 LLM 消费记录
**位置**：`src/api/server.py::smart_chat()`

```python
if request.device_id and consumption_service and llm_service:
    user_id = get_user_id_by_device(request.device_id)
    if not user_id:
        logger.warning(f"[SmartChat] 无法获取user_id，跳过LLM消费记录")
    else:
        consumption_service.record_llm_consumption(
            user_id=user_id,
            device_id=request.device_id,
            ...
        )
```

**问题**：
- ❌ `request.device_id` 为 `None`（前端获取失败）
- ❌ LLM 消费未记录

**根本原因**：
前端调用 `GET /api/device_id` 返回 404，因为全局 `device_id` 未设置。

---

## 5. API 端点检查 ❌

### 5.1 端点路径错误
| 前端调用 | 实际端点 | 状态 |
|---------|---------|------|
| `POST /api/device/register` | `POST /api/user/register` | ❌ 404 |
| `POST /api/voice/set-device-id` | 正确 | ✅ |
| `GET /api/device_id` | 正确 | ✅（但返回 404 因为未设置） |

### 5.2 缺失的参数
| API 端点 | 缺失参数 | 影响 |
|---------|---------|------|
| `POST /api/text/save` | `user_id`, `device_id` | 记录未关联用户 |
| `POST /api/text/update` | `user_id`, `device_id` | 更新未关联用户 |
| `GET /api/records` | `user_id` 筛选 | 可能返回其他用户记录 |

---

## 6. 问题总结

### 6.1 关键问题
1. **设备注册失败**：前端调用错误的端点路径
2. **device_id 未设置**：全局变量和 voice_service 的 `_device_id` 都未设置
3. **历史记录未关联用户**：保存/更新记录时未传递 `user_id` 和 `device_id`
4. **消费记录未写入**：因为 `device_id` 为 `None` 而被跳过
5. **查询未按用户筛选**：可能返回其他用户的数据

### 6.2 影响范围
- ❌ 设备注册流程
- ❌ 历史记录保存和查询
- ❌ ASR 消费记录
- ❌ LLM 消费记录
- ❌ 会员额度检查

---

## 7. 修复方案

### 7.1 修复设备注册端点
**文件**：`electron-app/electron/main.ts`

```typescript
// 修改前
const response = await fetch(`${API_URL}/api/device/register`, {

// 修改后
const response = await fetch(`${API_URL}/api/user/register`, {
```

### 7.2 修复历史记录保存
**文件**：`src/api/server.py`

#### 方案 A：从前端传递 device_id
```typescript
// 前端修改：SaveTextRequest 增加 device_id 字段
interface SaveTextRequest {
  text: string;
  app_type: string;
  metadata: any;
  device_id: string;  // 新增
}
```

```python
# 后端修改
@app.post("/api/text/save")
async def save_text_directly(request: SaveTextRequest):
    # 获取 user_id
    user_id = None
    if hasattr(request, 'device_id') and request.device_id:
        user_id = get_user_id_by_device(request.device_id)
    
    record_id = voice_service.storage_provider.save_record(
        request.text, 
        metadata,
        user_id=user_id,
        device_id=getattr(request, 'device_id', None)
    )
```

#### 方案 B：使用全局 device_id
```python
# 后端修改
@app.post("/api/text/save")
async def save_text_directly(request: SaveTextRequest):
    global device_id
    
    # 获取 user_id
    user_id = None
    if device_id:
        user_id = get_user_id_by_device(device_id)
    
    record_id = voice_service.storage_provider.save_record(
        request.text, 
        metadata,
        user_id=user_id,
        device_id=device_id
    )
```

**建议**：使用方案 A，明确传递，更清晰

### 7.3 修复历史记录查询
```python
@app.get("/api/records")
async def list_records(
    limit: int = 50, 
    offset: int = 0, 
    app_type: str = None,
    device_id: str = None  # 新增参数
):
    # 获取 user_id
    user_id = None
    if device_id:
        user_id = get_user_id_by_device(device_id)
    
    records = voice_service.storage_provider.list_records(
        limit=limit,
        offset=offset,
        app_type=app_type,
        user_id=user_id  # 按用户筛选
    )
```

### 7.4 确保 ASR 会话时间记录
**文件**：`src/services/voice_service.py`

```python
def _on_speech_start(self):
    """语音开始回调"""
    # 确保记录会话开始时间
    if not self._asr_session_start_time:
        self._asr_session_start_time = int(time.time() * 1000)
        logger.info(f"[语音服务] 记录ASR会话开始时间: {self._asr_session_start_time}")
```

---

## 8. 修复优先级

### P0 - 阻塞问题（必须立即修复）
1. ✅ 修复设备注册端点路径
2. ✅ 修复历史记录保存（传递 user_id 和 device_id）
3. ✅ 修复历史记录查询（按 user_id 筛选）

### P1 - 重要问题（尽快修复）
4. ✅ 确保 ASR 会话时间记录
5. ✅ 确保 device_id 正确传递到所有需要的地方

### P2 - 优化问题（后续改进）
6. ⏳ 添加更详细的日志
7. ⏳ 添加数据完整性检查
8. ⏳ 优化错误处理

---

## 9. 测试清单

### 9.1 设备注册测试
- [ ] 首次启动应用，设备成功注册
- [ ] `devices` 表有记录
- [ ] `user_devices` 表有绑定记录
- [ ] 全局 `device_id` 已设置
- [ ] `voice_service._device_id` 已设置

### 9.2 历史记录测试
- [ ] 保存历史记录，`user_id` 正确
- [ ] 保存历史记录，`device_id` 正确
- [ ] 查询历史记录，只返回当前用户的记录
- [ ] 更新历史记录，`user_id` 和 `device_id` 不变

### 9.3 消费记录测试
- [ ] ASR 使用后，`consumption_records` 有记录
- [ ] LLM 使用后，`consumption_records` 有记录
- [ ] `monthly_consumption` 正确聚合（按 user_id）
- [ ] 可以按 device_id 查询明细

---

## 10. 下一步行动

1. 修复前端设备注册端点
2. 修复历史记录保存 API
3. 修复历史记录查询 API
4. 测试完整流程
5. 确认消费记录正常写入

