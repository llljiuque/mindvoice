"""
存储提供商基类实现示例
"""
from typing import Dict, Any, Optional
from ...core.base import StorageProvider


class BaseStorageProvider(StorageProvider):
    """存储提供商基类，提供通用功能"""
    
    def __init__(self):
        self._config: Dict[str, Any] = {}
        self._initialized = False
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化存储提供商"""
        self._config = config
        self._initialized = True
        return True
    
    def save_record(self, text: str, metadata: Dict[str, Any]) -> str:
        """保存记录，子类必须实现"""
        raise NotImplementedError("Subclass must implement save_record method")
    
    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """获取记录，子类必须实现"""
        raise NotImplementedError("Subclass must implement get_record method")
    
    def list_records(self, limit: int = 100, offset: int = 0) -> list[Dict[str, Any]]:
        """列出记录，子类必须实现"""
        raise NotImplementedError("Subclass must implement list_records method")
    
    def delete_record(self, record_id: str) -> bool:
        """删除记录，子类必须实现"""
        raise NotImplementedError("Subclass must implement delete_record method")
