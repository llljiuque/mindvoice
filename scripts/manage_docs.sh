#!/bin/bash

# 文档管理工具
# 功能：分析项目文档结构，识别需要归档的过程性文档，并执行归档操作
# 策略：临时文档应在 temp_docs/，根目录只保留核心文档，docs/ 按用途分类

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 归档目录
ARCHIVE_DIR="docs/archive"

# 打印带颜色的标题
print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# 打印分类标题
print_category() {
    echo -e "${YELLOW}▶ $1${NC}"
}

# 打印成功信息
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# 打印警告信息
print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# 分析文档
analyze_docs() {
    print_header "📊 文档结构分析"
    
    # 统计文档数量
    ROOT_DOCS_COUNT=$(find . -maxdepth 1 -name "*.md" -type f 2>/dev/null | wc -l | tr -d ' ')
    DOCS_DIR_COUNT=$(find ./docs -name "*.md" -type f 2>/dev/null | wc -l | tr -d ' ')
    TEMP_DOCS_COUNT=$(find ./temp_docs -name "*.md" -type f 2>/dev/null | wc -l | tr -d ' ')
    TOTAL_COUNT=$((ROOT_DOCS_COUNT + DOCS_DIR_COUNT))
    
    echo "📁 文档统计："
    echo "  • 根目录: $ROOT_DOCS_COUNT 个（应保持 4-5 个核心文档）"
    echo "  • docs/ 目录: $DOCS_DIR_COUNT 个"
    echo "  • temp_docs/ 目录: $TEMP_DOCS_COUNT 个（临时文档，不上传）"
    echo "  • 总计: $TOTAL_COUNT 个"
    echo ""
    
    # 检查根目录文档
    print_category "根目录文档检查"
    echo ""
    
    CORE_DOCS=$(find . -maxdepth 1 -type f \( -name "README*.md" -o -name "CHANGELOG.md" -o -name "CONTRIBUTING.md" -o -name "LICENSE*" \) | sort)
    CORE_COUNT=$(echo "$CORE_DOCS" | grep -c "\.md" 2>/dev/null || echo "0")
    
    if [ "$CORE_COUNT" -gt 0 ]; then
        echo "  ✅ 核心文档 ($CORE_COUNT 个) - 正确"
        echo "$CORE_DOCS" | while read -r file; do
            [ -f "$file" ] && echo "     $(basename "$file")"
        done
        echo ""
    fi
    
    # 检查是否有不应该在根目录的文档
    OTHER_DOCS=$(find . -maxdepth 1 -type f -name "*.md" | grep -vE "(README|CHANGELOG|CONTRIBUTING|LICENSE)" | sort)
    OTHER_COUNT=$(echo "$OTHER_DOCS" | grep -c "\.md" 2>/dev/null || echo "0")
    
    if [ "$OTHER_COUNT" -gt 0 ]; then
        print_warning "发现 $OTHER_COUNT 个非核心文档在根目录（应移到 temp_docs/ 或归档）"
        echo "$OTHER_DOCS" | while read -r file; do
            [ -f "$file" ] && echo "     $(basename "$file")"
        done
        echo ""
    fi
    
    # 检查 temp_docs/ 目录
    if [ -d "temp_docs" ] && [ "$TEMP_DOCS_COUNT" -gt 0 ]; then
        print_category "temp_docs/ 目录检查"
        echo ""
        echo "  📝 临时文档 ($TEMP_DOCS_COUNT 个)"
        find temp_docs -name "*.md" -type f ! -name "README.md" | while read -r file; do
            echo "     $(basename "$file")"
        done
        echo ""
        if [ "$TEMP_DOCS_COUNT" -gt 10 ]; then
            print_warning "temp_docs/ 文档较多（$TEMP_DOCS_COUNT 个），建议清理"
            echo ""
        fi
    fi
    
    # 检查 docs/ 子目录中的过程性文档
    print_category "docs/ 子目录过程性文档检查"
    echo ""
    
    ARCHIVABLE_COUNT=0
    
    # 检查 docs/build/ 中的过程性文档
    if [ -d "docs/build" ]; then
        BUILD_PROCESS_DOCS=$(find docs/build -name "*_REPORT.md" -o -name "*_FIX.md" -o -name "*_SUCCESS*.md" | sort)
        BUILD_PROCESS_COUNT=$(echo "$BUILD_PROCESS_DOCS" | grep -c "\.md" 2>/dev/null || echo "0")
        if [ "$BUILD_PROCESS_COUNT" -gt 0 ]; then
            echo "  📦 docs/build/ 过程性文档 ($BUILD_PROCESS_COUNT 个) - 可归档"
            echo "$BUILD_PROCESS_DOCS" | while read -r file; do
                [ -f "$file" ] && echo "     $(basename "$file")"
            done
            echo ""
            ARCHIVABLE_COUNT=$((ARCHIVABLE_COUNT + BUILD_PROCESS_COUNT))
        fi
    fi
    
    # 检查 docs/ 根目录中的过程性文档
    if [ -d "docs" ]; then
        DOCS_PROCESS_DOCS=$(find docs -maxdepth 1 -name "*_REPORT.md" -o -name "*_CHECK*.md" -o -name "*_20[0-9][0-9][0-9][0-9][0-9][0-9].md" | sort)
        DOCS_PROCESS_COUNT=$(echo "$DOCS_PROCESS_DOCS" | grep -c "\.md" 2>/dev/null || echo "0")
        if [ "$DOCS_PROCESS_COUNT" -gt 0 ]; then
            echo "  📦 docs/ 根目录过程性文档 ($DOCS_PROCESS_COUNT 个) - 可归档"
            echo "$DOCS_PROCESS_DOCS" | while read -r file; do
                [ -f "$file" ] && echo "     $(basename "$file")"
            done
            echo ""
            ARCHIVABLE_COUNT=$((ARCHIVABLE_COUNT + DOCS_PROCESS_COUNT))
        fi
    fi
    
    if [ "$ARCHIVABLE_COUNT" -eq 0 ]; then
        print_success "docs/ 目录结构良好，未发现需要归档的过程性文档"
        echo ""
    fi
    
    return $ARCHIVABLE_COUNT
}

# 执行归档
archive_docs() {
    print_header "📦 执行文档归档"
    
    # 创建归档目录
    mkdir -p "$ARCHIVE_DIR/build"
    mkdir -p "$ARCHIVE_DIR/bugfix"
    mkdir -p "$ARCHIVE_DIR/refactor"
    mkdir -p "$ARCHIVE_DIR/feature"
    mkdir -p "$ARCHIVE_DIR/investigation"
    
    ARCHIVED_COUNT=0
    
    # 归档 docs/build/ 中的过程性文档
    if [ -d "docs/build" ]; then
        BUILD_PROCESS_DOCS=$(find docs/build -name "*_REPORT.md" -o -name "*_FIX.md" -o -name "*_SUCCESS*.md" | sort)
        if [ -n "$BUILD_PROCESS_DOCS" ]; then
            print_category "归档 docs/build/ 过程性文档"
            echo "$BUILD_PROCESS_DOCS" | while read -r file; do
                if [ -f "$file" ]; then
                    filename=$(basename "$file")
                    mv "$file" "$ARCHIVE_DIR/build/"
                    echo "  ✓ $filename"
                    ARCHIVED_COUNT=$((ARCHIVED_COUNT + 1))
                fi
            done
            echo ""
        fi
    fi
    
    # 归档 docs/ 根目录中的过程性文档
    if [ -d "docs" ]; then
        DOCS_PROCESS_DOCS=$(find docs -maxdepth 1 -name "*_REPORT.md" -o -name "*_CHECK*.md" -o -name "*_20[0-9][0-9][0-9][0-9][0-9][0-9].md" | sort)
        if [ -n "$DOCS_PROCESS_DOCS" ]; then
            print_category "归档 docs/ 根目录过程性文档"
            echo "$DOCS_PROCESS_DOCS" | while read -r file; do
                if [ -f "$file" ]; then
                    filename=$(basename "$file")
                    # 根据文件名判断归档位置
                    if echo "$filename" | grep -qE "(BUGFIX|_FIX_)"; then
                        mv "$file" "$ARCHIVE_DIR/bugfix/"
                    elif echo "$filename" | grep -qE "(CHECK|REPORT)"; then
                        mv "$file" "$ARCHIVE_DIR/investigation/"
                    else
                        mv "$file" "$ARCHIVE_DIR/feature/"
                    fi
                    echo "  ✓ $filename"
                    ARCHIVED_COUNT=$((ARCHIVED_COUNT + 1))
                fi
            done
            echo ""
        fi
    fi
    
    # 更新归档索引
    cat > "$ARCHIVE_DIR/README.md" << EOF
# 文档归档

本目录存放项目开发过程中产生的过程性文档。

## 目录结构

- \`bugfix/\` - Bug 修复记录
- \`refactor/\` - 代码重构记录
- \`feature/\` - 功能实现记录
- \`investigation/\` - 问题调研和系统检查报告
- \`build/\` - 构建过程记录

## 归档说明

这些文档记录了项目的演进历史，可用于：
1. 问题排查参考
2. 技术决策回顾
3. 开发过程学习

**最后更新**: $(date '+%Y-%m-%d %H:%M:%S')
EOF
    
    print_success "归档完成！"
    echo ""
    echo "归档位置: $ARCHIVE_DIR/"
    echo ""
}

# 主函数
main() {
    command -v clear >/dev/null 2>&1 && clear || echo ""
    echo ""
    print_header "📚 MindVoice 文档管理工具"
    echo ""
    
    # 执行分析
    analyze_docs
    ARCHIVABLE_COUNT=$?
    
    if [ "$ARCHIVABLE_COUNT" -eq 0 ]; then
        echo ""
        print_success "文档结构良好，无需操作。"
        echo ""
        
        # 检查 temp_docs/
        if [ -d "temp_docs" ] && [ "$(find temp_docs -name "*.md" -type f ! -name "README.md" | wc -l | xargs)" -gt 0 ]; then
            echo ""
            print_warning "提示：temp_docs/ 中有临时文档，完成后记得清理"
            echo "  查看: ls -la temp_docs/"
            echo "  清理: rm temp_docs/OLD_*.md 或 mv temp_docs/XXX.md docs/archive/"
            echo ""
        fi
        
        exit 0
    fi
    
    # 询问是否归档
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "是否立即归档这些文档？"
    echo ""
    echo "  [y] 是 - 归档到 docs/archive/"
    echo "  [n] 否 - 仅分析，不执行操作"
    echo ""
    read -p "请选择 (y/n): " -n 1 -r
    echo ""
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        archive_docs
        
        echo ""
        print_header "✅ 操作完成"
        echo ""
        echo "下一步建议："
        echo "  1. 查看归档结果: ls -la $ARCHIVE_DIR/*/"
        echo "  2. 检查文档结构: ./scripts/manage_docs.sh"
        echo "  3. 提交到 Git:"
        echo "     git add docs/archive/"
        echo "     git commit -m 'docs: 归档过程性文档'"
        echo ""
    else
        echo ""
        print_success "已取消归档操作。"
        echo ""
        echo "💡 提示: 随时可以再次运行此工具进行归档"
        echo "   命令: ./scripts/manage_docs.sh"
        echo ""
    fi
}

# 运行主函数
main

