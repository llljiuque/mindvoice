#!/bin/bash
# MindVoice 停止脚本
# 用途：停止所有相关进程（API服务器、Electron、Vite等）

set -e

echo "========================================="
echo "正在停止 MindVoice..."
echo "========================================="
echo ""

STOPPED=0

# 1. 停止 API 服务器进程
API_PIDS=$(pgrep -f "api_server.py" 2>/dev/null || true)
if [ -n "$API_PIDS" ]; then
    echo "🛑 停止 API 服务器进程..."
    echo "$API_PIDS" | xargs kill -TERM 2>/dev/null || true
    sleep 1
    # 如果还在运行，强制终止
    API_PIDS=$(pgrep -f "api_server.py" 2>/dev/null || true)
    if [ -n "$API_PIDS" ]; then
        echo "$API_PIDS" | xargs kill -9 2>/dev/null || true
    fi
    echo "✅ API 服务器已停止"
    STOPPED=1
else
    echo "ℹ️  API 服务器未运行"
fi

# 2. 停止 Electron 进程
ELECTRON_PIDS=$(pgrep -f "Electron.*MindVoice" 2>/dev/null || true)
if [ -z "$ELECTRON_PIDS" ]; then
    # 降级：查找所有 electron 进程
    ELECTRON_PIDS=$(pgrep -f "electron" 2>/dev/null | grep -v grep || true)
fi

if [ -n "$ELECTRON_PIDS" ]; then
    echo "🛑 停止 Electron 进程..."
    echo "$ELECTRON_PIDS" | xargs kill -TERM 2>/dev/null || true
    sleep 1
    # 如果还在运行，强制终止
    ELECTRON_PIDS=$(pgrep -f "electron" 2>/dev/null || true)
    if [ -n "$ELECTRON_PIDS" ]; then
        echo "$ELECTRON_PIDS" | xargs kill -9 2>/dev/null || true
    fi
    echo "✅ Electron 已停止"
    STOPPED=1
else
    echo "ℹ️  Electron 未运行"
fi

# 3. 停止 Vite 开发服务器
VITE_PIDS=$(pgrep -f "vite" 2>/dev/null | grep -v grep || true)
if [ -n "$VITE_PIDS" ]; then
    echo "🛑 停止 Vite 开发服务器..."
    echo "$VITE_PIDS" | xargs kill -TERM 2>/dev/null || true
    sleep 1
    # 如果还在运行，强制终止
    VITE_PIDS=$(pgrep -f "vite" 2>/dev/null || true)
    if [ -n "$VITE_PIDS" ]; then
        echo "$VITE_PIDS" | xargs kill -9 2>/dev/null || true
    fi
    echo "✅ Vite 已停止"
    STOPPED=1
else
    echo "ℹ️  Vite 未运行"
fi

# 4. 停止 uvicorn 进程（如果直接运行）
UVICORN_PIDS=$(pgrep -f "uvicorn.*8765" 2>/dev/null || true)
if [ -n "$UVICORN_PIDS" ]; then
    echo "🛑 停止 uvicorn 进程..."
    echo "$UVICORN_PIDS" | xargs kill -TERM 2>/dev/null || true
    sleep 1
    # 如果还在运行，强制终止
    UVICORN_PIDS=$(pgrep -f "uvicorn.*8765" 2>/dev/null || true)
    if [ -n "$UVICORN_PIDS" ]; then
        echo "$UVICORN_PIDS" | xargs kill -9 2>/dev/null || true
    fi
    echo "✅ uvicorn 已停止"
    STOPPED=1
else
    echo "ℹ️  uvicorn 未运行"
fi

echo ""
echo "========================================="
if [ $STOPPED -eq 1 ]; then
    echo "✅ MindVoice 已完全停止"
else
    echo "ℹ️  没有发现运行中的 MindVoice 进程"
fi
echo "========================================="
echo ""

