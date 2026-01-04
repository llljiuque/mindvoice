# 清理浏览器缓存和重新编译

看到 `text is not defined` 错误，这是因为浏览器加载了旧的编译代码。

## 解决步骤

### 1. 停止开发服务器
按 `Ctrl+C` 停止当前运行的 Vite 开发服务器

### 2. 清理编译缓存
```bash
cd electron-app
rm -rf dist
rm -rf dist-electron
rm -rf node_modules/.vite
```

### 3. 重新启动开发服务器
```bash
npm run dev
```

### 4. 清理浏览器缓存
在浏览器中：
- 打开开发者工具 (F12)
- 右键点击刷新按钮
- 选择"清空缓存并硬性重新加载"

或者直接：
- 按 `Ctrl+Shift+R` (Windows/Linux)
- 按 `Cmd+Shift+R` (Mac)

## 如果问题仍然存在

检查是否有未保存的文件：
```bash
# 查看git状态
git status

# 查看实际文件内容
cat electron-app/src/App.tsx | grep "text"
```

## 验证

刷新后，应该看到：
- 没有 `text is not defined` 错误
- 应用正常加载
- 语音笔记功能正常工作

