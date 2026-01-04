#!/bin/bash

# MindVoice 系统复位脚本
# 用途：全新初始化系统，清理所有数据和缓存
# ⚠️  警告：此操作不可逆，会删除所有数据！

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_FILE="$PROJECT_ROOT/config.yml"

echo "========================================="
echo "⚠️  MindVoice 系统复位工具"
echo "========================================="
echo ""
echo "此操作将："
echo "1. 删除所有历史记录（数据库）"
echo "2. 删除所有图片文件"
echo "3. 删除所有知识库数据"
echo "4. 删除 Electron 缓存数据"
echo "5. 清理所有编译缓存"
echo "6. 清理所有日志文件"
echo ""
echo "⚠️  警告：此操作不可逆！"
echo ""

# 读取配置（去除注释和前后空格）
if [ -f "$CONFIG_FILE" ]; then
    DATA_DIR_RAW=$(grep '^\s*data_dir:' "$CONFIG_FILE" | head -1 | sed 's/.*data_dir:\s*//; s/#.*//; s/^[[:space:]]*//; s/[[:space:]]*$//')
    DATA_DIR="${DATA_DIR_RAW/#\~/$HOME}"
    
    if [ -n "$DATA_DIR" ]; then
        echo "📂 检测到数据目录: $DATA_DIR"
        if [ -d "$DATA_DIR" ]; then
            du -sh "$DATA_DIR" 2>/dev/null || echo "  (无法统计大小)"
        else
            echo "  (目录不存在)"
        fi
    fi
else
    echo "⚠️  未找到配置文件，将只清理项目内的数据"
fi

echo ""
read -p "确认要继续吗？(yes/NO): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ 已取消"
    exit 0
fi

echo ""
echo "========================================="
echo "开始复位系统..."
echo "========================================="
echo ""

# 1. 删除数据目录
if [ -n "$DATA_DIR" ] && [ -d "$DATA_DIR" ]; then
    echo "🗑️  删除数据目录: $DATA_DIR"
    rm -rf "$DATA_DIR"
    echo "✅ 数据目录已删除"
else
    echo "ℹ️  数据目录不存在，跳过"
fi

# 2. 删除 Electron 用户数据目录（浏览器缓存等）
if [ "$(uname)" = "Darwin" ]; then
    # macOS
    ELECTRON_DATA_DIR="$HOME/Library/Application Support/MindVoice-App"
elif [ "$(uname)" = "Linux" ]; then
    # Linux
    ELECTRON_DATA_DIR="$HOME/.config/MindVoice-App"
else
    # Windows (Git Bash)
    ELECTRON_DATA_DIR="$APPDATA/MindVoice-App"
fi

if [ -n "$ELECTRON_DATA_DIR" ] && [ -d "$ELECTRON_DATA_DIR" ]; then
    echo "🗑️  删除 Electron 缓存目录: $ELECTRON_DATA_DIR"
    rm -rf "$ELECTRON_DATA_DIR"
    echo "✅ Electron 缓存已删除"
else
    echo "ℹ️  Electron 缓存目录不存在，跳过"
fi

# 3. 清理项目内的 data 目录（降级数据）
if [ -d "$PROJECT_ROOT/data" ]; then
    echo "🗑️  删除项目内的 data 目录"
    rm -rf "$PROJECT_ROOT/data"
    echo "✅ 项目 data 目录已删除"
fi

# 4. 清理日志文件
if [ -d "$PROJECT_ROOT/logs" ]; then
    echo "🗑️  清理日志文件"
    rm -rf "$PROJECT_ROOT/logs"
    mkdir -p "$PROJECT_ROOT/logs"
    echo "✅ 日志文件已清理"
fi

# 5. 清理前端编译缓存
echo "🗑️  清理前端编译缓存"
cd "$PROJECT_ROOT/electron-app"

if [ -d "dist" ]; then
    rm -rf dist
    echo "  ✓ 已删除 dist/"
fi

if [ -d "dist-electron" ]; then
    rm -rf dist-electron
    echo "  ✓ 已删除 dist-electron/"
fi

if [ -d "node_modules/.vite" ]; then
    rm -rf node_modules/.vite
    echo "  ✓ 已删除 node_modules/.vite/"
fi

echo "✅ 前端缓存已清理"

# 6. 清理 Python 缓存
echo "🗑️  清理 Python 缓存"
cd "$PROJECT_ROOT"
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
echo "✅ Python 缓存已清理"

# 6. 清理旧的构建产物
if [ -d "$PROJECT_ROOT/python-backend/build" ]; then
    rm -rf "$PROJECT_ROOT/python-backend/build"
    echo "✅ Python 构建产物已清理"
fi

if [ -d "$PROJECT_ROOT/python-backend/dist" ]; then
    rm -rf "$PROJECT_ROOT/python-backend/dist"
    echo "✅ Python 分发包已清理"
fi

# 7. 清理发布归档
if [ -d "$PROJECT_ROOT/release/archives" ]; then
    echo "🗑️  清理发布归档"
    rm -rf "$PROJECT_ROOT/release/archives"/*
    echo "✅ 发布归档已清理"
fi

echo ""
echo "========================================="
echo "✅ 系统复位完成"
echo "========================================="
echo ""
echo "下一步操作："
echo "1. 检查配置文件: config.yml"
echo "2. 启动系统: ./quick_start.sh"
echo "3. 系统会自动创建全新的数据目录结构"
echo ""
echo "数据目录将在首次启动时创建："
if [ -n "$DATA_DIR" ]; then
    echo "  $DATA_DIR"
    echo "    ├── database/"
    echo "    ├── images/"
    echo "    ├── knowledge/"
    echo "    └── backups/"
fi
echo ""


