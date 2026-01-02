"""
统一日志管理系统
提供结构化日志记录、错误追踪和日志聚合功能
"""
import logging
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum

from .error_codes import SystemErrorInfo, ErrorCategory


class LogLevel(str, Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class SystemLogger:
    """系统日志管理器"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化日志系统"""
        if not self._initialized:
            self.logger = logging.getLogger("MindVoice")
            self.log_dir = Path("logs")
            self.log_dir.mkdir(exist_ok=True)
            self._setup_handlers()
            SystemLogger._initialized = True
    
    def _setup_handlers(self):
        """设置日志处理器"""
        # 清除现有处理器
        self.logger.handlers.clear()
        
        # 设置日志级别
        self.logger.setLevel(logging.DEBUG)
        
        # 控制台处理器 - 带颜色和格式
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = ColoredFormatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # 文件处理器 - 所有日志
        log_file = self.log_dir / f"mindvoice_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # 错误日志单独文件
        error_log_file = self.log_dir / f"errors_{datetime.now().strftime('%Y%m%d')}.log"
        error_handler = logging.FileHandler(error_log_file, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        self.logger.addHandler(error_handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """获取子日志记录器"""
        return logging.getLogger(f"MindVoice.{name}")
    
    def log_system_event(
        self,
        level: LogLevel,
        component: str,
        event: str,
        details: Optional[Dict[str, Any]] = None,
        error_info: Optional[SystemErrorInfo] = None
    ):
        """
        记录系统事件
        
        Args:
            level: 日志级别
            component: 组件名称 (如 "ASR", "LLM", "Network")
            event: 事件描述
            details: 事件详情
            error_info: 错误信息对象
        """
        logger = self.get_logger(component)
        
        # 构建日志消息
        message = event
        
        # 添加详情
        if details:
            detail_str = " | ".join([f"{k}={v}" for k, v in details.items()])
            message += f" [{detail_str}]"
        
        # 添加错误信息
        if error_info:
            message += f" | ErrorCode={error_info.code}"
            if error_info.technical_info:
                message += f" | Tech={error_info.technical_info}"
        
        # 记录日志
        log_method = getattr(logger, level.lower())
        log_method(message)
        
        # 如果是错误，记录完整的错误对象到单独的JSON文件
        if error_info and level in [LogLevel.ERROR, LogLevel.CRITICAL]:
            self._log_error_detail(component, error_info, details)
    
    def _log_error_detail(
        self,
        component: str,
        error_info: SystemErrorInfo,
        details: Optional[Dict[str, Any]] = None
    ):
        """记录详细错误信息到JSON文件"""
        error_log_file = self.log_dir / f"error_details_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        error_record = {
            "timestamp": datetime.now().isoformat(),
            "component": component,
            "error": error_info.to_dict(),
            "details": details or {}
        }
        
        try:
            with open(error_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(error_record, ensure_ascii=False) + '\n')
        except Exception as e:
            self.logger.error(f"无法写入错误详情日志: {e}")
    
    def log_network_event(self, event: str, endpoint: str, status: str, **kwargs):
        """记录网络事件"""
        details = {"endpoint": endpoint, "status": status, **kwargs}
        self.log_system_event(LogLevel.INFO, "Network", event, details)
    
    def log_audio_event(self, event: str, device: Optional[str] = None, **kwargs):
        """记录音频事件"""
        details = {"device": device or "default", **kwargs}
        self.log_system_event(LogLevel.INFO, "AudioDevice", event, details)
    
    def log_asr_event(self, event: str, **kwargs):
        """记录ASR事件"""
        self.log_system_event(LogLevel.INFO, "ASR", event, kwargs)
    
    def log_llm_event(self, event: str, **kwargs):
        """记录LLM事件"""
        self.log_system_event(LogLevel.INFO, "LLM", event, kwargs)
    
    def log_storage_event(self, event: str, **kwargs):
        """记录存储事件"""
        self.log_system_event(LogLevel.INFO, "Storage", event, kwargs)
    
    def log_error(
        self,
        component: str,
        error_info: SystemErrorInfo,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        记录错误
        
        Args:
            component: 组件名称
            error_info: 错误信息对象
            details: 额外详情
        """
        self.log_system_event(
            LogLevel.ERROR,
            component,
            f"Error: {error_info.message}",
            details,
            error_info
        )
    
    def log_critical(
        self,
        component: str,
        error_info: SystemErrorInfo,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        记录严重错误
        
        Args:
            component: 组件名称
            error_info: 错误信息对象
            details: 额外详情
        """
        self.log_system_event(
            LogLevel.CRITICAL,
            component,
            f"CRITICAL: {error_info.message}",
            details,
            error_info
        )


class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器（用于控制台）"""
    
    # ANSI颜色代码
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 品红
    }
    RESET = '\033[0m'
    
    def format(self, record):
        """格式化日志记录"""
        # 保存原始levelname
        original_levelname = record.levelname
        
        # 添加颜色
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
        
        # 格式化
        result = super().format(record)
        
        # 恢复原始levelname
        record.levelname = original_levelname
        
        return result


# 全局日志实例
_system_logger = None


def get_system_logger() -> SystemLogger:
    """获取全局系统日志实例"""
    global _system_logger
    if _system_logger is None:
        _system_logger = SystemLogger()
    return _system_logger


def get_logger(name: str) -> logging.Logger:
    """
    获取日志记录器
    
    Args:
        name: 组件名称
        
    Returns:
        日志记录器实例
    """
    return get_system_logger().get_logger(name)

