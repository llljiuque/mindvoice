#!/bin/bash
# 停止语音桌面助手的所有进程

echo "正在停止语音桌面助手..."

# 查找并终止 API 服务器进程
API_PIDS=$(pgrep -f "api_server.py" 2>/dev/null || true)
if [ -n "$API_PIDS" ]; then
    echo "终止 API 服务器进程..."
    echo "$API_PIDS" | xargs kill -TERM 2>/dev/null || true
    sleep 1
    echo "$API_PIDS" | xargs kill -9 2>/dev/null || true
fi

# 查找并终止 Electron 进程
ELECTRON_PIDS=$(pgrep -f "electron" | grep -v grep 2>/dev/null || true)
if [ -n "$ELECTRON_PIDS" ]; then
    echo "终止 Electron 进程..."
    echo "$ELECTRON_PIDS" | xargs kill -TERM 2>/dev/null || true
    sleep 1
    echo "$ELECTRON_PIDS" | xargs kill -9 2>/dev/null || true
fi

# 查找并终止 Vite 进程
VITE_PIDS=$(pgrep -f "vite" | grep -v grep 2>/dev/null || true)
if [ -n "$VITE_PIDS" ]; then
    echo "终止 Vite 进程..."
    echo "$VITE_PIDS" | xargs kill -TERM 2>/dev/null || true
    sleep 1
    echo "$VITE_PIDS" | xargs kill -9 2>/dev/null || true
fi

# 查找并终止 uvicorn 进程（如果直接运行）
UVICORN_PIDS=$(pgrep -f "uvicorn" | grep -v grep 2>/dev/null || true)
if [ -n "$UVICORN_PIDS" ]; then
    echo "终止 uvicorn 进程..."
    echo "$UVICORN_PIDS" | xargs kill -TERM 2>/dev/null || true
    sleep 1
    echo "$UVICORN_PIDS" | xargs kill -9 2>/dev/null || true
fi

echo "完成！"

