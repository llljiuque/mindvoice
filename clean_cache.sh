#!/bin/bash
# 清理编译缓存脚本

echo "🧹 开始清理编译缓存..."

# 进入electron-app目录
cd "$(dirname "$0")/electron-app" || exit

# 清理dist目录
if [ -d "dist" ]; then
    echo "清理 dist/ ..."
    rm -rf dist
fi

# 清理dist-electron目录
if [ -d "dist-electron" ]; then
    echo "清理 dist-electron/ ..."
    rm -rf dist-electron
fi

# 清理Vite缓存
if [ -d "node_modules/.vite" ]; then
    echo "清理 node_modules/.vite/ ..."
    rm -rf node_modules/.vite
fi

echo "✅ 清理完成！"
echo ""
echo "现在可以重新启动开发服务器："
echo "  cd electron-app && npm run dev"

