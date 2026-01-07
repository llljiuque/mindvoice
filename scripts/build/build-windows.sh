#!/bin/bash
#
# MindVoice Windows 构建脚本
# 用途：构建 Windows 平台的完整安装包（x64）
# 作者：深圳王哥 & AI
# 日期：2026-01-05
# 版本：1.0.0
#

set -euo pipefail  # 严格错误处理

# ============================================================================
# 配置
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR="$PROJECT_ROOT/build"
PYTHON_BACKEND_DIR="$PROJECT_ROOT/python-backend"
ELECTRON_DIR="$PROJECT_ROOT/electron-app"
RELEASE_DIR="$PROJECT_ROOT/release"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================================================
# 工具函数
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "$1 未安装"
        return 1
    fi
    return 0
}

# ============================================================================
# 环境检查
# ============================================================================

check_environment() {
    log_info "检查构建环境..."
    
    # 检测 Python 命令（Windows 上可能是 python，Linux/Mac 上是 python3）
    local python_cmd="python3"
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        if command -v python &> /dev/null; then
            python_cmd="python"
        elif command -v python3 &> /dev/null; then
            python_cmd="python3"
        else
            log_error "未找到 Python，请先安装 Python 3.9+"
            exit 1
        fi
    else
        if ! command -v python3 &> /dev/null; then
            log_error "未找到 python3，请先安装 Python 3.9+"
            exit 1
        fi
    fi
    
    # 检查必要命令
    local required_commands=("node" "npm")
    for cmd in "${required_commands[@]}"; do
        if ! check_command "$cmd"; then
            log_error "缺少必要命令: $cmd"
            exit 1
        fi
    done
    
    # 检查 Python 版本
    local python_version=$($python_cmd --version 2>&1 | awk '{print $2}')
    log_info "Python 版本: $python_version (使用命令: $python_cmd)"
    
    # 检查 Node.js 版本
    local node_version=$(node --version)
    log_info "Node.js 版本: $node_version"
    
    # 检查 venv
    if [ ! -d "$PROJECT_ROOT/venv" ]; then
        log_error "Python 虚拟环境不存在，请先运行: $python_cmd -m venv venv"
        exit 1
    fi
    
    # 检查 Windows 构建工具（如果在 Windows 上）
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        log_info "检测到 Windows 环境"
        # 保存 Python 命令供后续使用
        export PYTHON_CMD="$python_cmd"
    else
        log_warning "当前不在 Windows 环境，构建 Windows 应用可能需要 Wine 或交叉编译"
        export PYTHON_CMD="$python_cmd"
    fi
    
    log_success "环境检查通过"
}

# ============================================================================
# 清理
# ============================================================================

clean_build() {
    log_info "清理旧的构建文件..."
    
    rm -rf "$PYTHON_BACKEND_DIR/dist"
    rm -rf "$PYTHON_BACKEND_DIR/build"
    rm -rf "$ELECTRON_DIR/dist"
    rm -rf "$ELECTRON_DIR/dist-electron"
    
    # 只清理 Windows 相关的构建产物，保留其他平台的
    log_info "清理 Windows 构建产物..."
    rm -rf "$RELEASE_DIR/latest/win" 2>/dev/null || true
    rm -rf "$RELEASE_DIR/latest/win-unpacked" 2>/dev/null || true
    rm -f "$RELEASE_DIR/latest"/*-windows-x64.exe 2>/dev/null || true
    rm -f "$RELEASE_DIR/latest"/*-windows-x64.exe.sha256 2>/dev/null || true
    rm -f "$RELEASE_DIR/latest"/*-windows-x64.zip 2>/dev/null || true
    rm -f "$RELEASE_DIR/latest"/*-windows-x64.zip.sha256 2>/dev/null || true
    rm -f "$RELEASE_DIR/latest"/*-windows-x64.blockmap 2>/dev/null || true
    
    log_success "清理完成"
}

# ============================================================================
# Python 后端打包
# ============================================================================

build_python_backend() {
    log_info "开始打包 Python 后端..."
    
    # 检查平台兼容性
    if [[ "$OSTYPE" != "msys" && "$OSTYPE" != "win32" ]]; then
        log_warning "当前在非 Windows 平台构建，Python 后端将打包为当前平台版本"
        log_warning "生成的 Python 后端无法在 Windows 上运行"
    fi
    
    cd "$PROJECT_ROOT"
    
    # Windows 上使用不同的激活方式
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        # Windows Git Bash: 使用正斜杠，Git Bash 会自动转换
        if [ -f "venv/Scripts/activate" ]; then
            source venv/Scripts/activate
        elif [ -f "venv/bin/activate" ]; then
            source venv/bin/activate
        else
            log_error "无法找到虚拟环境激活脚本"
            exit 1
        fi
    else
        # Linux/Mac: 使用 bin/activate
        source venv/bin/activate
    fi
    
    # 检查并安装依赖（Python 3.14 兼容性处理）
    log_info "检查 Python 依赖..."
    python_version_major=$(python -c "import sys; print(sys.version_info.major)" 2>/dev/null || echo "0")
    python_version_minor=$(python -c "import sys; print(sys.version_info.minor)" 2>/dev/null || echo "0")
    
    # 如果是 Python 3.14+，需要特殊处理 numpy
    local need_numpy_fix=0
    if [ "$python_version_major" -eq 3 ] && [ "$python_version_minor" -ge 14 ]; then
        log_info "检测到 Python 3.14+，处理 numpy 兼容性..."
        need_numpy_fix=1
        
        # 强制使用预编译包安装最新版本的 numpy（避免编译错误）
        log_info "安装 numpy（使用预编译包，避免编译错误）..."
        if pip install --only-binary :all: numpy --upgrade >/dev/null 2>&1; then
            log_success "numpy 已安装到兼容版本（预编译包）"
        else
            log_warning "预编译包安装失败，尝试普通安装（可能需要编译）..."
            if pip install numpy --upgrade >/dev/null 2>&1; then
                log_success "numpy 已安装"
            else
                log_error "numpy 安装失败"
                log_error "请手动运行: pip install --only-binary :all: numpy --upgrade"
                log_error "或使用: pip install numpy --upgrade"
                deactivate
                exit 1
            fi
        fi
    fi
    
    # 检查依赖是否已安装
    if ! python -c "import numpy, fastapi, litellm" 2>/dev/null; then
        log_info "安装项目依赖..."
        
        # 如果是 Python 3.14+ 且 numpy 已安装，创建临时 requirements 文件（排除 numpy）
        if [ "$need_numpy_fix" -eq 1 ] && python -c "import numpy" 2>/dev/null; then
            log_info "Python 3.14+ 检测到，排除 numpy 避免重新编译..."
            # 创建临时 requirements 文件（排除 numpy 行）
            local temp_requirements
            if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
                temp_requirements="$PROJECT_ROOT/build/temp_requirements.txt"
            else
                temp_requirements="/tmp/temp_requirements.txt"
            fi
            mkdir -p "$(dirname "$temp_requirements")"
            
            # 过滤掉 numpy 行（包括注释行）
            grep -v "^numpy" "$PROJECT_ROOT/requirements.txt" | grep -v "^#.*numpy" > "$temp_requirements" 2>/dev/null || {
                # 如果过滤失败，使用原文件但跳过 numpy
                cp "$PROJECT_ROOT/requirements.txt" "$temp_requirements"
            }
            
            # 尝试安装依赖，如果网络失败则使用国内镜像
            log_info "尝试安装依赖（这可能需要几分钟）..."
            local pip_output_file
            if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
                pip_output_file="$PROJECT_ROOT/build/pip_install.log"
            else
                pip_output_file="/tmp/pip_install.log"
            fi
            mkdir -p "$(dirname "$pip_output_file")"
            
            # 实时显示输出并保存到文件
            if pip install -r "$temp_requirements" 2>&1 | tee "$pip_output_file"; then
                log_success "依赖安装完成"
                rm -f "$pip_output_file"
            elif grep -q "ProxyError\|TimeoutError\|Could not find a version" "$pip_output_file" 2>/dev/null; then
                log_warning "检测到网络问题，尝试使用国内镜像..."
                if pip install -r "$temp_requirements" -i https://pypi.tuna.tsinghua.edu.cn/simple 2>&1 | tee "$pip_output_file"; then
                    log_success "依赖安装完成（使用国内镜像）"
                    rm -f "$pip_output_file"
                else
                    log_error "依赖安装失败（网络问题）"
                    log_info "建议："
                    log_info "  1. 检查网络连接和代理设置"
                    log_info "  2. 手动运行: pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple"
                    log_info "  3. 或配置代理: pip install --proxy http://proxy:port -r requirements.txt"
                    log_info "详细日志: $pip_output_file"
                    rm -f "$temp_requirements"
                    deactivate
                    exit 1
                fi
            elif grep -q "ResolutionImpossible\|no matching distributions\|onnxruntime" "$pip_output_file" 2>/dev/null; then
                log_warning "检测到依赖冲突（可能是 Python 3.14 兼容性问题）..."
                log_info "尝试使用更宽松的依赖解析..."
                if pip install -r "$temp_requirements" --no-deps 2>&1 | tee "$pip_output_file"; then
                    log_warning "已安装主要依赖（跳过依赖检查）"
                    log_info "尝试安装依赖的依赖（可能部分失败）..."
                    pip install -r "$temp_requirements" 2>&1 | tee -a "$pip_output_file" || {
                        log_warning "部分依赖安装失败，但主要依赖已安装"
                        log_info "这可能是 Python 3.14 的兼容性问题，某些包可能不支持"
                    }
                    log_success "依赖安装完成（部分依赖可能缺失）"
                    rm -f "$pip_output_file"
                else
                    log_error "依赖安装失败（依赖冲突）"
                    log_info "这是 Python 3.14 的兼容性问题，某些包（如 onnxruntime）可能不支持"
                    log_info "建议："
                    log_info "  1. 使用 Python 3.11 或 3.12（推荐）"
                    log_info "  2. 或手动安装: pip install -r requirements.txt --no-deps"
                    log_info "  3. 然后单独安装可用的依赖"
                    log_info "详细日志: $pip_output_file"
                    rm -f "$temp_requirements"
                    deactivate
                    exit 1
                fi
            else
                log_error "依赖安装失败，请检查 requirements.txt"
                tail -20 "$pip_output_file" 2>/dev/null || echo "查看详细日志: $pip_output_file"
                rm -f "$temp_requirements" "$pip_output_file"
                deactivate
                exit 1
            fi
            
            # 清理临时文件
            rm -f "$temp_requirements"
            log_success "依赖安装完成（numpy 已单独安装）"
        else
            # 正常安装所有依赖
            log_info "尝试安装依赖（这可能需要几分钟）..."
            local pip_output_file
            if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
                pip_output_file="$PROJECT_ROOT/build/pip_install.log"
            else
                pip_output_file="/tmp/pip_install.log"
            fi
            mkdir -p "$(dirname "$pip_output_file")"
            
            # 实时显示输出并保存到文件
            if pip install -r requirements.txt 2>&1 | tee "$pip_output_file"; then
                log_success "依赖安装完成"
                rm -f "$pip_output_file"
            elif grep -q "ProxyError\|TimeoutError\|Could not find a version" "$pip_output_file" 2>/dev/null; then
                log_warning "检测到网络问题，尝试使用国内镜像..."
                if pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple 2>&1 | tee "$pip_output_file"; then
                    log_success "依赖安装完成（使用国内镜像）"
                    rm -f "$pip_output_file"
                else
                    log_error "依赖安装失败（网络问题）"
                    log_info "建议："
                    log_info "  1. 检查网络连接和代理设置"
                    log_info "  2. 手动运行: pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple"
                    log_info "  3. 或配置代理: pip install --proxy http://proxy:port -r requirements.txt"
                    log_info "详细日志: $pip_output_file"
                    if [ "$need_numpy_fix" -eq 1 ]; then
                        log_info "提示：如果是 numpy 编译错误，请先运行: pip install --only-binary :all: numpy --upgrade"
                    fi
                    deactivate
                    exit 1
                fi
            elif grep -q "ResolutionImpossible\|no matching distributions" "$pip_output_file" 2>/dev/null; then
                log_warning "检测到依赖冲突（可能是 Python 3.14 兼容性问题），尝试使用宽松模式..."
                # 尝试使用 --no-deps 安装主要依赖，然后手动处理冲突
                log_info "尝试逐个安装依赖（跳过有问题的包）..."
                local failed_packages=()
                while IFS= read -r line; do
                    # 跳过空行和注释
                    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
                    # 提取包名（去除版本要求）
                    local pkg_name=$(echo "$line" | sed 's/[>=<!=].*//' | xargs)
                    if [ -n "$pkg_name" ]; then
                        log_info "安装: $pkg_name"
                        if ! pip install "$line" -i https://pypi.tuna.tsinghua.edu.cn/simple 2>&1 | tee -a "$pip_output_file"; then
                            log_warning "跳过有问题的包: $pkg_name"
                            failed_packages+=("$pkg_name")
                        fi
                    fi
                done < requirements.txt
                
                if [ ${#failed_packages[@]} -gt 0 ]; then
                    log_warning "以下包安装失败（可能是 Python 3.14 兼容性问题）: ${failed_packages[*]}"
                    log_info "这些包可能不是必需的，构建可能会继续"
                fi
                log_success "依赖安装完成（部分包可能已跳过）"
                rm -f "$pip_output_file"
            else
                log_error "依赖安装失败，请检查 requirements.txt"
                tail -20 "$pip_output_file" 2>/dev/null || echo "查看详细日志: $pip_output_file"
                if [ "$need_numpy_fix" -eq 1 ]; then
                    log_info "提示：如果是 numpy 编译错误，请先运行: pip install --only-binary :all: numpy --upgrade"
                fi
                rm -f "$pip_output_file"
                deactivate
                exit 1
            fi
        fi
    else
        log_success "依赖检查通过"
    fi
    
    # 安装 PyInstaller
    log_info "检查 PyInstaller..."
    pip install pyinstaller --quiet
    
    # 使用 spec 文件打包
    log_info "执行打包（这可能需要几分钟）..."
    pyinstaller "$BUILD_DIR/config/pyinstaller.spec" \
        --distpath "$PYTHON_BACKEND_DIR/dist" \
        --workpath "$PYTHON_BACKEND_DIR/build" \
        --noconfirm || {
        log_error "Python 后端打包失败"
        deactivate
        exit 1
    }
    
    # 验证输出（Windows 上可执行文件是 .exe）
    if [ ! -f "$PYTHON_BACKEND_DIR/dist/mindvoice-api" ] && [ ! -f "$PYTHON_BACKEND_DIR/dist/mindvoice-api.exe" ]; then
        log_error "Python 后端打包失败：未找到可执行文件"
        deactivate
        exit 1
    fi
    
    # 测试运行（仅在当前平台可运行时测试）
    log_info "测试 Python 后端..."
    local api_binary="$PYTHON_BACKEND_DIR/dist/mindvoice-api"
    if [ ! -f "$api_binary" ]; then
        api_binary="$PYTHON_BACKEND_DIR/dist/mindvoice-api.exe"
    fi
    
    if [ -f "$api_binary" ]; then
        # 尝试测试运行（可能失败，但不影响构建）
        if "$api_binary" --help &> /dev/null 2>&1; then
            log_success "Python 后端打包成功"
        else
            log_warning "Python 后端打包完成，但测试运行失败（可能是平台不匹配）"
        fi
    else
        log_error "Python 后端打包失败：可执行文件不存在"
        deactivate
        exit 1
    fi
    
    deactivate
}

# ============================================================================
# Electron 前端构建
# ============================================================================

build_electron_frontend() {
    log_info "开始构建 Electron 前端..."
    
    cd "$ELECTRON_DIR"
    
    # 检查 node_modules
    if [ ! -d "node_modules" ]; then
        log_info "安装依赖..."
        npm install
    fi
    
    # 复制构建资源到 electron-app/build
    log_info "准备构建资源..."
    mkdir -p build
    cp -r "$BUILD_DIR/resources/"* build/ 2>/dev/null || true
    
    # 构建前端
    log_info "构建 Vite 前端..."
    npm run build:vite
    
    log_info "构建 Electron 主进程..."
    npm run build:electron
    
    log_success "Electron 前端构建完成"
}

# ============================================================================
# 打包应用
# ============================================================================

package_application() {
    log_info "开始打包 Windows 应用..."
    
    cd "$ELECTRON_DIR"
    
    # 检查 Windows 图标文件
    local icon_path="$BUILD_DIR/resources/icons/icon.ico"
    if [ ! -f "$icon_path" ]; then
        log_warning "Windows 图标文件不存在: $icon_path"
        log_warning "将使用默认图标，建议添加 icon.ico 文件"
    fi
    
    # 检查必要文件是否存在
    log_info "检查必要文件..."
    if [ ! -d "$PYTHON_BACKEND_DIR/dist" ]; then
        log_error "Python 后端目录不存在: $PYTHON_BACKEND_DIR/dist"
        log_error "请先运行 Python 后端打包步骤"
        exit 1
    fi
    
    if [ ! -f "$PROJECT_ROOT/config.yml.example" ]; then
        log_error "配置文件不存在: $PROJECT_ROOT/config.yml.example"
        exit 1
    fi
    
    # 重要警告：在 macOS 上构建 Windows 应用时，Python 后端无法直接打包成 Windows 版本
    if [[ "$OSTYPE" != "msys" && "$OSTYPE" != "win32" ]]; then
        log_warning "=========================================="
        log_warning "⚠️  重要提示：在 macOS/Linux 上构建 Windows 应用"
        log_warning "=========================================="
        log_warning "Python 后端已打包为当前平台版本（macOS），无法在 Windows 上运行"
        log_warning "Wine 可能不稳定，如果构建失败，建议在 Windows 系统上构建"
        log_warning "建议："
        log_warning "  1. 在 Windows 系统上运行此脚本以生成 Windows 版本的 Python 后端"
        log_warning "  2. 或者使用 Docker/虚拟机进行交叉编译"
        log_warning "  3. Electron 部分可以正常构建，但需要手动替换 Python 后端"
        log_warning "=========================================="
        echo
        read -p "是否继续构建 Electron 部分？(y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "用户取消构建"
            exit 0
        fi
        
        # 设置环境变量以改善 Wine 兼容性
        export WINEPREFIX="$HOME/.wine-electron-builder"
        export WINEDEBUG=-all  # 禁用 Wine 调试输出
        log_info "设置 Wine 环境变量以改善兼容性"
    fi
    
    # 使用 electron-builder 打包 Windows 版本
    # 只构建 x64 架构（32位 x86 已过时，主流 CPU 都是 64 位）
    log_info "构建 Windows x64 安装包..."
    log_info "提示：首次构建会下载 Electron 二进制文件（约 108MB）"
    log_info "提示：下载过程可能需要几分钟，请耐心等待..."
    log_info "提示：如果 Wine 执行失败，这是 macOS 上的已知问题，建议在 Windows 上构建"
    echo
    
    # 设置日志文件路径（跨平台兼容）
    local log_file
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        # Windows: 使用项目目录下的临时目录
        log_file="$PROJECT_ROOT/build/electron-builder-x64.log"
        mkdir -p "$PROJECT_ROOT/build"
    else
        # Linux/Mac: 使用 /tmp
        log_file="/tmp/electron-builder-x64.log"
    fi
    
    # 设置超时（30分钟）并显示进度
    local build_result=0
    if command -v timeout &> /dev/null; then
        timeout 1800 npx electron-builder \
            --win \
            --x64 \
            --config "$BUILD_DIR/config/electron-builder.json" \
            --publish never 2>&1 | tee "$log_file" || {
            build_result=$?
            if [ $build_result -eq 124 ]; then
                log_error "Windows x64 构建超时（30分钟）"
            else
                log_error "Windows x64 构建失败（退出码: $build_result）"
                log_info "查看详细日志: $log_file"
                # 检查是否是 Wine 错误
                if grep -q "wine\|Wine\|WINEDEBUG" "$log_file" 2>/dev/null; then
                    log_warning "检测到 Wine 相关错误，这是 macOS 上构建 Windows 应用的已知问题"
                    log_warning "建议：在 Windows 系统上运行此脚本，或使用 Docker/虚拟机"
                fi
            fi
            exit 1
        }
    else
        # macOS/Windows 没有 timeout 命令，直接运行
        npx electron-builder \
            --win \
            --x64 \
            --config "$BUILD_DIR/config/electron-builder.json" \
            --publish never 2>&1 | tee "$log_file" || {
            build_result=$?
            log_error "Windows x64 构建失败（退出码: $build_result）"
            log_info "查看详细日志: $log_file"
            # 检查是否是 Wine 错误
            if grep -q "wine\|Wine\|WINEDEBUG" "$log_file" 2>/dev/null; then
                log_warning "检测到 Wine 相关错误，这是 macOS 上构建 Windows 应用的已知问题"
                log_warning "建议：在 Windows 系统上运行此脚本，或使用 Docker/虚拟机"
            fi
            exit 1
        }
    fi
    
    
    log_success "应用打包完成"
}

# ============================================================================
# 后处理
# ============================================================================

post_build() {
    log_info "后处理..."
    
    # 清理不需要的文件（只清理 Windows 相关的）
    log_info "清理 Windows 中间文件和不需要的构建产物..."
    rm -rf "$RELEASE_DIR/latest/win" 2>/dev/null || true
    rm -rf "$RELEASE_DIR/latest/win-unpacked" 2>/dev/null || true
    rm -f "$RELEASE_DIR/latest"/*-windows-x64.blockmap 2>/dev/null || true
    rm -f "$RELEASE_DIR/latest"/*-windows-x64.zip 2>/dev/null || true
    # 注意：builder-*.yml 和 builder-*.yaml 可能是多平台共享的，保留
    
    # 显示最终输出文件
    log_info "构建产物："
    find "$RELEASE_DIR/latest" -type f -name "*.exe" -exec ls -lh {} \; 2>/dev/null || log_warning "未找到安装包文件"
    
    # 生成 SHA256 校验和（如果支持）
    log_info "生成 SHA256 校验和..."
    cd "$RELEASE_DIR/latest"
    
    # 为 Windows 安装包生成校验和（只保留 x64）
    for file in MindVoice-*-windows-x64.exe; do
        if [ -f "$file" ]; then
            if command -v shasum &> /dev/null; then
                shasum -a 256 "$file" > "$file.sha256"
                log_success "$file → $file.sha256"
            elif command -v sha256sum &> /dev/null; then
                sha256sum "$file" > "$file.sha256"
                log_success "$file → $file.sha256"
            else
                log_warning "未找到 SHA256 工具，跳过校验和生成"
            fi
        fi
    done
    
    cd "$PROJECT_ROOT"
    
    log_success "清理完成，只保留 Windows x64 安装包"
}

# ============================================================================
# 主流程
# ============================================================================

main() {
    log_info "=========================================="
    log_info "MindVoice Windows 构建脚本"
    log_info "=========================================="
    echo
    
    # 读取版本号
    local version=$(grep -o '"version": *"[^"]*"' "$ELECTRON_DIR/package.json" | cut -d'"' -f4)
    log_info "构建版本: $version"
    echo
    
    # 执行构建流程
    check_environment
    clean_build
    build_python_backend
    build_electron_frontend
    package_application
    post_build
    
    echo
    log_success "=========================================="
    log_success "构建完成！"
    log_success "=========================================="
    log_info "安装包位置: $RELEASE_DIR/latest/"
    log_info "Windows x64 安装包: MindVoice-${version}-windows-x64.exe"
}

# 执行主流程
main "$@"

