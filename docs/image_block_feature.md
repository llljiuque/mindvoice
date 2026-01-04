# Block 图片显示功能

## 功能概述

VoiceNote 现在支持在 Block 中显示图片！用户可以通过 Ctrl+V 粘贴剪贴板中的图片。

## 使用方法

### 1. 粘贴图片
- 在任何应用中复制图片（右键复制、截图等）
- 在 VoiceNote 编辑区域按 `Ctrl+V` (Windows/Linux) 或 `Cmd+V` (macOS)
- 图片会自动上传并插入到笔记中

### 2. 图片存储
- **存储位置**: `data/images/` 目录
- **命名格式**: `{timestamp}-{uuid}.png`
- **访问方式**: 通过后端 API `/api/images/{filename}` 访问

### 3. 图片管理
- 图片块可以像普通块一样删除（悬停显示删除按钮）
- 图片块支持拖拽排序（使用左侧的拖拽手柄）
- 图片会自动适应容器宽度，保持原始宽高比

## 技术实现

### Block 接口扩展
```typescript
export interface Block {
  id: string;
  type: BlockType;  // 新增 'image' 类型
  content: string;
  imageUrl?: string;      // 图片 URL（相对路径）
  imageCaption?: string;  // 图片说明（可选）
  // ... 其他字段
}
```

### 后端 API

#### 1. 保存图片
```
POST /api/images/save
Content-Type: application/json

{
  "image_data": "data:image/png;base64,iVBORw0KG...",
  "filename": "optional-filename.png"  // 可选
}

Response:
{
  "success": true,
  "image_url": "images/1704268800000-abc123.png",
  "message": "图片已保存"
}
```

#### 2. 获取图片
```
GET /api/images/{filename}

Response: 图片文件（二进制）
```

### 前端实现

#### 粘贴事件处理
- 监听 `onPaste` 事件
- 检测剪贴板中的图片数据
- 转换为 Base64
- 调用后端 API 保存
- 创建图片 Block

#### 图片渲染
```tsx
if (block.type === 'image') {
  return (
    <div className="block block-image-container">
      <div className="block-handle">🖼️</div>
      <div className="block-image-wrapper">
        <img src={imageUrl} alt={caption} className="block-image" />
        {caption && <div className="block-image-caption">{caption}</div>}
      </div>
      <button className="block-delete-btn">🗑️</button>
    </div>
  );
}
```

## 样式特点

- 图片块使用浅灰色渐变背景
- 悬停时显示轻微阴影效果
- 图片自动适应宽度，响应式设计
- 支持图片说明文字（居中显示）
- 图片加载失败时显示友好错误提示

## 安全考虑

1. **路径遍历防护**: 文件名过滤 `..`, `/`, `\` 字符
2. **Base64 验证**: 解码失败时返回错误
3. **文件大小**: 建议前端限制图片大小（如 5MB）
4. **文件类型**: 支持 PNG, JPG, GIF, WebP

## 版本历史

- **v1.1.0** (2026-01-03): 初次实现图片 Block 功能

## 未来改进

### 可选增强功能
1. **图片编辑**
   - 裁剪
   - 旋转
   - 调整大小

2. **批量上传**
   - 支持一次粘贴多张图片
   - 拖拽上传文件

3. **图片压缩**
   - 自动压缩大图片
   - 保存缩略图

4. **云存储**
   - 支持上传到云服务（OSS, S3 等）
   - 分享图片链接

5. **图片标注**
   - 添加箭头、文字等标注
   - 高亮区域

## 故障排查

### 图片无法显示
1. 检查 `data/images/` 目录是否存在
2. 检查图片文件是否存在
3. 检查后端 API 是否正常运行
4. 查看浏览器控制台错误信息

### 图片上传失败
1. 检查图片格式是否支持
2. 检查图片大小是否过大
3. 检查磁盘空间是否充足
4. 查看后端日志 `logs/api_server_*.log`

### 粘贴不生效
1. 确保剪贴板中有图片数据
2. 确保焦点在编辑区域
3. 检查浏览器是否允许剪贴板访问
4. 尝试刷新页面重新测试

## 开发者注意事项

- 图片 Block 的 `content` 字段为空字符串
- 图片保存时使用相对路径，便于迁移
- API 响应的 `image_url` 格式为 `images/{filename}`
- 前端访问时需要拼接 API 基础 URL
- 删除笔记时，关联的图片文件不会自动删除（需要手动清理）

