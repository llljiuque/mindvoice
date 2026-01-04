#!/bin/bash

# =============================================================
# 优化的启动脚本 - 快速启动语音桌面助手
# 优化点：减少检查步骤、快速端口检测、改进错误处理
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

# 快速检查命令是否存在
check_command() {
    command -v "$1" >/dev/null 2>&1
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

# 快速清理进程
cleanup_fast() {
    local port=${1:-$API_PORT}
    local quiet=${2:-false}
    
    if [ "$quiet" = false ]; then
        print_info "正在清理进程..."
    fi
    
    # 一次性收集所有 PID
    local pids=""
    
    # 查找占用端口的进程
    if command -v lsof >/dev/null 2>&1; then
        pids=$(lsof -ti :$port 2>/dev/null || true)
    fi
    
    # 查找相关进程
    pids="$pids $(pgrep -f "api_server.py" 2>/dev/null || true)"
    pids="$pids $(pgrep -f "uvicorn.*8765" 2>/dev/null || true)"
    
    # 查找 Electron 进程（排除当前脚本进程）
    local electron_pids=$(pgrep -f "electron" 2>/dev/null | grep -v "^$$$" || true)
    if [ -n "$electron_pids" ]; then
        pids="$pids $electron_pids"
    fi
    
    # 查找 Vite 进程（排除当前脚本进程）
    local vite_pids=$(pgrep -f "vite" 2>/dev/null | grep -v "^$$$" || true)
    if [ -n "$vite_pids" ]; then
        pids="$pids $vite_pids"
    fi
    
    # 去重并终止
    if [ -n "$pids" ]; then
        # 去重
        pids=$(echo "$pids" | tr ' ' '\n' | sort -u | tr '\n' ' ')
        
        # 先尝试优雅终止
        echo "$pids" | xargs kill -TERM 2>/dev/null || true
        sleep 0.5
        
        # 检查哪些进程还在运行，强制终止
        local remaining_pids=""
        for pid in $pids; do
            if kill -0 $pid 2>/dev/null; then
                remaining_pids="$remaining_pids $pid "
            fi
        done
        
        if [ -n "$remaining_pids" ]; then
            echo "$remaining_pids" | xargs kill -9 2>/dev/null || true
            sleep 0.3
        fi
    fi
    
    # 等待端口完全释放
    sleep 0.3
    
    if [ "$quiet" = false ]; then
        print_success "进程清理完成"
    fi
}

# 快速检查 API 就绪（优化版本）
check_api_ready_fast() {
    local pid=$1
    local port=$2
    local host=$3
    local max_wait=${4:-20}  # 默认最多等待 20 秒
    
    local start_time=$(date +%s)
    local attempt=0
    local max_attempts=$((max_wait * 2))  # 每 0.5 秒检查一次
    
    while [ $attempt -lt $max_attempts ]; do
        # 检查进程是否还在运行
        if ! kill -0 $pid 2>/dev/null; then
            return 1  # 进程已退出
        fi
        
        # 使用 curl 快速检查（超时 0.5 秒）
        if command -v curl >/dev/null 2>&1; then
            local http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 0.5 --connect-timeout 0.5 "http://$host:$port/" 2>/dev/null || echo "000")
            
            if [ "$http_code" = "200" ] || [ "$http_code" = "404" ] || [ "$http_code" = "307" ]; then
                local elapsed=$(($(date +%s) - start_time))
                print_success "API 服务器就绪（等待 ${elapsed} 秒）"
                return 0
            fi
        else
            # 备用方案：检查端口是否已绑定
            if check_port_fast $port $host; then
                sleep 0.5
                local elapsed=$(($(date +%s) - start_time))
                print_success "API 服务器就绪（等待 ${elapsed} 秒）"
                return 0
            fi
        fi
        
        # 每 2 秒显示一次进度
        if [ $((attempt % 4)) -eq 0 ]; then
            local elapsed=$(($(date +%s) - start_time))
            echo -ne "\r[INFO] 等待 API 服务器启动... (${elapsed}秒) "
        fi
        
        sleep 0.5
        attempt=$((attempt + 1))
    done
    
    echo ""  # 换行
    return 1  # 超时
}

# 最小化环境检查（只检查必要的）
check_env_minimal() {
    # 检查 Python
    if ! check_command "$PYTHON_CMD"; then
        print_error "未找到 $PYTHON_CMD，请先安装 Python 3"
        print_info "macOS: brew install python3"
        exit 1
    fi
    
    # 检查虚拟环境
    if [ ! -d "$VENV_DIR" ]; then
        print_error "虚拟环境不存在"
        print_info "请先运行完整安装: ./quick_start.sh"
        exit 1
    fi
    
    # 激活虚拟环境
    if [ -f "$VENV_DIR/bin/activate" ]; then
        source "$VENV_DIR/bin/activate" 2>/dev/null || {
            print_error "无法激活虚拟环境"
            print_info "请重新创建虚拟环境: ./quick_start.sh --clean && ./quick_start.sh"
            exit 1
        }
    else
        print_error "虚拟环境文件损坏: $VENV_DIR/bin/activate"
        print_info "请重新创建虚拟环境: ./quick_start.sh --clean && ./quick_start.sh"
        exit 1
    fi
    
    # 快速检查关键模块（不阻塞）
    if ! python -c "import fastapi, uvicorn" 2>/dev/null; then
        print_error "关键模块缺失"
        print_info "请安装依赖: ./quick_start.sh --reinstall"
        exit 1
    fi
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
            cleanup_fast $API_PORT
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
                    cleanup_fast $API_PORT
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
            cleanup_fast $API_PORT
            sleep 1
            return 0
        fi
        
        print_info "正在自动清理残余进程..."
        cleanup_fast $API_PORT
        sleep 1
    fi
    
    return 0
}

# 启动 API 服务器
start_api_server() {
    print_info "启动 API 服务器..."
    
    # 检查并清理端口（双重保险）
    if check_port_fast $API_PORT $API_HOST; then
        print_warning "端口 $API_PORT 仍被占用，再次清理..."
        cleanup_fast $API_PORT true
        sleep 0.5
        
        # 再次检查
        if check_port_fast $API_PORT $API_HOST; then
            print_error "端口 $API_PORT 清理后仍被占用"
            print_info "请手动关闭占用端口的进程:"
            if command -v lsof >/dev/null 2>&1; then
                print_info "  lsof -i :$API_PORT"
                print_info "  kill -9 \$(lsof -ti :$API_PORT)"
            else
                print_info "  netstat -an | grep :$API_PORT"
            fi
            return 1
        fi
    fi
    
    # 确保虚拟环境已激活
    if [ -f "$VENV_DIR/bin/activate" ]; then
        source "$VENV_DIR/bin/activate"
    else
        print_error "虚拟环境不存在: $VENV_DIR"
        print_info "请先运行: ./quick_start.sh"
        return 1
    fi
    
    # 检查 API 服务器脚本是否存在
    if [ ! -f "$PROJECT_DIR/api_server.py" ]; then
        print_error "API 服务器脚本不存在: $PROJECT_DIR/api_server.py"
        return 1
    fi
    
    # 创建日志目录
    LOG_DIR="$PROJECT_DIR/logs"
    mkdir -p "$LOG_DIR"
    API_LOG_FILE="$LOG_DIR/api_server_$(date +%Y%m%d_%H%M%S).log"
    
    # 启动 API 服务器（最多重试 2 次）
    local max_retries=2
    local retry=0
    local api_started=false
    
    while [ $retry -lt $max_retries ] && [ "$api_started" = false ]; do
        if [ $retry -gt 0 ]; then
            print_info "重试启动 API 服务器 (尝试 $retry/$max_retries)..."
            cleanup_fast $API_PORT
            sleep 1
        fi
        
        # 启动 API 服务器
        python "$PROJECT_DIR/api_server.py" --port $API_PORT --host $API_HOST > "$API_LOG_FILE" 2>&1 &
        API_PID=$!
        
        print_info "API 服务器 PID: $API_PID"
        print_info "日志文件: $API_LOG_FILE"
        
        # 等待进程启动
        sleep 0.5
        
        # 检查进程是否还在运行
        if ! kill -0 $API_PID 2>/dev/null; then
            retry=$((retry + 1))
            if [ $retry -lt $max_retries ]; then
                print_warning "API 服务器启动失败，查看日志:"
                tail -10 "$API_LOG_FILE" 2>/dev/null | sed 's/^/  /'
                continue
            else
                print_error "API 服务器启动失败（已重试 $max_retries 次）"
                print_info "查看完整日志: tail -50 $API_LOG_FILE"
                return 1
            fi
        fi
        
        # 等待 API 就绪
        print_info "等待 API 服务器就绪..."
        if check_api_ready_fast $API_PID $API_PORT $API_HOST 25; then
            api_started=true
        else
            retry=$((retry + 1))
            if kill -0 $API_PID 2>/dev/null; then
                kill $API_PID 2>/dev/null || true
            fi
            if [ $retry -lt $max_retries ]; then
                print_warning "API 服务器启动超时，查看日志:"
                tail -15 "$API_LOG_FILE" 2>/dev/null | sed 's/^/  /'
            else
                print_error "API 服务器启动超时（已重试 $max_retries 次）"
                print_info "查看完整日志: tail -50 $API_LOG_FILE"
                print_info "常见问题："
                print_info "  1. 检查配置文件 config.yml 是否正确"
                print_info "  2. 检查依赖是否完整安装: ./quick_start.sh --reinstall"
                print_info "  3. 检查端口是否被其他程序占用"
                return 1
            fi
        fi
    done
    
    if [ "$api_started" = true ]; then
        return 0
    else
        return 1
    fi
}

# 启动 Electron 前端
start_electron() {
    ELECTRON_DIR="$PROJECT_DIR/electron-app"
    
    if [ ! -d "$ELECTRON_DIR" ]; then
        print_warning "Electron 前端目录不存在"
        return 1
    fi
    
    # 检查 Node.js
    if ! check_command "node"; then
        print_warning "未找到 Node.js，无法启动 Electron 前端"
        return 1
    fi
    
    # 检查依赖（快速检查）
    if [ ! -d "$ELECTRON_DIR/node_modules" ]; then
        print_warning "Electron 依赖未安装，请先运行: cd electron-app && npm install"
        return 1
    fi
    
    # 检查构建（快速检查）
    if [ ! -f "$ELECTRON_DIR/dist-electron/main.js" ]; then
        print_info "构建 Electron 主进程..."
        cd "$ELECTRON_DIR"
        if ! npm run build:electron >/dev/null 2>&1; then
            print_error "Electron 构建失败"
            cd "$PROJECT_DIR"
            return 1
        fi
        cd "$PROJECT_DIR"
    fi
    
    # 启动 Electron
    print_info "启动 Electron 前端..."
    cd "$ELECTRON_DIR"
    npm run dev
    cd "$PROJECT_DIR"
}

# 清理函数
cleanup() {
    print_info "正在清理..."
    cleanup_fast $API_PORT
    print_success "清理完成"
}

# 主函数
main() {
    local force_clean=${1:-false}
    
    print_info "=========================================="
    print_info "语音桌面助手 - 快速启动"
    print_info "=========================================="
    echo ""
    
    # 切换到项目目录
    cd "$PROJECT_DIR"
    
    # 最小化环境检查
    check_env_minimal
    
    # 检查单实例运行（在启动前）
    check_single_instance $force_clean
    
    # 设置退出时的清理
    trap cleanup EXIT INT TERM
    
    # 启动 API 服务器
    if ! start_api_server; then
        print_error "启动失败"
        exit 1
    fi
    
    echo ""
    print_success "API 服务器运行中 (http://$API_HOST:$API_PORT)"
    echo ""
    
    # 尝试启动 Electron（可选）
    if check_command "node" && [ -d "$PROJECT_DIR/electron-app" ]; then
        print_info "提示: 按 Ctrl+C 停止服务"
        echo ""
        start_electron
    else
        print_info "提示: 按 Ctrl+C 停止服务器"
        print_info "要启动 Electron 前端，请安装 Node.js 并在另一个终端运行:"
        print_info "  cd electron-app && npm run dev"
        echo ""
        # 保持运行
        wait
    fi
}

# 处理命令行参数
case "${1:-}" in
    --help|-h)
        echo "用法: $0 [选项]"
        echo ""
        echo "选项:"
        echo "  --help, -h      显示帮助信息"
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
    --api-only)
        # 仅启动 API 服务器
        cd "$PROJECT_DIR"
        check_env_minimal
        check_single_instance false
        trap cleanup EXIT INT TERM
        if start_api_server; then
            print_info "API 服务器运行中，按 Ctrl+C 停止"
            wait
        fi
        ;;
    --force)
        # 强制清理并启动
        main true
        ;;
    "")
        # 无参数，执行主流程
        main false
        ;;
    *)
        print_error "未知参数: $1"
        echo "使用 --help 查看帮助信息"
        exit 1
        ;;
esac

