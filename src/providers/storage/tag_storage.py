"""
标签管理存储服务

功能：
- 标签的创建、更新、删除
- 记录与标签的关联管理
- 按标签查询记录
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from src.core.logger import get_logger

logger = get_logger("TagStorage")


class TagStorageService:
    """标签存储服务"""
    
    def __init__(self, db_path: str):
        """初始化标签存储服务
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = Path(db_path).expanduser()
        logger.info(f"[标签存储] 初始化: {self.db_path}")
    
    def create_tag(self, user_id: str, tag_name: str, 
                  color: Optional[str] = None, 
                  icon: Optional[str] = None) -> int:
        """创建标签
        
        Args:
            user_id: 用户ID
            tag_name: 标签名称
            color: 颜色（可选，如 #FF5733）
            icon: 图标（可选，如 emoji 或图标名）
        
        Returns:
            tag_id: 标签ID
        """
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            # 获取当前最大排序号
            cursor.execute('SELECT MAX(sort_order) FROM tags WHERE user_id = ?', (user_id,))
            max_order = cursor.fetchone()[0] or 0
            
            cursor.execute('''
                INSERT INTO tags (user_id, tag_name, color, icon, sort_order, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, tag_name, color, icon, max_order + 1, now))
            
            tag_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"[标签存储] 创建标签成功: user_id={user_id}, tag_id={tag_id}, tag_name={tag_name}")
            return tag_id
            
        except sqlite3.IntegrityError:
            conn.rollback()
            logger.warning(f"[标签存储] 标签已存在: user_id={user_id}, tag_name={tag_name}")
            # 返回已存在的标签ID
            cursor.execute('SELECT tag_id FROM tags WHERE user_id = ? AND tag_name = ?', (user_id, tag_name))
            return cursor.fetchone()[0]
        except Exception as e:
            conn.rollback()
            logger.error(f"[标签存储] 创建标签失败: {e}", exc_info=True)
            raise
        finally:
            conn.close()
    
    def update_tag(self, tag_id: int, tag_name: Optional[str] = None,
                  color: Optional[str] = None, icon: Optional[str] = None) -> bool:
        """更新标签
        
        Args:
            tag_id: 标签ID
            tag_name: 新标签名称（可选）
            color: 新颜色（可选）
            icon: 新图标（可选）
        
        Returns:
            是否更新成功
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            update_fields = []
            params = []
            
            if tag_name is not None:
                update_fields.append("tag_name = ?")
                params.append(tag_name)
            
            if color is not None:
                update_fields.append("color = ?")
                params.append(color)
            
            if icon is not None:
                update_fields.append("icon = ?")
                params.append(icon)
            
            if not update_fields:
                return True
            
            params.append(tag_id)
            query = f"UPDATE tags SET {', '.join(update_fields)} WHERE tag_id = ?"
            cursor.execute(query, params)
            
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"[标签存储] 更新标签成功: tag_id={tag_id}")
                return True
            else:
                logger.warning(f"[标签存储] 标签不存在: tag_id={tag_id}")
                return False
            
        except Exception as e:
            conn.rollback()
            logger.error(f"[标签存储] 更新标签失败: {e}", exc_info=True)
            raise
        finally:
            conn.close()
    
    def delete_tag(self, tag_id: int) -> bool:
        """删除标签（级联删除关联）
        
        Args:
            tag_id: 标签ID
        
        Returns:
            是否删除成功
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM tags WHERE tag_id = ?', (tag_id,))
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"[标签存储] 删除标签成功: tag_id={tag_id}")
                return True
            else:
                logger.warning(f"[标签存储] 标签不存在: tag_id={tag_id}")
                return False
            
        except Exception as e:
            conn.rollback()
            logger.error(f"[标签存储] 删除标签失败: {e}", exc_info=True)
            raise
        finally:
            conn.close()
    
    def get_user_tags(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的所有标签
        
        Args:
            user_id: 用户ID
        
        Returns:
            标签列表
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT tag_id, tag_name, color, icon, sort_order, created_at
                FROM tags
                WHERE user_id = ?
                ORDER BY sort_order ASC
            ''', (user_id,))
            
            tags = []
            for row in cursor.fetchall():
                tags.append({
                    'tag_id': row[0],
                    'tag_name': row[1],
                    'color': row[2],
                    'icon': row[3],
                    'sort_order': row[4],
                    'created_at': row[5]
                })
            
            return tags
            
        except Exception as e:
            logger.error(f"[标签存储] 获取用户标签失败: {e}", exc_info=True)
            raise
        finally:
            conn.close()
    
    def add_tag_to_record(self, record_id: str, tag_id: int) -> bool:
        """给记录添加标签
        
        Args:
            record_id: 记录ID
            tag_id: 标签ID
        
        Returns:
            是否添加成功
        """
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO record_tags (record_id, tag_id, created_at)
                VALUES (?, ?, ?)
            ''', (record_id, tag_id, now))
            
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"[标签存储] 添加标签成功: record_id={record_id}, tag_id={tag_id}")
                return True
            else:
                logger.warning(f"[标签存储] 标签已存在或记录不存在: record_id={record_id}, tag_id={tag_id}")
                return False
            
        except Exception as e:
            conn.rollback()
            logger.error(f"[标签存储] 添加标签失败: {e}", exc_info=True)
            raise
        finally:
            conn.close()
    
    def remove_tag_from_record(self, record_id: str, tag_id: int) -> bool:
        """从记录移除标签
        
        Args:
            record_id: 记录ID
            tag_id: 标签ID
        
        Returns:
            是否移除成功
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                DELETE FROM record_tags
                WHERE record_id = ? AND tag_id = ?
            ''', (record_id, tag_id))
            
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"[标签存储] 移除标签成功: record_id={record_id}, tag_id={tag_id}")
                return True
            else:
                logger.warning(f"[标签存储] 标签关联不存在: record_id={record_id}, tag_id={tag_id}")
                return False
            
        except Exception as e:
            conn.rollback()
            logger.error(f"[标签存储] 移除标签失败: {e}", exc_info=True)
            raise
        finally:
            conn.close()
    
    def get_record_tags(self, record_id: str) -> List[Dict[str, Any]]:
        """获取记录的所有标签
        
        Args:
            record_id: 记录ID
        
        Returns:
            标签列表
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT t.tag_id, t.tag_name, t.color, t.icon
                FROM tags t
                INNER JOIN record_tags rt ON t.tag_id = rt.tag_id
                WHERE rt.record_id = ?
                ORDER BY t.sort_order ASC
            ''', (record_id,))
            
            tags = []
            for row in cursor.fetchall():
                tags.append({
                    'tag_id': row[0],
                    'tag_name': row[1],
                    'color': row[2],
                    'icon': row[3]
                })
            
            return tags
            
        except Exception as e:
            logger.error(f"[标签存储] 获取记录标签失败: {e}", exc_info=True)
            raise
        finally:
            conn.close()
    
    def get_records_by_tag(self, tag_id: int, limit: int = 100, offset: int = 0) -> List[str]:
        """按标签查询记录ID列表
        
        Args:
            tag_id: 标签ID
            limit: 返回数量限制
            offset: 偏移量（用于分页）
        
        Returns:
            记录ID列表
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT record_id
                FROM record_tags
                WHERE tag_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (tag_id, limit, offset))
            
            return [row[0] for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"[标签存储] 按标签查询记录失败: {e}", exc_info=True)
            raise
        finally:
            conn.close()
    
    def update_tag_order(self, tag_orders: List[Dict[str, int]]) -> bool:
        """批量更新标签排序
        
        Args:
            tag_orders: 标签ID和排序号列表，如 [{'tag_id': 1, 'sort_order': 0}, ...]
        
        Returns:
            是否更新成功
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            for item in tag_orders:
                cursor.execute('''
                    UPDATE tags
                    SET sort_order = ?
                    WHERE tag_id = ?
                ''', (item['sort_order'], item['tag_id']))
            
            conn.commit()
            logger.info(f"[标签存储] 更新标签排序成功: count={len(tag_orders)}")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"[标签存储] 更新标签排序失败: {e}", exc_info=True)
            raise
        finally:
            conn.close()

