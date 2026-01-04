#!/bin/bash
#
# 清理构建文件脚本
# 用途：清理所有构建产物和临时文件
# 作者：深圳王哥 & AI
# 日期：2026-01-04
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

echo "🧹 清理构建文件..."

# Python 后端
log_info "清理 Python 后端构建文件..."
rm -rf "$PROJECT_ROOT/python-backend/dist"
rm -rf "$PROJECT_ROOT/python-backend/build"
rm -rf "$PROJECT_ROOT/build.spec"
rm -rf "$PROJECT_ROOT/*.spec"

# Electron 前端
log_info "清理 Electron 前端构建文件..."
rm -rf "$PROJECT_ROOT/electron-app/dist"
rm -rf "$PROJECT_ROOT/electron-app/dist-electron"

# 发布文件
log_info "清理发布文件..."
rm -rf "$PROJECT_ROOT/release/latest"

# Python 缓存
log_info "清理 Python 缓存..."
find "$PROJECT_ROOT" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$PROJECT_ROOT" -type f -name "*.pyc" -delete 2>/dev/null || true
find "$PROJECT_ROOT" -type f -name "*.pyo" -delete 2>/dev/null || true

echo ""
log_success "清理完成！"

