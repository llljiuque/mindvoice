#!/usr/bin/env python3
"""
API服务器启动脚本
独立的后端服务，可以被任何前端框架调用
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.api.server import run_server, setup_logging

if __name__ == "__main__":
    import argparse
    import socket
    
    def is_port_in_use(port, host='127.0.0.1'):
        """检查端口是否被占用（排除TIME_WAIT状态）"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                # 使用 SO_REUSEADDR 来允许在 TIME_WAIT 状态下绑定
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((host, port))
                return False
            except OSError:
                # 如果设置了 SO_REUSEADDR 仍然无法绑定，说明端口真的被占用
                return True
    
    parser = argparse.ArgumentParser(description="启动语音桌面助手API服务器")
    parser.add_argument("--host", default="127.0.0.1", help="服务器地址（默认: 127.0.0.1）")
    parser.add_argument("--port", type=int, default=8765, help="服务器端口（默认: 8765）")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="日志级别（默认: INFO）")
    
    args = parser.parse_args()
    
    # 检查端口是否被占用
    if is_port_in_use(args.port, args.host):
        print(f"错误: 端口 {args.port} 已被占用")
        print(f"请先关闭占用该端口的进程，或使用其他端口:")
        print(f"  python api_server.py --port <其他端口>")
        print(f"\n查找占用端口的进程:")
        print(f"  lsof -i :{args.port}")
        sys.exit(1)
    
    # 设置日志级别
    os.environ['LOG_LEVEL'] = args.log_level
    
    # 运行服务器
    run_server(host=args.host, port=args.port)

