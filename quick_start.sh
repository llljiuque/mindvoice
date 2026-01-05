#!/bin/bash

# =============================================================
# macOS 语音桌面助手 - 快速启动脚本
# 功能：自动检查环境、部署依赖、运行应用
# =============================================================

# 设置编码为 UTF-8
export LANG=zh_CN.UTF-8
export LC_ALL=zh_CN.UTF-8

# 不使用 set -e，手动处理错误
set +e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"
PYTHON_CMD="python3"
API_PORT=8765
API_HOST="127.0.0.1"

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查命令是否存在
check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# 检查 Python 环境
check_python() {
    print_info "检查 Python 环境..."
    
    if ! check_command "$PYTHON_CMD"; then
        print_error "未找到 $PYTHON_CMD，请先安装 Python 3"
        exit 1
    fi
    
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
    print_success "Python 版本: $PYTHON_VERSION"
    
    # 检查 Python 版本是否 >= 3.9
    MAJOR_VERSION=$(echo $PYTHON_VERSION | cut -d. -f1)
    MINOR_VERSION=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [ "$MAJOR_VERSION" -lt 3 ] || ([ "$MAJOR_VERSION" -eq 3 ] && [ "$MINOR_VERSION" -lt 9 ]); then
        print_error "需要 Python 3.9 或更高版本，当前版本: $PYTHON_VERSION"
        exit 1
    fi
}

# 检查系统依赖
check_system_deps() {
    print_info "检查系统依赖..."
    
    # 检查操作系统
    if [[ "$OSTYPE" == "darwin"* ]]; then
        print_info "检测到 macOS 系统"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        print_info "检测到 Linux 系统"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        print_info "检测到 Windows 系统"
    else
        print_warning "未知操作系统: $OSTYPE"
    fi
    
    # 检查必要的系统工具
    local missing_deps=()
    
    if ! check_command "pip3"; then
        missing_deps+=("pip3")
    fi
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        print_error "缺少以下依赖: ${missing_deps[*]}"
        print_info "请运行: brew install python3"
        exit 1
    fi
    
    print_success "系统依赖检查通过"
}

# 创建虚拟环境
setup_venv() {
    print_info "设置虚拟环境..."
    
    if [ -d "$VENV_DIR" ]; then
        print_info "虚拟环境已存在，跳过创建"
    else
        print_info "创建虚拟环境..."
        $PYTHON_CMD -m venv "$VENV_DIR"
        print_success "虚拟环境创建成功"
    fi
    
    # 激活虚拟环境
    source "$VENV_DIR/bin/activate"
    
    # 升级 pip
    print_info "升级 pip..."
    pip install --upgrade pip --quiet
    
    print_success "虚拟环境设置完成"
}

# 安装依赖
install_dependencies() {
    print_info "安装项目依赖..."
    
    if [ ! -f "$PROJECT_DIR/requirements.txt" ]; then
        print_error "未找到 requirements.txt"
        exit 1
    fi
    
    # 检查是否需要安装依赖
    # 比较 requirements.txt 的修改时间与 .installed 标记
    if [ -f "$VENV_DIR/.installed" ]; then
        if [ "$PROJECT_DIR/requirements.txt" -nt "$VENV_DIR/.installed" ]; then
            print_info "requirements.txt 已更新，重新安装依赖..."
            rm -f "$VENV_DIR/.installed"
        else
            print_info "依赖已安装，跳过..."
            return
        fi
    fi
    
    pip install -r "$PROJECT_DIR/requirements.txt" --quiet
    
    # 标记已安装（记录 requirements.txt 的修改时间）
    touch "$VENV_DIR/.installed"
    
    print_success "依赖安装完成"
}

# 检查配置
check_config() {
    print_info "检查配置..."
    
    # 检查项目根目录的 config.yml
    PROJECT_CONFIG_YML="$PROJECT_DIR/config.yml"
    
    if [ -f "$PROJECT_CONFIG_YML" ]; then
        print_success "配置文件存在: $PROJECT_CONFIG_YML"
    else
        print_warning "配置文件不存在，将使用默认配置"
        if [ -f "$PROJECT_DIR/config.yml.example" ]; then
            print_info "可以复制示例配置文件："
            print_info "  cp config.yml.example config.yml"
            print_info "然后编辑 config.yml 填入你的 API 密钥"
        fi
    fi
}

# 检查权限
check_permissions() {
    print_info "检查 macOS 权限..."
    
    # 检查麦克风权限（macOS 10.14+）
    if [[ "$OSTYPE" == "darwin"* ]]; then
        print_info "请确保已授予应用麦克风权限："
        print_info "系统偏好设置 → 安全性与隐私 → 隐私 → 麦克风"
        print_info "如果未授予权限，应用可能无法录音"
    fi
}

# 验证安装
verify_installation() {
    print_info "验证安装..."
    
    # 检查关键模块
    local modules=("fastapi" "uvicorn" "sounddevice" "aiohttp")
    local missing_modules=()
    
    for module in "${modules[@]}"; do
        if ! python -c "import ${module}" 2>/dev/null; then
            missing_modules+=("$module")
        fi
    done
    
    if [ ${#missing_modules[@]} -gt 0 ]; then
        print_error "以下模块未正确安装: ${missing_modules[*]}"
        print_info "尝试重新安装依赖..."
        rm -f "$VENV_DIR/.installed"
        install_dependencies
    else
        print_success "所有关键模块验证通过"
    fi
}

# 检查 Node.js 环境
check_nodejs() {
    print_info "检查 Node.js 环境..."
    
    if ! check_command "node"; then
        print_warning "未找到 Node.js，Electron 前端将无法运行"
        print_info "请安装 Node.js 18+: https://nodejs.org/"
        return 1
    fi
    
    NODE_VERSION=$(node --version)
    print_success "Node.js 版本: $NODE_VERSION"
    
    if ! check_command "npm"; then
        print_warning "未找到 npm"
        return 1
    fi
    
    NPM_VERSION=$(npm --version)
    print_success "npm 版本: $NPM_VERSION"
    return 0
}

# 安装 Electron 前端依赖
install_electron_deps() {
    print_info "检查 Electron 前端依赖..."
    
    ELECTRON_DIR="$PROJECT_DIR/electron-app"
    
    if [ ! -d "$ELECTRON_DIR" ]; then
        print_warning "Electron 前端目录不存在: $ELECTRON_DIR"
        return 1
    fi
    
    if [ ! -f "$ELECTRON_DIR/package.json" ]; then
        print_warning "未找到 package.json"
        return 1
    fi
    
    cd "$ELECTRON_DIR"
    
    # 安装 npm 依赖
    if [ ! -d "$ELECTRON_DIR/node_modules" ]; then
        print_info "安装 Electron 前端依赖..."
        if npm install; then
            print_success "Electron 前端依赖安装完成"
        else
            print_error "Electron 前端依赖安装失败"
            cd "$PROJECT_DIR"
            return 1
        fi
    else
        print_info "Electron 前端依赖已安装"
    fi
    
    # 检查并构建 Electron 主进程代码
    if [ ! -f "$ELECTRON_DIR/dist-electron/main.js" ]; then
        print_info "构建 Electron 主进程代码..."
        if npm run build:electron; then
            print_success "Electron 主进程代码构建完成"
        else
            print_error "Electron 主进程代码构建失败"
            cd "$PROJECT_DIR"
            return 1
        fi
    else
        # 检查源代码是否有更新
        if [ "$ELECTRON_DIR/electron/main.ts" -nt "$ELECTRON_DIR/dist-electron/main.js" ] || \
           [ "$ELECTRON_DIR/electron/preload.ts" -nt "$ELECTRON_DIR/dist-electron/preload.js" ]; then
            print_info "检测到 Electron 源代码更新，重新构建..."
            if npm run build:electron; then
                print_success "Electron 主进程代码重新构建完成"
            else
                print_error "Electron 主进程代码重新构建失败"
                cd "$PROJECT_DIR"
                return 1
            fi
        else
            print_info "Electron 主进程代码已构建"
        fi
    fi
    
    cd "$PROJECT_DIR"
    return 0
}

# 检查端口是否被占用
check_port() {
    local port=$1
    local host=${2:-"127.0.0.1"}
    
    # 使用 Python 尝试绑定端口（最可靠的方法）
    # 如果能绑定成功，说明端口未被占用；如果失败，说明端口被占用
    # 使用 SO_REUSEADDR 来允许在 TIME_WAIT 状态下绑定
    # 这样可以区分真正的端口占用（LISTENING）和临时状态（TIME_WAIT）
    python3 <<EOF >/dev/null 2>&1
import socket
import sys
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(0.1)
try:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('$host', $port))
    s.close()
    sys.exit(1)  # 端口未被占用（可以绑定）
except OSError:
    s.close()
    sys.exit(0)  # 端口被占用（无法绑定）
EOF
    if [ $? -eq 0 ]; then
        return 0  # 端口被占用（绑定失败）
    fi
    
    # 使用 netstat 检查 LISTENING 状态（备用方法，仅检查真正监听的连接）
    if command -v netstat >/dev/null 2>&1; then
        if netstat -an 2>/dev/null | grep -q ":$port.*LISTEN"; then
            return 0  # 端口被占用（有进程在监听）
        fi
    fi
    
    # 使用 lsof 检查 LISTENING 状态（仅检查真正监听的连接）
    if command -v lsof >/dev/null 2>&1; then
        if lsof -i :$port 2>/dev/null | grep -q "LISTEN"; then
            return 0  # 端口被占用（有进程在监听）
        fi
    fi
    
    return 1  # 端口未被占用
}

# 快速端口检查（优化版本）
check_port_fast() {
    local port=$1
    local host=${2:-"127.0.0.1"}
    
    # 使用 Python 快速检查（最可靠）
    python3 -c "
import socket
import sys
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(0.1)
try:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('$host', $port))
    s.close()
    sys.exit(1)  # 端口未被占用
except OSError:
    s.close()
    sys.exit(0)  # 端口被占用
" 2>/dev/null
    
    return $?
}

# 检查程序是否正在运行（API 服务器响应正常）
check_program_running() {
    local port=${1:-$API_PORT}
    local host=${2:-$API_HOST}
    
    # 检查 API 服务器是否响应
    if command -v curl >/dev/null 2>&1; then
        local http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 1 --connect-timeout 1 "http://$host:$port/api/status" 2>/dev/null || echo "000")
        if [ "$http_code" = "200" ]; then
            return 0  # 程序正在运行
        fi
    fi
    
    # 备用方案：检查根路径
    if command -v curl >/dev/null 2>&1; then
        local http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 1 --connect-timeout 1 "http://$host:$port/" 2>/dev/null || echo "000")
        if [ "$http_code" = "200" ] || [ "$http_code" = "404" ] || [ "$http_code" = "307" ]; then
            return 0  # 程序正在运行
        fi
    fi
    
    return 1  # 程序未运行
}

# 检查是否有残余进程（进程存在但 API 不响应）
check_zombie_processes() {
    local port=${1:-$API_PORT}
    local found=false
    
    # 检查端口是否被占用
    if check_port_fast $port $API_HOST; then
        found=true
    fi
    
    # 检查是否有相关进程
    local api_pids=$(pgrep -f "api_server.py" 2>/dev/null || true)
    if [ -n "$api_pids" ]; then
        found=true
    fi
    
    if [ "$found" = true ]; then
        return 0  # 发现残余进程
    fi
    
    return 1  # 没有残余进程
}

# 获取运行中的进程信息
get_running_process_info() {
    local port=${1:-$API_PORT}
    local info=""
    
    # 获取占用端口的进程信息
    if command -v lsof >/dev/null 2>&1; then
        local port_info=$(lsof -i :$port 2>/dev/null | grep LISTEN | head -1)
        if [ -n "$port_info" ]; then
            info="$info\n端口 $port: $port_info"
        fi
    fi
    
    # 获取 API 服务器进程信息
    local api_pids=$(pgrep -f "api_server.py" 2>/dev/null || true)
    if [ -n "$api_pids" ]; then
        for pid in $api_pids; do
            local pid_info=$(ps -p $pid -o pid,etime,command 2>/dev/null | tail -1)
            if [ -n "$pid_info" ]; then
                info="$info\nAPI 服务器进程: $pid_info"
            fi
        done
    fi
    
    # 获取 Electron 进程信息
    local electron_pids=$(pgrep -f "electron" 2>/dev/null | grep -v "^$$$" || true)
    if [ -n "$electron_pids" ]; then
        for pid in $electron_pids; do
            local pid_info=$(ps -p $pid -o pid,etime,command 2>/dev/null | tail -1)
            if [ -n "$pid_info" ]; then
                info="$info\nElectron 进程: $pid_info"
            fi
        done
    fi
    
    echo -e "$info"
}

# 检查单实例运行（在启动前检查）
check_single_instance() {
    local force_clean=${1:-false}  # 是否强制清理
    
    # 1. 检查程序是否正在正常运行
    if check_program_running $API_PORT $API_HOST; then
        print_warning "程序已经在运行中！"
        echo ""
        print_info "运行中的进程信息："
        get_running_process_info $API_PORT | sed 's/^/  /'
        echo ""
        
        if [ "$force_clean" = true ]; then
            print_info "强制清理模式：停止旧实例并启动新实例..."
            cleanup_processes $API_PORT
            sleep 1
            return 0
        fi
        
        print_info "选项："
        print_info "  1. 退出（保持当前运行的程序）"
        print_info "  2. 停止旧实例并启动新实例"
        echo ""
        
        # 非交互模式（CI/CD 或脚本调用）时，默认退出
        if [ ! -t 0 ] || [ -n "$CI" ]; then
            print_info "非交互模式，退出..."
            exit 0
        fi
        
        # 交互模式，询问用户
        while true; do
            read -p "请选择 [1/2] (默认: 1): " choice
            choice=${choice:-1}
            
            case $choice in
                1)
                    print_info "退出，保持当前程序运行"
                    exit 0
                    ;;
                2)
                    print_info "停止旧实例并启动新实例..."
                    cleanup_processes $API_PORT
                    sleep 1
                    return 0
                    ;;
                *)
                    print_warning "无效选择，请输入 1 或 2"
                    ;;
            esac
        done
    fi
    
    # 2. 检查是否有残余进程（进程存在但 API 不响应）
    if check_zombie_processes $API_PORT; then
        print_warning "检测到残余进程（可能是上次异常关闭导致的）"
        echo ""
        print_info "发现的进程："
        get_running_process_info $API_PORT | sed 's/^/  /'
        echo ""
        
        if [ "$force_clean" = true ]; then
            print_info "强制清理模式：自动清理残余进程..."
            cleanup_processes $API_PORT
            sleep 1
            return 0
        fi
        
        print_info "正在自动清理残余进程..."
        cleanup_processes $API_PORT
        sleep 1
    fi
    
    return 0
}

# 清理函数（优化版本：更快、更可靠）
cleanup_processes() {
    local port=${1:-8765}
    print_info "正在清理进程..."
    
    # 收集所有需要终止的进程 PID（一次性收集，避免重复查询）
    local all_pids=""
    
    # 查找占用指定端口的进程
    if command -v lsof >/dev/null 2>&1; then
        local port_pids=$(lsof -ti :$port 2>/dev/null || true)
        if [ -n "$port_pids" ]; then
            all_pids="$all_pids $port_pids"
        fi
    fi
    
    # 查找 API 服务器进程
    local api_pids=$(pgrep -f "api_server.py" 2>/dev/null || true)
    if [ -n "$api_pids" ]; then
        all_pids="$all_pids $api_pids"
    fi
    
    # 查找 Electron 进程（排除当前脚本进程）
    local electron_pids=$(pgrep -f "electron" 2>/dev/null | grep -v "^$$$" || true)
    if [ -n "$electron_pids" ]; then
        all_pids="$all_pids $electron_pids"
    fi
    
    # 查找 Vite 进程（排除当前脚本进程）
    local vite_pids=$(pgrep -f "vite" 2>/dev/null | grep -v "^$$$" || true)
    if [ -n "$vite_pids" ]; then
        all_pids="$all_pids $vite_pids"
    fi
    
    # 如果找到进程，统一终止
    if [ -n "$all_pids" ]; then
        # 去重并发送 TERM 信号
        echo "$all_pids" | tr ' ' '\n' | sort -u | xargs kill -TERM 2>/dev/null || true
        # 等待 0.5 秒让进程优雅退出
        sleep 0.5
        
        # 检查哪些进程还在运行，强制终止
        local remaining_pids=""
        for pid in $all_pids; do
            if kill -0 $pid 2>/dev/null; then
                remaining_pids="$remaining_pids $pid"
            fi
        done
        
        if [ -n "$remaining_pids" ]; then
            echo "$remaining_pids" | tr ' ' '\n' | xargs kill -9 2>/dev/null || true
            sleep 0.3
        fi
    fi
    
    # 等待端口完全释放（缩短等待时间）
    sleep 0.5
    
    print_success "进程清理完成"
}

# 运行应用
run_app() {
    local force_clean=${1:-false}  # 是否强制清理
    local api_only=${2:-false}      # 是否仅启动 API 服务器
    
    print_info "启动应用..."
    print_info "=========================================="
    print_success "语音桌面助手"
    print_info "=========================================="
    echo ""
    
    # 检查单实例运行（在启动前检查）
    check_single_instance $force_clean
    
    # 设置退出时的清理
    trap cleanup_processes EXIT INT TERM
    
    # 默认端口
    local api_port=$API_PORT
    local api_host=$API_HOST
    
    # 检查端口是否被占用
    if check_port $api_port $api_host; then
        print_warning "端口 $api_port 已被占用，正在清理相关进程..."
        cleanup_processes $api_port
        
        # 再次检查端口是否已释放
        if check_port $api_port $api_host; then
            print_error "端口 $api_port 清理后仍被占用，启动失败"
            print_info "占用端口的进程信息："
            if command -v lsof >/dev/null 2>&1; then
                lsof -i :$api_port 2>/dev/null || print_info "  (无法获取进程信息)"
            else
                print_info "  (lsof 命令不可用)"
            fi
            print_info ""
            print_info "请手动关闭占用端口的进程，或使用其他端口："
            print_info "  python api_server.py --port <其他端口>"
            if command -v lsof >/dev/null 2>&1; then
                print_info "查找占用端口的进程: lsof -i :$api_port"
                print_info "或者手动终止进程: kill -9 \$(lsof -ti :$api_port)"
            fi
            return 1
        else
            print_success "端口清理完成，继续启动..."
        fi
    fi
    
    # 如果指定了 --api-only，仅启动 API 服务器
    if [ "$api_only" = true ]; then
        print_info "仅启动 API 服务器（不启动 Electron）..."
        print_info "提示：按 Ctrl+C 停止服务器"
        echo ""
        
        # 设置退出时的清理
        trap cleanup_processes EXIT INT TERM
        
        # 确保虚拟环境已激活
        if [ -f "$VENV_DIR/bin/activate" ]; then
            source "$VENV_DIR/bin/activate"
        fi
        
        python "$PROJECT_DIR/api_server.py" --port $api_port --host $api_host
        return 0
    fi
    
    # 检查是否可以启动 Electron
    if check_nodejs && install_electron_deps; then
        print_info "检测到 Electron 前端，将同时启动 API 服务器和前端..."
        print_info "提示：按 Ctrl+C 可以同时停止两个服务"
        echo ""
        
        # 后台启动 API 服务器
        print_info "启动 API 服务器（后台）..."
        
        # 尝试启动 API 服务器，如果失败则清理端口并重试
        local max_retries=2
        local retry_count=0
        local api_started=false
        
        # 检查服务器是否就绪的函数（优化版本 - 实时检查，非固定等待）
        check_api_ready() {
            local pid=$1
            local port=$2
            local host=$3
            
            # 首先检查进程是否还在运行
            if ! kill -0 $pid 2>/dev/null; then
                return 1  # 进程不存在
            fi
            
            # 等待服务器就绪（最多等待 60 次，每次 0.5 秒 = 30 秒）
            # API 服务器需要加载 ASR、LLM、Embedding 等模型，启动时间较长
            # 注意：Embedding 模型首次加载可能需要 20-30 秒（即使已下载，加载到内存也需要时间）
            # 注意：不是固定等待，而是每 0.5 秒检查一次，一旦就绪立即返回
            local max_attempts=60
            local attempt=0
            local start_time=$(date +%s)
            
            while [ $attempt -lt $max_attempts ]; do
                # 检查进程是否还在运行
                if ! kill -0 $pid 2>/dev/null; then
                    return 1  # 进程已退出
                fi
                
                # 使用 HTTP 健康检查（使用根路径，更可靠）
                if command -v curl >/dev/null 2>&1; then
                    local http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 1 --connect-timeout 1 "http://$host:$port/" 2>/dev/null || echo "000")
                    
                    # 检查是否成功响应
                    if [ "$http_code" = "200" ] || [ "$http_code" = "404" ] || [ "$http_code" = "307" ]; then
                        local elapsed=$(($(date +%s) - start_time))
                        echo ""  # 换行
                        print_info "服务器就绪（实际等待: ${elapsed} 秒）"
                        return 0  # 服务器就绪，立即返回
                    fi
                    
                    # 每 1 秒显示一次进度和已等待时间
                    if [ $((attempt % 2)) -eq 0 ]; then
                        local elapsed=$(($(date +%s) - start_time))
                        echo -ne "\r[INFO] 检查中... (已等待 ${elapsed} 秒) "
                    fi
                else
                    # 如果没有 curl，使用端口检查作为备用方案
                    if check_port $port $host; then
                        # 端口已绑定，再等待一下确保服务器完全启动
                        sleep 1
                        local elapsed=$(($(date +%s) - start_time))
                        echo ""  # 换行
                        print_info "服务器就绪（实际等待: ${elapsed} 秒）"
                        return 0
                    fi
                fi
                
                sleep 0.5
                attempt=$((attempt + 1))
            done
            
            echo ""  # 换行
            return 1  # 超时
        }
        
        while [ $retry_count -lt $max_retries ] && [ "$api_started" = false ]; do
            # 确保端口未被占用
            if check_port $api_port $api_host; then
                print_warning "端口 $api_port 仍被占用，清理相关进程..."
                cleanup_processes $api_port
                sleep 1
            fi
            
            # 启动 API 服务器（后台运行，输出重定向到日志文件）
            # 确保使用虚拟环境中的 Python
            if [ -f "$VENV_DIR/bin/activate" ]; then
                source "$VENV_DIR/bin/activate"
            fi
            
            # 创建日志目录（如果不存在）
            LOG_DIR="$PROJECT_DIR/logs"
            mkdir -p "$LOG_DIR"
            API_LOG_FILE="$LOG_DIR/api_server_$(date +%Y%m%d_%H%M%S).log"
            
            # 启动 API 服务器，输出到日志文件
            python "$PROJECT_DIR/api_server.py" --port $api_port --host $api_host > "$API_LOG_FILE" 2>&1 &
            API_PID=$!
            
            print_info "API 服务器日志文件: $API_LOG_FILE"
            
            # 给进程一点时间启动
            sleep 0.5
            
            # 检查进程是否还在运行（如果立即退出说明启动失败）
            if ! kill -0 $API_PID 2>/dev/null; then
                retry_count=$((retry_count + 1))
                print_warning "API 服务器进程启动后立即退出（尝试 $retry_count/$max_retries）"
                cleanup_processes $api_port
                sleep 1
                if [ $retry_count -lt $max_retries ]; then
                    print_info "重试启动 API 服务器..."
                fi
                continue
            fi
            
            # 等待并检查 API 服务器是否就绪
            print_info "等待 API 服务器就绪..."
            print_info "正在初始化服务："
            print_info "  - 语音识别服务 (ASR)"
            print_info "  - 大语言模型服务 (LLM)"
            print_info "  - 知识库服务 (Embedding 模型加载可能需要 20-30 秒)"
            print_info "  - 智能对话代理 (Agents)"
            print_info "（首次启动可能需要 20-30 秒，请稍候...）"
            if check_api_ready $API_PID $api_port $api_host; then
                echo ""  # 换行（清除进度点）
                api_started=true
                print_success "API 服务器启动成功（PID: $API_PID，端口: $api_port）"
                print_info "查看详细日志: tail -f $API_LOG_FILE"
            else
                echo ""  # 换行（清除进度点）
                retry_count=$((retry_count + 1))
                if kill -0 $API_PID 2>/dev/null; then
                    print_warning "API 服务器进程存在但未就绪（尝试 $retry_count/$max_retries）"
                    kill $API_PID 2>/dev/null || true
                    sleep 0.5
                else
                    print_warning "API 服务器启动失败（尝试 $retry_count/$max_retries）"
                fi
                
                # 清理可能残留的进程
                cleanup_processes $api_port
                sleep 1
                
                if [ $retry_count -lt $max_retries ]; then
                    print_info "重试启动 API 服务器..."
                fi
            fi
        done
        
        if [ "$api_started" = false ]; then
            print_error "API 服务器启动失败，已尝试 $max_retries 次"
            return 1
        fi
        
        # 启动 Electron 前端（前台，会阻塞）
        print_info "启动 Electron 前端..."
        cd "$PROJECT_DIR/electron-app"
        
        # 设置 Electron 退出时的清理
        trap "cleanup_processes; exit" INT TERM
        
        npm run dev
        
        # Electron 退出时，停止 API 服务器
        cleanup_processes
        cd "$PROJECT_DIR"
    else
        print_info "仅启动 API 服务器..."
        print_info "提示：要使用完整功能，请安装 Node.js 并在另一个终端运行："
        print_info "  cd electron-app && npm install && npm run dev"
        print_info "提示：按 Ctrl+C 停止服务器"
        echo ""
        
        # 设置退出时的清理
        trap cleanup_processes EXIT INT TERM
        
        python "$PROJECT_DIR/api_server.py" --port $api_port --host $api_host
    fi
}

# 清理函数（已移动到run_app中）
cleanup() {
    cleanup_processes
}

# 主函数
main() {
    local force_clean=${1:-false}  # 是否强制清理
    local api_only=${2:-false}      # 是否仅启动 API 服务器
    
    print_info "=========================================="
    print_info "语音桌面助手 - 快速启动"
    print_info "=========================================="
    echo ""
    
    # 切换到项目目录
    cd "$PROJECT_DIR"
    
    # 执行检查和部署步骤
    check_python
    check_system_deps
    setup_venv
    install_dependencies
    check_config
    check_permissions
    verify_installation
    check_nodejs  # 检查但不强制要求
    
    echo ""
    print_success "所有检查完成，准备启动应用..."
    echo ""
    
    # 设置退出时的清理
    trap cleanup EXIT
    
    # 运行应用
    run_app $force_clean $api_only
}

# 处理命令行参数
case "${1:-}" in
    --help|-h)
        echo "用法: $0 [选项]"
        echo ""
        echo "选项:"
        echo "  --help, -h      显示帮助信息"
        echo "  --clean         清理虚拟环境和缓存"
        echo "  --reinstall     重新安装依赖"
        echo "  --check-only    仅检查环境，不运行应用"
        echo "  --api-only      仅启动 API 服务器（不启动 Electron）"
        echo "  --force         强制清理旧实例并启动（不询问）"
        echo ""
        echo "单实例运行："
        echo "  程序默认只允许运行一个实例。如果检测到已有实例："
        echo "  - 正常运行：提示并询问是否停止旧实例"
        echo "  - 残余进程：自动清理并启动新实例"
        echo ""
        exit 0
        ;;
    --clean)
        print_info "清理虚拟环境..."
        rm -rf "$VENV_DIR"
        print_success "虚拟环境已清理"
        exit 0
        ;;
    --reinstall)
        print_info "重新安装依赖..."
        rm -f "$VENV_DIR/.installed"
        check_python
        setup_venv
        install_dependencies
        print_success "依赖重新安装完成"
        exit 0
        ;;
    --check-only)
        check_python
        check_system_deps
        if [ -d "$VENV_DIR" ]; then
            source "$VENV_DIR/bin/activate"
            verify_installation
        else
            print_warning "虚拟环境不存在，请先运行完整部署"
        fi
        exit 0
        ;;
    --api-only)
        # 仅启动 API 服务器
        cd "$PROJECT_DIR"
        check_python
        check_system_deps
        setup_venv
        install_dependencies
        check_config
        verify_installation
        check_single_instance false
        trap cleanup_processes EXIT INT TERM
        
        # 确保虚拟环境已激活
        if [ -f "$VENV_DIR/bin/activate" ]; then
            source "$VENV_DIR/bin/activate"
        fi
        
        # 创建日志目录
        LOG_DIR="$PROJECT_DIR/logs"
        mkdir -p "$LOG_DIR"
        API_LOG_FILE="$LOG_DIR/api_server_$(date +%Y%m%d_%H%M%S).log"
        
        print_info "启动 API 服务器..."
        python "$PROJECT_DIR/api_server.py" --port $API_PORT --host $API_HOST > "$API_LOG_FILE" 2>&1 &
        API_PID=$!
        
        print_info "API 服务器 PID: $API_PID"
        print_info "日志文件: $API_LOG_FILE"
        print_info "API 服务器运行中，按 Ctrl+C 停止"
        wait
        ;;
    --force)
        # 强制清理并启动
        main true false
        ;;
    "")
        # 无参数，执行主流程
        main false false
        ;;
    *)
        print_error "未知参数: $1"
        echo "使用 --help 查看帮助信息"
        exit 1
        ;;
esac
