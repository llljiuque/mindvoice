#!/bin/bash

# 版本号更新脚本
# 用法: ./update_version.sh <新版本号> [发布日期]
# 示例: ./update_version.sh 1.1.0
# 如果不指定发布日期，将自动使用当前日期

if [ -z "$1" ]; then
  echo "错误: 请提供版本号"
  echo "用法: ./update_version.sh <版本号> [发布日期]"
  echo "示例: ./update_version.sh 1.1.0"
  echo "       ./update_version.sh 1.1.0 2025-12-31"
  exit 1
fi

VERSION=$1
RELEASE_DATE=${2:-$(date +%Y-%m-%d)}

echo "正在更新版本号到: $VERSION"
echo "发布日期: $RELEASE_DATE"

# 更新 electron-app/src/version.ts
VERSION_FILE="electron-app/src/version.ts"
if [ -f "$VERSION_FILE" ]; then
  sed -i.bak "s/version: '[^']*'/version: '$VERSION'/" "$VERSION_FILE"
  sed -i.bak "s/releaseDate: '[^']*'/releaseDate: '$RELEASE_DATE'/" "$VERSION_FILE"
  rm "${VERSION_FILE}.bak" 2>/dev/null
  echo "✓ 已更新 $VERSION_FILE"
else
  echo "✗ 文件不存在: $VERSION_FILE"
  exit 1
fi

# 更新 electron-app/package.json
PACKAGE_FILE="electron-app/package.json"
if [ -f "$PACKAGE_FILE" ]; then
  sed -i.bak "s/\"version\": \"[^\"]*\"/\"version\": \"$VERSION\"/" "$PACKAGE_FILE"
  rm "${PACKAGE_FILE}.bak" 2>/dev/null
  echo "✓ 已更新 $PACKAGE_FILE"
else
  echo "✗ 文件不存在: $PACKAGE_FILE"
  exit 1
fi

echo ""
echo "版本号更新完成！"
echo "请检查以下文件的变更:"
echo "  - $VERSION_FILE"
echo "  - $PACKAGE_FILE"

