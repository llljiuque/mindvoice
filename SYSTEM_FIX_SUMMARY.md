# MindVoice 系统修复总结

## 修复时间
2026-01-06

## 背景
系统经历了数据库重构（以 user_id 为主，device_id 为消费产生地），需要全面检查和修复相关部分。

---

## 修复内容

### 1. 修复设备注册端点 ✅

**问题**：前端调用错误的端点路径

**文件**：`electron-app/electron/main.ts`

**修改前**：
```typescript
const response = await fetch(`${API_URL}/api/device/register`, {
```

**修改后**：
```typescript
const response = await fetch(`${API_URL}/api/user/register`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    device_id: deviceInfo.deviceId,
    machine_id: deviceInfo.machineId,
    platform: deviceInfo.platform,
    nickname: '新用户',
    device_name: 'MacBook Pro'
  }),
});
```

**影响**：
- ✅ 设备注册成功
- ✅ 全局 `device_id` 正确设置
- ✅ `voice_service._device_id` 正确设置

---

### 2. 修复历史记录保存 API ✅

**问题**：保存记录时未传递 `user_id` 和 `device_id`

**文件**：`src/api/server.py`

#### 2.1 修改请求模型
```python
class SaveTextRequest(BaseModel):
    text: str
    app_type: str = 'voice-note'
    metadata: dict
    device_id: Optional[str] = None  # 新增
```

#### 2.2 修改保存逻辑
```python
@app.post("/api/text/save")
async def save_text_directly(request: SaveTextRequest):
    # 获取 user_id 和 device_id
    user_id = None
    device_id_to_use = request.device_id or device_id
    
    if device_id_to_use:
        user_id = get_user_id_by_device(device_id_to_use)
    
    # 保存记录时传递 user_id 和 device_id
    record_id = voice_service.storage_provider.save_record(
        request.text, 
        metadata,
        user_id=user_id,
        device_id=device_id_to_use
    )
```

**影响**：
- ✅ 历史记录正确关联到用户
- ✅ 历史记录记录了设备信息

---

### 3. 修复历史记录更新 API ✅

**问题**：更新记录时未传递 `user_id` 和 `device_id`

**文件**：`src/api/server.py`

```python
@app.put("/api/records/{record_id}")
async def update_record(record_id: str, request: SaveTextRequest):
    # 获取 user_id 和 device_id
    user_id = None
    device_id_to_use = request.device_id or device_id
    
    if device_id_to_use:
        user_id = get_user_id_by_device(device_id_to_use)
    
    # 更新记录时传递 user_id 和 device_id
    success = voice_service.storage_provider.update_record(
        record_id, 
        request.text, 
        metadata,
        user_id=user_id,
        device_id=device_id_to_use
    )
```

**影响**：
- ✅ 更新记录时保持用户关联
- ✅ 更新记录时保持设备信息

---

### 4. 修复历史记录查询 API ✅

**问题**：查询记录时未按 `user_id` 筛选

**文件**：`src/api/server.py`

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
    device_id_to_use = device_id or globals().get('device_id')
    
    if device_id_to_use:
        user_id = get_user_id_by_device(device_id_to_use)
    
    # 按用户筛选
    records = voice_service.storage_provider.list_records(
        limit=limit,
        offset=offset,
        app_type=app_type,
        user_id=user_id  # 按用户筛选
    )
    
    # 按用户计数
    total = voice_service.storage_provider.count_records(
        app_type=app_type,
        user_id=user_id
    )
```

**影响**：
- ✅ 只返回当前用户的记录
- ✅ 不会返回其他用户的记录
- ✅ 总数统计正确

---

### 5. 确保 ASR 会话时间记录 ✅

**问题**：ASR 会话开始时间可能未记录

**文件**：`src/services/voice_service.py`

**状态**：已确认代码中已有记录逻辑

```python
def _on_speech_start(self):
    # 记录ASR会话开始时间
    self._asr_session_start_time = int(time.time() * 1000)
    logger.info(f"[语音服务] 记录ASR会话开始时间: {self._asr_session_start_time}")
```

**影响**：
- ✅ ASR 消费时长计算正确
- ✅ ASR 消费记录完整

---

## 前端需要修改的地方

### 1. 保存历史记录时传递 device_id

**文件**：`electron-app/src/services/AutoSaveService.ts`

**需要修改**：
```typescript
// 当前代码
const response = await fetch('http://127.0.0.1:8765/api/text/save', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(saveData),
});

// 应该修改为
const deviceIdResponse = await fetch(`${API_BASE_URL}/api/device_id`);
const deviceIdData = await deviceIdResponse.json();

const response = await fetch('http://127.0.0.1:8765/api/text/save', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    ...saveData,
    device_id: deviceIdData.device_id  // 添加 device_id
  }),
});
```

### 2. 查询历史记录时传递 device_id

**文件**：`electron-app/src/components/shared/HistoryView.tsx`（或类似文件）

**需要修改**：
```typescript
// 当前代码
const response = await fetch(`${API_BASE_URL}/api/records?limit=${limit}&offset=${offset}`);

// 应该修改为
const deviceIdResponse = await fetch(`${API_BASE_URL}/api/device_id`);
const deviceIdData = await deviceIdResponse.json();

const response = await fetch(
  `${API_BASE_URL}/api/records?limit=${limit}&offset=${offset}&device_id=${deviceIdData.device_id}`
);
```

---

## 测试清单

### 1. 设备注册测试
- [ ] 首次启动应用，设备成功注册
- [ ] `devices` 表有记录
- [ ] `user_devices` 表有绑定记录
- [ ] 全局 `device_id` 已设置
- [ ] `voice_service._device_id` 已设置

### 2. 历史记录测试
- [ ] 保存历史记录，`user_id` 正确
- [ ] 保存历史记录，`device_id` 正确
- [ ] 查询历史记录，只返回当前用户的记录
- [ ] 更新历史记录，`user_id` 和 `device_id` 不变

### 3. 消费记录测试
- [ ] ASR 使用后，`consumption_records` 有记录
- [ ] LLM 使用后，`consumption_records` 有记录
- [ ] `monthly_consumption` 正确聚合（按 user_id）
- [ ] 可以按 device_id 查询明细

---

## 数据库表结构确认

### records 表
```sql
CREATE TABLE records (
    id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    metadata TEXT,
    app_type TEXT NOT NULL DEFAULT 'voice-note',
    user_id TEXT,          -- 用户ID
    device_id TEXT,        -- 设备ID（记录产生地）
    ...
);
```

**注意**：`user_id` 和 `device_id` 是可选字段，但应该尽量填充。

### consumption_records 表
```sql
CREATE TABLE consumption_records (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,     -- 用户ID（必需）
    device_id TEXT NOT NULL,   -- 设备ID（必需）
    ...
);
```

### monthly_consumption 表
```sql
CREATE TABLE monthly_consumption (
    user_id TEXT NOT NULL,     -- 用户ID（聚合主键）
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    ...
    PRIMARY KEY (user_id, year, month)
);
```

**注意**：`device_id` 不在主键中，仅按 `user_id` 聚合。

---

## 架构说明

### user_id vs device_id

#### user_id（用户ID）
- **用途**：标识用户身份
- **来源**：用户注册时生成
- **关系**：一个用户可以有多个设备
- **聚合**：消费记录按 user_id 聚合

#### device_id（设备ID）
- **用途**：标识设备，记录消费产生地
- **来源**：设备首次启动时生成
- **关系**：一个设备只能绑定一个用户
- **用途**：用于查询明细、审计、多设备管理

### 数据流

1. **设备注册**：
   ```
   device_id → 注册 → 生成 user_id → 绑定 (user_devices)
   ```

2. **历史记录保存**：
   ```
   device_id → 查询 user_id → 保存 (user_id + device_id)
   ```

3. **消费记录**：
   ```
   device_id → 查询 user_id → 记录 (user_id + device_id)
   ```

4. **月度汇总**：
   ```
   consumption_records (user_id) → 聚合 → monthly_consumption (user_id)
   ```

---

## 已知问题

### 1. 前端未传递 device_id
- **状态**：需要修改前端代码
- **影响**：中等
- **优先级**：P1

### 2. 历史记录的 user_id 可能为空
- **状态**：数据库字段是可选的
- **影响**：低（可以后续填充）
- **优先级**：P2

---

## 下一步行动

1. ✅ 修复后端 API（已完成）
2. ⏳ 修复前端代码（待完成）
3. ⏳ 测试完整流程（待完成）
4. ⏳ 确认消费记录正常写入（待完成）

---

## 相关文档

- [系统检查报告](./SYSTEM_CHECK_REPORT.md)
- [数据库架构文档](./docs/DATABASE_SCHEMA.md)
- [会员系统文档](./docs/MEMBERSHIP_REDESIGN.md)

