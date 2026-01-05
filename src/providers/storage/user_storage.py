"""
用户信息存储服务

功能：
- 用户资料管理（昵称、邮箱、简介、头像）
- 用户与设备绑定管理（一个user_id可绑定多个device_id）
- 支持通过device_id查询用户信息
"""

import sqlite3
import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from src.core.logger import get_logger

logger = get_logger("UserStorage")


class UserStorageService:
    """用户存储服务"""
    
    def __init__(self, db_path: str):
        """初始化用户存储服务
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        logger.info(f"[用户存储] 初始化完成: {self.db_path}")
    
    def _init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            # 创建用户表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    nickname TEXT,
                    email TEXT,
                    bio TEXT,
                    avatar_url TEXT,
                    login_count INTEGER DEFAULT 0,
                    last_login_at TIMESTAMP,
                    is_deleted INTEGER DEFAULT 0,
                    deleted_at TIMESTAMP,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            ''')
            
            # 创建用户设备绑定表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    device_id TEXT NOT NULL UNIQUE,
                    device_name TEXT,
                    bound_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            ''')
            
            # 创建索引
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_devices_user_id 
                ON user_devices(user_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_devices_device_id 
                ON user_devices(device_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_users_email 
                ON users(email)
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_not_deleted ON users(is_deleted) WHERE is_deleted = 0')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_login ON users(last_login_at DESC)')
            
            conn.commit()
            logger.info("[用户存储] 数据库表初始化完成 (v1.2.0)")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"[用户存储] 数据库初始化失败: {e}", exc_info=True)
            raise
        finally:
            conn.close()
    
    def create_user(self, nickname: Optional[str] = None, 
                   email: Optional[str] = None,
                   bio: Optional[str] = None,
                   avatar_url: Optional[str] = None) -> str:
        """创建新用户
        
        Args:
            nickname: 昵称（可选）
            email: 邮箱（可选）
            bio: 个人简介（可选）
            avatar_url: 头像URL（可选）
        
        Returns:
            user_id: 新创建的用户ID
        """
        user_id = str(uuid.uuid4())
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO users (user_id, nickname, email, bio, avatar_url, login_count, last_login_at, is_deleted, deleted_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, nickname, email, bio, avatar_url, 0, None, 0, None, now, now))
            
            conn.commit()
            logger.info(f"[用户存储] 创建用户成功: user_id={user_id}")
            return user_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"[用户存储] 创建用户失败: {e}", exc_info=True)
            raise
        finally:
            conn.close()
    
    def update_user(self, user_id: str,
                   nickname: Optional[str] = None,
                   email: Optional[str] = None,
                   bio: Optional[str] = None,
                   avatar_url: Optional[str] = None) -> bool:
        """更新用户信息
        
        Args:
            user_id: 用户ID
            nickname: 昵称（可选）
            email: 邮箱（可选）
            bio: 个人简介（可选）
            avatar_url: 头像URL（可选）
        
        Returns:
            是否更新成功
        """
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            # 构建更新字段
            update_fields = []
            params = []
            
            if nickname is not None:
                update_fields.append("nickname = ?")
                params.append(nickname)
            
            if email is not None:
                update_fields.append("email = ?")
                params.append(email)
            
            if bio is not None:
                update_fields.append("bio = ?")
                params.append(bio)
            
            if avatar_url is not None:
                update_fields.append("avatar_url = ?")
                params.append(avatar_url)
            
            update_fields.append("updated_at = ?")
            params.append(now)
            params.append(user_id)
            
            query = f"UPDATE users SET {', '.join(update_fields)} WHERE user_id = ?"
            cursor.execute(query, params)
            
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"[用户存储] 更新用户成功: user_id={user_id}")
                return True
            else:
                logger.warning(f"[用户存储] 用户不存在: user_id={user_id}")
                return False
            
        except Exception as e:
            conn.rollback()
            logger.error(f"[用户存储] 更新用户失败: {e}", exc_info=True)
            raise
        finally:
            conn.close()
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户信息
        
        Args:
            user_id: 用户ID
        
        Returns:
            用户信息字典，不存在则返回None
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT user_id, nickname, email, bio, avatar_url, 
                       login_count, last_login_at, is_deleted, deleted_at, created_at, updated_at
                FROM users
                WHERE user_id = ? AND is_deleted = 0
            ''', (user_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'user_id': row[0],
                    'nickname': row[1],
                    'email': row[2],
                    'bio': row[3],
                    'avatar_url': row[4],
                    'login_count': row[5] or 0,
                    'last_login_at': row[6],
                    'is_deleted': row[7],
                    'deleted_at': row[8],
                    'created_at': row[9],
                    'updated_at': row[10]
                }
            return None
            
        except Exception as e:
            logger.error(f"[用户存储] 获取用户失败: {e}", exc_info=True)
            raise
        finally:
            conn.close()
    
    def bind_device(self, user_id: str, device_id: str, device_name: Optional[str] = None) -> bool:
        """绑定设备到用户
        
        Args:
            user_id: 用户ID
            device_id: 设备ID
            device_name: 设备名称（可选）
        
        Returns:
            是否绑定成功
        """
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            # 检查用户是否存在
            cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
            if not cursor.fetchone():
                logger.warning(f"[用户存储] 用户不存在: user_id={user_id}")
                return False
            
            # 检查设备是否已绑定
            cursor.execute('SELECT user_id FROM user_devices WHERE device_id = ?', (device_id,))
            existing = cursor.fetchone()
            
            if existing:
                # 设备已绑定到其他用户，解绑后重新绑定
                if existing[0] != user_id:
                    logger.warning(f"[用户存储] 设备已绑定到其他用户，将解绑: device_id={device_id}")
                    cursor.execute('DELETE FROM user_devices WHERE device_id = ?', (device_id,))
            
            # 绑定设备
            cursor.execute('''
                INSERT OR REPLACE INTO user_devices (user_id, device_id, device_name, bound_at)
                VALUES (?, ?, ?, ?)
            ''', (user_id, device_id, device_name, now))
            
            conn.commit()
            logger.info(f"[用户存储] 绑定设备成功: user_id={user_id}, device_id={device_id}")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"[用户存储] 绑定设备失败: {e}", exc_info=True)
            raise
        finally:
            conn.close()
    
    def unbind_device(self, device_id: str) -> bool:
        """解绑设备
        
        Args:
            device_id: 设备ID
        
        Returns:
            是否解绑成功
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM user_devices WHERE device_id = ?', (device_id,))
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"[用户存储] 解绑设备成功: device_id={device_id}")
                return True
            else:
                logger.warning(f"[用户存储] 设备未绑定: device_id={device_id}")
                return False
            
        except Exception as e:
            conn.rollback()
            logger.error(f"[用户存储] 解绑设备失败: {e}", exc_info=True)
            raise
        finally:
            conn.close()
    
    def get_user_by_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """通过设备ID获取用户信息
        
        Args:
            device_id: 设备ID
        
        Returns:
            用户信息字典（包含device_id），不存在则返回None
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT u.user_id, u.nickname, u.email, u.bio, u.avatar_url, 
                       u.login_count, u.last_login_at, u.is_deleted, u.deleted_at, 
                       u.created_at, u.updated_at, ud.device_id
                FROM users u
                INNER JOIN user_devices ud ON u.user_id = ud.user_id
                WHERE ud.device_id = ? AND u.is_deleted = 0
            ''', (device_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'user_id': row[0],
                    'nickname': row[1],
                    'email': row[2],
                    'bio': row[3],
                    'avatar_url': row[4],
                    'login_count': row[5] or 0,
                    'last_login_at': row[6],
                    'is_deleted': row[7],
                    'deleted_at': row[8],
                    'created_at': row[9],
                    'updated_at': row[10],
                    'device_id': row[11]
                }
            return None
            
        except Exception as e:
            logger.error(f"[用户存储] 通过设备ID获取用户失败: {e}", exc_info=True)
            raise
        finally:
            conn.close()
    
    def get_user_devices(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的所有设备
        
        Args:
            user_id: 用户ID
        
        Returns:
            设备列表
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT device_id, device_name, bound_at
                FROM user_devices
                WHERE user_id = ?
                ORDER BY bound_at DESC
            ''', (user_id,))
            
            devices = []
            for row in cursor.fetchall():
                devices.append({
                    'device_id': row[0],
                    'device_name': row[1],
                    'bound_at': row[2]
                })
            
            return devices
            
        except Exception as e:
            logger.error(f"[用户存储] 获取用户设备失败: {e}", exc_info=True)
            raise
        finally:
            conn.close()
    
    def create_or_update_user_by_device(self, device_id: str,
                                       nickname: Optional[str] = None,
                                       email: Optional[str] = None,
                                       bio: Optional[str] = None,
                                       avatar_url: Optional[str] = None) -> Dict[str, Any]:
        """通过设备ID创建或更新用户（便捷方法）
        
        如果设备已绑定用户，则更新该用户信息
        如果设备未绑定，则创建新用户并绑定设备
        
        Args:
            device_id: 设备ID
            nickname: 昵称（可选）
            email: 邮箱（可选）
            bio: 个人简介（可选）
            avatar_url: 头像URL（可选）
        
        Returns:
            用户信息字典
        """
        # 检查设备是否已绑定用户
        existing_user = self.get_user_by_device(device_id)
        
        if existing_user:
            # 更新现有用户
            user_id = existing_user['user_id']
            self.update_user(user_id, nickname, email, bio, avatar_url)
            logger.info(f"[用户存储] 更新现有用户: user_id={user_id}, device_id={device_id}")
        else:
            # 创建新用户并绑定设备
            user_id = self.create_user(nickname, email, bio, avatar_url)
            self.bind_device(user_id, device_id)
            logger.info(f"[用户存储] 创建新用户并绑定设备: user_id={user_id}, device_id={device_id}")
        
        # 返回最新用户信息
        user = self.get_user_by_device(device_id)
        return user
    
    def delete_user(self, user_id: str, hard_delete: bool = False) -> bool:
        """删除用户（默认软删除）
        
        Args:
            user_id: 用户ID
            hard_delete: 是否硬删除（物理删除），默认 False（软删除）
        
        Returns:
            是否删除成功
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            if hard_delete:
                # 硬删除：物理删除用户及关联数据
                cursor.execute('DELETE FROM user_devices WHERE user_id = ?', (user_id,))
                cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
                logger.info(f"[用户存储] 硬删除用户成功: user_id={user_id}")
            else:
                # 软删除：标记为已删除
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute('''
                    UPDATE users
                    SET is_deleted = 1, deleted_at = ?, updated_at = ?
                    WHERE user_id = ? AND is_deleted = 0
                ''', (now, now, user_id))
                logger.info(f"[用户存储] 软删除用户成功: user_id={user_id}")
            
            conn.commit()
            
            if cursor.rowcount > 0:
                return True
            else:
                logger.warning(f"[用户存储] 用户不存在或已删除: user_id={user_id}")
                return False
            
        except Exception as e:
            conn.rollback()
            logger.error(f"[用户存储] 删除用户失败: {e}", exc_info=True)
            raise
        finally:
            conn.close()
    
    def restore_user(self, user_id: str) -> bool:
        """恢复已删除的用户
        
        Args:
            user_id: 用户ID
        
        Returns:
            是否恢复成功
        """
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE users
                SET is_deleted = 0, deleted_at = NULL, updated_at = ?
                WHERE user_id = ? AND is_deleted = 1
            ''', (now, user_id))
            
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"[用户存储] 恢复用户成功: user_id={user_id}")
                return True
            else:
                logger.warning(f"[用户存储] 用户不存在或未被删除: user_id={user_id}")
                return False
            
        except Exception as e:
            conn.rollback()
            logger.error(f"[用户存储] 恢复用户失败: {e}", exc_info=True)
            raise
        finally:
            conn.close()
    
    def update_login(self, user_id: str) -> bool:
        """更新用户登录信息（登录次数+1，更新最后登录时间）
        
        Args:
            user_id: 用户ID
        
        Returns:
            是否更新成功
        """
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE users
                SET login_count = COALESCE(login_count, 0) + 1,
                    last_login_at = ?,
                    updated_at = ?
                WHERE user_id = ?
            ''', (now, now, user_id))
            
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"[用户存储] 更新登录信息成功: user_id={user_id}")
                return True
            else:
                logger.warning(f"[用户存储] 用户不存在: user_id={user_id}")
                return False
            
        except Exception as e:
            conn.rollback()
            logger.error(f"[用户存储] 更新登录信息失败: {e}", exc_info=True)
            raise
        finally:
            conn.close()
    
    def login_by_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """通过设备ID登录（自动更新登录信息）
        
        Args:
            device_id: 设备ID
        
        Returns:
            用户信息字典，不存在则返回None
        """
        # 获取用户信息
        user = self.get_user_by_device(device_id)
        
        if user:
            # 更新登录信息
            self.update_login(user['user_id'])
            # 重新获取更新后的用户信息
            user = self.get_user_by_device(device_id)
            logger.info(f"[用户存储] 设备登录成功: device_id={device_id}, user_id={user['user_id']}")
        
        return user

