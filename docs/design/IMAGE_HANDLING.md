# 图片处理技术文档

## 图片存储架构

### 存储位置
- **图片文件**: `data/images/{timestamp}-{hash}.{ext}`
- **数据库**: metadata.blocks 中的 imageUrl 字段
- **格式**: 相对路径，如 `images/261619072-6ddaa776.png`

### 图片块结构

```typescript
{
  id: "block-xxx",
  type: "image",
  content: "",  // 图片块的 content 为空字符串
  imageUrl: "images/261619072-6ddaa776.png",  // 相对路径
  imageCaption?: "图片说明"  // 可选的说明文字
}
```

## 图片上传流程

### 前端上传

```typescript
// BlockEditor.tsx - 粘贴图片处理
const reader = new FileReader();
reader.onload = async (event) => {
  const base64Data = event.target?.result as string;
  
  // 调用API上传
  const response = await fetch(`${API_BASE_URL}/api/images/save`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_data: base64Data })
  });
  
  const result = await response.json();
  // result.image_url = "images/261619072-6ddaa776.png"
};
```

### 后端保存

```python
# server.py - 图片保存API
@app.post("/api/images/save")
async def save_image(request: SaveImageRequest):
    # 1. 解码 Base64
    image_bytes = base64.b64decode(image_data)
    
    # 2. 生成唯一文件名
    timestamp = int(time.time() * 1000)
    hash_str = hashlib.md5(image_bytes[:1024]).hexdigest()[:8]
    filename = f"{timestamp}-{hash_str}.{ext}"
    
    # 3. 保存到 data/images/
    image_path = project_root / "data" / "images" / filename
    with open(image_path, 'wb') as f:
        f.write(image_bytes)
    
    # 4. 返回相对路径
    return {"success": True, "image_url": f"images/{filename}"}
```

## text 字段处理规范 ⚠️ 重要

**规则**: text 字段必须包含图片占位符，确保从纯文本恢复时不丢失图片信息

```typescript
// VoiceNoteAdapter.ts - toSaveData()
const textContent = blocks
  .filter(b => b.type !== 'note-info' && !b.isBufferBlock)
  .map(b => {
    if (b.type === 'image') {
      // ✅ 正确：添加图片占位符
      return `[IMAGE: ${b.imageUrl || ''}]${b.imageCaption ? ' ' + b.imageCaption : ''}`;
    }
    return b.content;
  })
  .filter(text => text.trim())
  .join('\n');
```

## 图片恢复流程

### 从 blocks 恢复（推荐）

```typescript
// App.tsx - loadRecord()
if (data.metadata?.blocks && Array.isArray(data.metadata.blocks) && data.metadata.blocks.length > 0) {
  // 直接使用 blocks，包含完整的图片块信息
  setInitialBlocks(data.metadata.blocks);
}
```

### 从纯文本恢复（降级方案）

```typescript
// App.tsx - loadRecord()
else {
  // 解析 text 字段中的图片占位符
  const textBlocks = data.text.split('\n')
    .filter(line => line.trim())
    .map((line, index) => {
      // 检测图片占位符
      const imageMatch = line.match(/^\[IMAGE: (.*?)\](.*)?$/);
      if (imageMatch) {
        return {
          id: `block-restored-${timestamp}-${index}`,
          type: 'image',
          content: '',
          imageUrl: imageMatch[1],
          imageCaption: imageMatch[2]?.trim() || undefined,
        };
      }
      return {
        id: `block-restored-${timestamp}-${index}`,
        type: 'paragraph',
        content: line,
        isAsrWriting: false,
      };
    });
  
  setInitialBlocks([noteInfoBlock, ...textBlocks]);
}
```

### 图片URL渲染

```typescript
// BlockEditor.tsx - 渲染图片块
if (block.type === 'image') {
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8765';
  const imageUrl = block.imageUrl?.startsWith('http') 
    ? block.imageUrl 
    : `${API_BASE_URL}/api/${block.imageUrl}`;  // 拼接完整URL
  
  return <img src={imageUrl} alt={block.imageCaption || '图片'} />;
}
```

## API 端点

### 上传图片
- **端点**: `POST /api/images/save`
- **请求**: `{ image_data: "data:image/png;base64,..." }`
- **响应**: `{ success: true, image_url: "images/xxx.png" }`

### 获取图片
- **端点**: `GET /api/images/{filename}`
- **响应**: 图片文件（FileResponse）
- **安全**: 防止路径遍历攻击（检查 `..`、`/`、`\`）

## 错误处理

### 前端错误处理

```typescript
// 图片加载失败
<img 
  src={imageUrl}
  onError={(e) => {
    console.error('[BlockEditor] 图片加载失败:', imageUrl);
    e.currentTarget.style.display = 'none';
    // 显示错误提示
  }}
/>
```

### 后端错误处理

```python
# 图片文件不存在
if not image_path.exists():
    raise HTTPException(status_code=404, detail="图片不存在")

# 无效的文件名
if '..' in filename or '/' in filename:
    raise HTTPException(status_code=400, detail="无效的文件名")
```

## 图片文件管理

### 当前限制 ⚠️
1. **孤儿文件**: 删除历史记录时，图片文件不会自动删除
2. **文件累积**: 长期使用会导致 `data/images/` 目录体积增大
3. **备份不完整**: 仅备份数据库不包含图片文件

### 手动清理

```bash
# 查看图片目录大小
du -sh data/images/

# 手动删除旧图片（慎用，可能导致历史记录中的图片失效）
find data/images/ -type f -mtime +90 -delete
```

### 未来改进方向
1. **引用计数**: 在数据库中记录图片被引用次数
2. **垃圾回收**: 定期清理未被引用的图片文件
3. **完整备份**: 备份时同时打包图片文件
4. **导出功能**: 导出为 ZIP（markdown + images）

## 最佳实践

### ✅ 应该做的
1. **保存时**: 在 text 字段添加图片占位符
2. **恢复时**: 优先使用 blocks，降级到解析 text
3. **渲染时**: 添加 onError 处理图片加载失败
4. **删除时**: 考虑图片文件是否需要清理

### ❌ 不应该做的
1. 不要在 text 字段中遗漏图片块
2. 不要在 metadata 中存储 Base64（体积太大）
3. 不要直接删除 `data/images/` 目录
4. 不要在前端硬编码图片绝对路径

