#!/bin/bash
#
# 图标准备脚本
# 从源 PNG 生成所有平台需要的图标格式
# 作者：深圳王哥 & AI
# 日期：2026-01-04
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ASSETS_DIR="$PROJECT_ROOT/electron-app/assets"
BUILD_ICONS_DIR="$PROJECT_ROOT/build/resources/icons"
SOURCE_ICON="$ASSETS_DIR/ico.png"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

echo "🎨 准备应用图标..."

# 检查源图标
if [ ! -f "$SOURCE_ICON" ]; then
    echo "❌ 错误：源图标不存在: $SOURCE_ICON"
    exit 1
fi

# 创建输出目录
mkdir -p "$BUILD_ICONS_DIR"

# ============================================================================
# macOS .icns 格式
# ============================================================================

log_info "生成 macOS .icns 图标..."

mkdir -p icon.iconset

# 生成各种尺寸
sips -z 16 16     "$SOURCE_ICON" --out icon.iconset/icon_16x16.png 2>/dev/null
sips -z 32 32     "$SOURCE_ICON" --out icon.iconset/icon_16x16@2x.png 2>/dev/null
sips -z 32 32     "$SOURCE_ICON" --out icon.iconset/icon_32x32.png 2>/dev/null
sips -z 64 64     "$SOURCE_ICON" --out icon.iconset/icon_32x32@2x.png 2>/dev/null
sips -z 128 128   "$SOURCE_ICON" --out icon.iconset/icon_128x128.png 2>/dev/null
sips -z 256 256   "$SOURCE_ICON" --out icon.iconset/icon_128x128@2x.png 2>/dev/null
sips -z 256 256   "$SOURCE_ICON" --out icon.iconset/icon_256x256.png 2>/dev/null
sips -z 512 512   "$SOURCE_ICON" --out icon.iconset/icon_256x256@2x.png 2>/dev/null
sips -z 512 512   "$SOURCE_ICON" --out icon.iconset/icon_512x512.png 2>/dev/null
sips -z 1024 1024 "$SOURCE_ICON" --out icon.iconset/icon_512x512@2x.png 2>/dev/null

# 转换为 .icns
iconutil -c icns icon.iconset -o "$BUILD_ICONS_DIR/icon.icns"
rm -rf icon.iconset

log_success "macOS .icns 图标生成完成"

# ============================================================================
# Windows .ico 格式（需要 ImageMagick）
# ============================================================================

if command -v convert &> /dev/null; then
    log_info "生成 Windows .ico 图标..."
    convert "$SOURCE_ICON" -resize 256x256 "$BUILD_ICONS_DIR/icon.ico" 2>/dev/null
    log_success "Windows .ico 图标生成完成"
else
    log_warning "ImageMagick 未安装，跳过 .ico 生成"
    log_info "安装方法: brew install imagemagick"
fi

# ============================================================================
# Linux PNG 格式
# ============================================================================

log_info "生成 Linux PNG 图标..."
cp "$SOURCE_ICON" "$BUILD_ICONS_DIR/icon.png"
log_success "Linux PNG 图标生成完成"

echo ""
log_success "所有图标准备完成！"
echo ""
ls -lh "$BUILD_ICONS_DIR"

