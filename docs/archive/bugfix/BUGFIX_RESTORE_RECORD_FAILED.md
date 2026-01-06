# Bug修复：恢复任务失败

**问题发现**: 2026-01-06 09:55  
**修复时间**: 2026-01-06 10:00  

---

## 🐛 问题描述

**症状**:
- 用户在历史记录列表中看到记录
- 点击"📝 恢复任务"按钮
- 前端报错："记录不存在"

**错误日志**:
```javascript
App.tsx:1183 [历史记录] 恢复记录: 05c002a0-3259-480b-be5f-ec487531a29b
App.tsx:1197 [历史记录] 记录不存在
```

---

## 🔍 问题诊断

### 1. 检查数据库
```sql
SELECT id, app_type, created_at
FROM records 
WHERE id = '05c002a0-3259-480b-be5f-ec487531a29b';
```

**结果**: ✅ 记录存在
```
05c002a0-3259-480b-be5f-ec487531a29b|smart-chat|2026-01-06 09:55:33
```

### 2. 检查后端API响应
```bash
curl "http://127.0.0.1:8765/api/records/05c002a0-3259-480b-be5f-ec487531a29b"
```

**实际返回**:
```json
{
  "id": "05c002a0-3259-480b-be5f-ec487531a29b",
  "text": "...",
  "metadata": {...},
  "app_type": "smart-chat",
  "created_at": "2026-01-06 09:55:33"
}
```

### 3. 检查前端期望
```typescript
// App.tsx:1196
if (!data.success || !data.record) {
  console.warn('[历史记录] 记录不存在');
  setToast({ message: '记录不存在', type: 'error' });
  return;
}

const record = data.record;
```

**前端期望格式**:
```json
{
  "success": true,
  "record": {
    "id": "...",
    "text": "...",
    ...
  }
}
```

### 诊断结论
❌ **API 响应格式不匹配**

---

## 🔧 问题根因

### FastAPI response_model 的行为

**修改前的代码**:
```python
@app.get("/api/records/{record_id}", response_model=RecordItem)
async def get_record(record_id: str):
    ...
    return RecordItem(
        id=record['id'],
        text=record['text'],
        ...
    )
```

**FastAPI 行为**:
- `response_model=RecordItem` 会让 FastAPI **直接序列化** `RecordItem` 的字段
- 返回格式: `{ id: "...", text: "...", ... }`
- **不会**包装在额外的对象中

**问题**:
- 前端期望包装格式: `{ success: true, record: {...} }`
- 后端直接返回字段: `{ id: "...", text: "...", ... }`
- 前端检查 `data.success` 为 `undefined`，判断为失败

---

## ✅ 修复方案

### 1. 创建包装响应模型

```python
class GetRecordResponse(BaseModel):
    """获取单条记录响应"""
    success: bool
    record: Optional[RecordItem] = None
    message: Optional[str] = None
```

### 2. 修改 API 端点

**修改前**:
```python
@app.get("/api/records/{record_id}", response_model=RecordItem)
async def get_record(record_id: str):
    if not voice_service or not voice_service.storage_provider:
        raise HTTPException(status_code=503, detail="存储服务未初始化")
    
    try:
        record = voice_service.storage_provider.get_record(record_id)
        if not record:
            raise HTTPException(status_code=404, detail="记录不存在")
        
        return RecordItem(
            id=record['id'],
            text=record['text'],
            metadata=record['metadata'],
            app_type=record['app_type'],
            created_at=record['created_at']
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

**修改后**:
```python
@app.get("/api/records/{record_id}", response_model=GetRecordResponse)
async def get_record(record_id: str):
    if not voice_service or not voice_service.storage_provider:
        return GetRecordResponse(
            success=False,
            message="存储服务未初始化"
        )
    
    try:
        record = voice_service.storage_provider.get_record(record_id)
        if not record:
            return GetRecordResponse(
                success=False,
                message="记录不存在"
            )
        
        logger.info(f"[get_record] 返回记录: id={record['id']}, app_type={record['app_type']}")
        
        return GetRecordResponse(
            success=True,
            record=RecordItem(
                id=record['id'],
                text=record['text'],
                metadata=record['metadata'],
                app_type=record['app_type'],
                created_at=record['created_at']
            )
        )
    except Exception as e:
        logger.error(f"获取记录失败: {e}", exc_info=True)
        return GetRecordResponse(
            success=False,
            message=f"获取记录失败: {str(e)}"
        )
```

### 改进点

1. **统一响应格式**: 包装为 `{ success, record, message }`
2. **不再抛出异常**: 用 `success: false` 代替 `HTTPException`
3. **更友好的错误信息**: 前端可以显示具体的 `message`

---

## 🧪 验证测试

### 1. 重启后端
```bash
cd /Users/wangjunhui/playcode/语音桌面助手
source venv/bin/activate
python src/api/server.py
```

### 2. 测试 API 响应格式
```bash
curl -s "http://127.0.0.1:8765/api/records/05c002a0-3259-480b-be5f-ec487531a29b"
```

**预期返回**:
```json
{
  "success": true,
  "record": {
    "id": "05c002a0-3259-480b-be5f-ec487531a29b",
    "text": "[用户] 09:55...",
    "metadata": {...},
    "app_type": "smart-chat",
    "created_at": "2026-01-06 09:55:33"
  },
  "message": null
}
```

### 3. 测试前端恢复功能
- 刷新前端（Cmd+Shift+R）
- 进入"历史记录"
- 找到记录 `05c002a0-3259-480b-be5f-ec487531a29b`
- 点击"📝 恢复任务"
- **预期**: 成功跳转到 SmartChat，显示对话内容

---

## 📊 影响范围

### 修改的文件
- `src/api/server.py`
  - 新增 `GetRecordResponse` 模型
  - 修改 `/api/records/{record_id}` 端点

### 兼容性
- ✅ **前端**: 完全兼容（前端一直期望这种格式）
- ✅ **后端**: 新格式，重启后生效
- ✅ **数据库**: 无影响

### 其他类似问题
检查了其他端点，发现类似的响应格式都正确：
- ✅ `/api/records` (列表): 已包装为 `ListRecordsResponse`
- ✅ `/api/text/save`: 已包装为 `SaveTextResponse`
- ✅ `/api/smartchat/chat`: 已包装为 `ChatResponse`

**仅此一个端点**有问题。

---

## 💡 经验教训

### 1. FastAPI response_model 的行为
- `response_model=ItemModel` → 直接返回 Item 字段
- `response_model=WrapperModel` → 返回 Wrapper 结构

### 2. 前后端 API 契约
- 前后端必须约定统一的响应格式
- 最好在 API 文档中明确说明
- 使用 TypeScript 类型和 Pydantic 模型保持一致

### 3. 错误处理的演进
**旧方式 (HTTPException)**:
```python
raise HTTPException(status_code=404, detail="记录不存在")
```
- 前端需要解析 HTTP 状态码
- 错误信息在 `detail` 字段

**新方式 (统一响应)**:
```python
return GetRecordResponse(success=False, message="记录不存在")
```
- 总是返回 200 HTTP 状态码
- 通过 `success` 字段判断成功/失败
- 错误信息在 `message` 字段

### 4. 为什么统一响应更好？
- ✅ 前端处理逻辑更简单（不需要 try-catch HTTP 错误）
- ✅ 错误信息更灵活（可以包含更多字段）
- ✅ 类型安全（TypeScript 可以推断完整类型）
- ✅ API 文档更清晰（总是返回相同结构）

---

## 🔄 后续改进建议

### 1. 统一所有 API 响应格式
确保所有端点都使用包装响应：
```python
class BaseResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    error: Optional[Dict[str, Any]] = None
```

### 2. 前端类型定义
```typescript
interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  error?: any;
}
```

### 3. API 测试覆盖
为每个端点添加集成测试，验证响应格式：
```python
def test_get_record_response_format():
    response = client.get("/api/records/test-id")
    assert "success" in response.json()
    assert "record" in response.json() or "message" in response.json()
```

---

**状态**: ✅ 修复完成，待重启验证

