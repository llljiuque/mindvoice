#!/bin/bash

# 数据库重建脚本
# 用途：应用新的数据库结构（里程碑基准）
# 特性：自动从 config.yml 读取数据库路径，支持灵活配置

set -e

# ========== 从 config.yml 读取数据库路径 ==========
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_FILE="$PROJECT_ROOT/config.yml"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ 配置文件不存在: $CONFIG_FILE"
    echo "请先创建 config.yml（参考 config.yml.example）"
    exit 1
fi

# 读取配置：data_dir + database（去除注释和前后空格）
DATA_DIR_RAW=$(grep '^\s*data_dir:' "$CONFIG_FILE" | head -1 | sed 's/.*data_dir:\s*//; s/#.*//; s/^[[:space:]]*//; s/[[:space:]]*$//')
DB_RELATIVE=$(grep '^\s*database:' "$CONFIG_FILE" | head -1 | sed 's/.*database:\s*//; s/#.*//; s/^[[:space:]]*//; s/[[:space:]]*$//')

if [ -z "$DATA_DIR_RAW" ] || [ -z "$DB_RELATIVE" ]; then
    echo "❌ 无法从 config.yml 中读取存储配置"
    echo "请检查 storage.data_dir 和 storage.database 配置"
    exit 1
fi

# 展开 ~ 为用户主目录
DATA_DIR="${DATA_DIR_RAW/#\~/$HOME}"
DB_PATH="$DATA_DIR/$DB_RELATIVE"

# 读取 backups 配置
BACKUP_RELATIVE=$(grep '^\s*backups:' "$CONFIG_FILE" | head -1 | sed 's/.*backups:\s*//; s/#.*//; s/^[[:space:]]*//; s/[[:space:]]*$//')
if [ -n "$BACKUP_RELATIVE" ]; then
    BACKUP_DIR="$DATA_DIR/$BACKUP_RELATIVE"
else
    BACKUP_DIR="$DATA_DIR/backups"
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "========================================="
echo "数据库重建脚本"
echo "========================================="
echo ""
echo "📂 配置文件: $CONFIG_FILE"
echo "📂 数据库路径: $DB_PATH"
echo ""

# 1. 检查数据库是否存在
if [ ! -f "$DB_PATH" ]; then
    echo "❌ 数据库文件不存在: $DB_PATH"
    echo "✅ 将在首次运行时自动创建"
    exit 0
fi

echo "📊 当前数据库信息:"
echo "位置: $DB_PATH"
echo "大小: $(ls -lh "$DB_PATH" | awk '{print $5}')"
echo ""

# 2. 检查记录数
RECORD_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM records;" 2>/dev/null || echo "0")
echo "记录数: $RECORD_COUNT"
echo ""

# 3. 如果有记录，询问是否备份
if [ "$RECORD_COUNT" -gt 0 ]; then
    echo "⚠️  数据库中有 $RECORD_COUNT 条记录"
    echo ""
    echo "选项:"
    echo "1) 备份现有数据库并重建（推荐）"
    echo "2) 直接重建（数据将丢失）"
    echo "3) 取消"
    echo ""
    read -p "请选择 (1/2/3): " choice
    
    case $choice in
        1)
            # 创建备份目录
            mkdir -p "$BACKUP_DIR"
            BACKUP_FILE="$BACKUP_DIR/history.db.$TIMESTAMP"
            
            echo ""
            echo "📦 备份数据库..."
            cp "$DB_PATH" "$BACKUP_FILE"
            echo "✅ 备份完成: $BACKUP_FILE"
            ;;
        2)
            echo ""
            echo "⚠️  跳过备份"
            ;;
        3)
            echo ""
            echo "❌ 取消操作"
            exit 0
            ;;
        *)
            echo ""
            echo "❌ 无效选择"
            exit 1
            ;;
    esac
else
    echo "✅ 数据库为空，无需备份"
fi

echo ""
echo "🔨 重建数据库..."

# 4. 删除旧数据库
rm -f "$DB_PATH"
echo "✅ 已删除旧数据库"

# 5. 确保目录存在
mkdir -p "$(dirname "$DB_PATH")"

# 6. 创建新数据库（使用里程碑基准结构）
sqlite3 "$DB_PATH" <<EOF
CREATE TABLE records (
    id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    metadata TEXT,
    app_type TEXT NOT NULL DEFAULT 'voice-note',
    created_at TIMESTAMP NOT NULL
);
EOF

echo "✅ 已创建新数据库（里程碑基准结构）"

# 7. 验证新结构
echo ""
echo "📋 新数据库结构:"
sqlite3 "$DB_PATH" ".schema records"

echo ""
echo "========================================="
echo "✅ 数据库重建完成"
echo "========================================="
echo ""
echo "说明:"
echo "- 新数据库位置: $DB_PATH"
echo "- 表结构: 里程碑基准（无向后兼容）"
echo "- app_type: NOT NULL（必需字段）"
echo "- created_at: NOT NULL（必需字段）"

if [ "$RECORD_COUNT" -gt 0 ] && [ -n "$BACKUP_FILE" ]; then
    echo ""
    echo "⚠️  旧数据已备份到: $BACKUP_FILE"
    echo "如需恢复，请手动执行:"
    echo "  cp $BACKUP_FILE $DB_PATH"
fi

echo ""

