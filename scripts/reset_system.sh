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
echo "3. 系统会自动创建全新的数据目录和数据库结构"
echo ""
echo "数据目录将在首次启动时创建："
if [ -n "$DATA_DIR" ]; then
    echo "  $DATA_DIR"
    echo "    ├── database/          # SQLite 数据库"
    echo "    │   └── history.db    # 包含 users、user_devices、records 表"
    echo "    ├── images/            # 用户上传的图片（头像等）"
    echo "    ├── knowledge/         # 知识库文件和向量数据"
    echo "    └── backups/           # 自动备份文件"
fi
echo ""
echo "📊 数据库表结构（v1.2.0 基准版本）："
echo ""
echo "  【用户系统】"
echo "  • users            - 用户信息（昵称、邮箱、头像、登录统计、软删除）"
echo "  • user_devices     - 设备绑定（多设备支持）"
echo ""
echo "  【数据管理】"
echo "  • records          - 历史记录（用户绑定、软删除、收藏、归档）"
echo "  • records_fts      - 全文搜索（FTS5，10-100倍性能提升）"
echo "  • tags             - 标签管理（自定义标签、颜色、图标）"
echo "  • record_tags      - 标签关联（记录与标签多对多）"
echo ""
echo "  【统计监控】"
echo "  • daily_stats      - 使用统计（每日统计，按应用类型）"
echo "  • backup_logs      - 备份记录（追踪备份操作）"
echo ""
echo "  【会员系统】"
echo "  • devices          - 设备信息（设备注册、活跃时间）"
echo "  • memberships      - 会员信息（等级、订阅、过期时间）"
echo "  • consumption_records    - 消费记录（ASR/LLM消耗详情）"
echo "  • monthly_consumption    - 月度汇总（按月统计消耗）"
echo "  • activation_codes       - 激活码（会员激活）"
echo ""
echo "  【系统管理】"
echo "  • schema_versions  - 数据库版本管理"
echo ""


