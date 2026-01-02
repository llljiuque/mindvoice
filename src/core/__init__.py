"""
核心模块 - 定义抽象接口和基础类
"""
from .base import RecordingState, AudioRecorder, ASRProvider, LLMProvider
from .config import Config
from .plugin_manager import PluginManager
from .error_codes import SystemError, SystemErrorInfo, ErrorCategory, get_error_by_code
from .logger import get_system_logger, get_logger, SystemLogger, LogLevel

__all__ = [
    'RecordingState',
    'AudioRecorder',
    'ASRProvider',
    'LLMProvider',
    'Config',
    'PluginManager',
    'SystemError',
    'SystemErrorInfo',
    'ErrorCategory',
    'get_error_by_code',
    'get_system_logger',
    'get_logger',
    'SystemLogger',
    'LogLevel',
]
