"""
SQLite 存储提供商实现示例
"""
import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from .base_storage import BaseStorageProvider


class SQLiteStorageProvider(BaseStorageProvider):
    """SQLite 存储提供商"""
    
    PROVIDER_NAME = "sqlite"
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化 SQLite 存储"""
        super().initialize(config)
        
        db_path = config.get('path', 'history.db')
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建表
        self._create_table()
        return True
    
    def _create_table(self):
        """创建数据表"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS records (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                metadata TEXT,
                app_type TEXT DEFAULT 'voice-note',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 检查是否需要迁移：为旧记录添加app_type字段
        cursor.execute("PRAGMA table_info(records)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'app_type' not in columns:
            cursor.execute('ALTER TABLE records ADD COLUMN app_type TEXT DEFAULT "voice-note"')
        
        conn.commit()
        conn.close()
    
    def _get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(str(self.db_path))
    
    def save_record(self, text: str, metadata: Dict[str, Any]) -> str:
        """保存记录"""
        import uuid
        record_id = str(uuid.uuid4())
        
        # 从metadata中提取app_type，默认为'voice-note'
        app_type = metadata.get('app_type', 'voice-note')
        
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO records (id, text, metadata, app_type)
            VALUES (?, ?, ?, ?)
        ''', (record_id, text, json.dumps(metadata, ensure_ascii=False), app_type))
        conn.commit()
        conn.close()
        
        return record_id
    
    def update_record(self, record_id: str, text: str, metadata: Dict[str, Any]) -> bool:
        """更新记录（用于增量保存）"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE records
            SET text = ?, metadata = ?
            WHERE id = ?
        ''', (text, json.dumps(metadata, ensure_ascii=False), record_id))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """获取记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, text, metadata, app_type, created_at
            FROM records
            WHERE id = ?
        ''', (record_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'text': row[1],
                'metadata': json.loads(row[2]) if row[2] else {},
                'app_type': row[3] or 'voice-note',
                'created_at': row[4]
            }
        return None
    
    def list_records(self, limit: int = 100, offset: int = 0, app_type: Optional[str] = None) -> list[Dict[str, Any]]:
        """列出记录
        
        Args:
            limit: 返回记录数量限制
            offset: 偏移量
            app_type: 应用类型筛选（可选）
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if app_type:
            cursor.execute('''
                SELECT id, text, metadata, app_type, created_at
                FROM records
                WHERE app_type = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (app_type, limit, offset))
        else:
            cursor.execute('''
                SELECT id, text, metadata, app_type, created_at
                FROM records
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (limit, offset))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'id': row[0],
                'text': row[1],
                'metadata': json.loads(row[2]) if row[2] else {},
                'app_type': row[3] or 'voice-note',
                'created_at': row[4]
            }
            for row in rows
        ]
    
    def delete_record(self, record_id: str) -> bool:
        """删除记录"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM records WHERE id = ?', (record_id,))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def count_records(self, app_type: Optional[str] = None) -> int:
        """获取记录总数
        
        Args:
            app_type: 应用类型筛选（可选）
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if app_type:
            cursor.execute('SELECT COUNT(*) FROM records WHERE app_type = ?', (app_type,))
        else:
            cursor.execute('SELECT COUNT(*) FROM records')
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    
    def delete_records(self, record_ids: list[str]) -> int:
        """批量删除记录
        
        Args:
            record_ids: 记录ID列表
            
        Returns:
            成功删除的记录数
        """
        if not record_ids:
            return 0
        
        conn = self._get_connection()
        cursor = conn.cursor()
        placeholders = ','.join(['?'] * len(record_ids))
        cursor.execute(f'DELETE FROM records WHERE id IN ({placeholders})', record_ids)
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted_count