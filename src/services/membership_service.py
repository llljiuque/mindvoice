"""
会员服务模块 (v1.2.1 重构版)

核心变化：
- 会员等级绑定到用户（user_id），而不是设备（device_id）
- 一个用户可以有多个设备，共享会员权益
- 消费记录区分设备，但额度按用户统计

功能：
- 设备注册与管理
- 会员信息管理（基于用户）
- 会员状态检查
- 会员升级与续费
- 额度查询与验证（按用户）
"""

import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from src.core.config import Config
from src.core.logger import get_logger

logger = get_logger("MembershipService")


class MembershipTier:
    """会员等级定义"""
    FREE = 'free'
    VIP = 'vip'
    PRO = 'pro'
    PRO_PLUS = 'pro_plus'


class MembershipStatus:
    """会员状态"""
    ACTIVE = 'active'
    EXPIRED = 'expired'
    PENDING = 'pending'


class MembershipQuota:
    """会员额度配置"""
    QUOTAS = {
        MembershipTier.FREE: {
            'asr_duration_ms_monthly': 3_600_000,      # 1小时
            'llm_tokens_monthly': 100_000,              # 10万tokens
        },
        MembershipTier.VIP: {
            'asr_duration_ms_monthly': 36_000_000,     # 10小时
            'llm_tokens_monthly': 1_000_000,            # 100万tokens
        },
        MembershipTier.PRO: {
            'asr_duration_ms_monthly': 180_000_000,    # 50小时
            'llm_tokens_monthly': 5_000_000,            # 500万tokens
        },
        MembershipTier.PRO_PLUS: {
            'asr_duration_ms_monthly': 720_000_000,    # 200小时
            'llm_tokens_monthly': 20_000_000,           # 2000万tokens
        }
    }


class MembershipService:
    """会员服务（v1.2.1 重构：以用户为中心）"""
    
    def __init__(self, config: Config):
        """初始化会员服务
        
        Args:
            config: 配置对象
        """
        self.config = config
        
        # 获取数据库路径
        data_dir = Path(config.get('storage.data_dir')).expanduser()
        database_relative = Path(config.get('storage.database'))
        self.db_path = data_dir / database_relative
        
        logger.info(f"[会员服务] 初始化 (v1.2.1)，数据库: {self.db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA foreign_keys=ON')
        return conn
    
    # ==================== 设备管理 ====================
    
    def register_device(self, device_id: str, machine_id: str, platform: str) -> Dict[str, Any]:
        """注册新设备（仅注册设备，不创建会员）
        
        Args:
            device_id: 设备ID
            machine_id: 机器ID
            platform: 平台（darwin/win32/linux）
        
        Returns:
            设备信息
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 检查设备是否已存在
            cursor.execute('SELECT * FROM devices WHERE device_id = ?', (device_id,))
            existing = cursor.fetchone()
            
            if existing:
                logger.info(f"[会员服务] 设备已注册: {device_id}")
                # 更新最后活跃时间
                cursor.execute('''
                    UPDATE devices 
                    SET last_active_at = ?
                    WHERE device_id = ?
                ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), device_id))
                conn.commit()
                
                return {
                    'device_id': device_id,
                    'is_new': False,
                    'machine_id': existing['machine_id'],
                    'platform': existing['platform'],
                    'first_registered_at': existing['first_registered_at'],
                    'last_active_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            
            # 注册新设备
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
                INSERT INTO devices (device_id, machine_id, platform, first_registered_at, last_active_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (device_id, machine_id, platform, now, now))
            
            conn.commit()
            
            logger.info(f"[会员服务] ✅ 新设备已注册: {device_id}")
            
            return {
                'device_id': device_id,
                'is_new': True,
                'machine_id': machine_id,
                'platform': platform,
                'first_registered_at': now,
                'last_active_at': now
            }
            
        except Exception as e:
            conn.rollback()
            logger.error(f"[会员服务] 注册设备失败: {e}", exc_info=True)
            raise
        finally:
            conn.close()
    
    # ==================== 会员信息管理 ====================
    
    def create_membership(self, user_id: str, tier: str = MembershipTier.FREE) -> Dict[str, Any]:
        """为用户创建会员（默认免费会员）
        
        Args:
            user_id: 用户ID
            tier: 会员等级（默认免费）
        
        Returns:
            会员信息
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 检查会员是否已存在
            cursor.execute('SELECT * FROM memberships WHERE user_id = ?', (user_id,))
            existing = cursor.fetchone()
            
            if existing:
                logger.warning(f"[会员服务] 会员已存在: {user_id}")
                return self.get_membership(user_id)
            
            # 创建会员
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
                INSERT INTO memberships (user_id, tier, status, subscription_period, activated_at, expires_at, auto_renew, created_at, updated_at)
                VALUES (?, ?, ?, NULL, ?, NULL, 0, ?, ?)
            ''', (user_id, tier, MembershipStatus.ACTIVE, now, now, now))
            
            conn.commit()
            
            logger.info(f"[会员服务] ✅ 会员已创建: user_id={user_id}, tier={tier}")
            
            return self.get_membership(user_id)
            
        except Exception as e:
            conn.rollback()
            logger.error(f"[会员服务] 创建会员失败: {e}", exc_info=True)
            raise
        finally:
            conn.close()
    
    def get_membership(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户会员信息
        
        Args:
            user_id: 用户ID
        
        Returns:
            会员信息字典，不存在时返回None
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM memberships WHERE user_id = ?
            ''', (user_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # 检查会员是否过期
            is_expired = False
            days_remaining = None
            
            if row['expires_at']:
                # 付费会员，检查过期时间
                expires_at = datetime.strptime(row['expires_at'], '%Y-%m-%d %H:%M:%S')
                now = datetime.now()
                
                if expires_at < now:
                    is_expired = True
                    # 自动降级到免费
                    self._downgrade_to_free(user_id)
                else:
                    days_remaining = (expires_at - now).days
            else:
                # 免费会员，永久有效
                is_expired = False
                days_remaining = None
            
            # 获取额度配置
            quota = MembershipQuota.QUOTAS.get(row['tier'], {})
            
            return {
                'user_id': user_id,
                'tier': row['tier'],
                'status': MembershipStatus.EXPIRED if is_expired else row['status'],
                'subscription_period': row['subscription_period'],
                'activated_at': row['activated_at'],
                'expires_at': row['expires_at'],
                'permanent': row['expires_at'] is None,
                'days_remaining': days_remaining,
                'is_active': not is_expired and row['status'] == MembershipStatus.ACTIVE,
                'quota': quota,
                'auto_renew': bool(row['auto_renew']),
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            }
            
        finally:
            conn.close()
    
    def _downgrade_to_free(self, user_id: str) -> None:
        """自动降级到免费会员"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
                UPDATE memberships
                SET tier = ?, status = ?, expires_at = NULL, subscription_period = NULL, updated_at = ?
                WHERE user_id = ?
            ''', (MembershipTier.FREE, MembershipStatus.ACTIVE, now, user_id))
            conn.commit()
            
            logger.info(f"[会员服务] 会员已过期，已自动降级到免费: user_id={user_id}")
            
        finally:
            conn.close()
    
    def activate_membership(self, user_id: str, tier: str, months: int) -> Dict[str, Any]:
        """激活/升级会员
        
        Args:
            user_id: 用户ID
            tier: 会员等级（vip/pro/pro_plus）
            months: 订阅月数
        
        Returns:
            更新后的会员信息
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 获取当前会员信息
            current = self.get_membership(user_id)
            if not current:
                raise ValueError(f"会员不存在: {user_id}")
            
            now = datetime.now()
            
            # 计算过期时间
            # 如果当前会员未过期，在原有基础上延长；否则从现在开始计算
            if current['expires_at'] and current['is_active']:
                expires_at_base = datetime.strptime(current['expires_at'], '%Y-%m-%d %H:%M:%S')
                if expires_at_base > now:
                    # 未过期，延长
                    expires_at = expires_at_base + timedelta(days=months * 30)
                else:
                    # 已过期，从现在开始
                    expires_at = now + timedelta(days=months * 30)
            else:
                # 免费会员或已过期，从现在开始
                expires_at = now + timedelta(days=months * 30)
            
            now_str = now.strftime('%Y-%m-%d %H:%M:%S')
            expires_at_str = expires_at.strftime('%Y-%m-%d %H:%M:%S')
            
            # 更新会员信息
            cursor.execute('''
                UPDATE memberships
                SET tier = ?, status = ?, subscription_period = ?, activated_at = ?, expires_at = ?, updated_at = ?
                WHERE user_id = ?
            ''', (tier, MembershipStatus.ACTIVE, months, now_str, expires_at_str, now_str, user_id))
            
            conn.commit()
            
            logger.info(f"[会员服务] ✅ 会员已激活: user_id={user_id}, {current['tier']} → {tier}, 有效期{months}个月")
            
            # 返回更新后的会员信息
            return self.get_membership(user_id)
            
        except Exception as e:
            conn.rollback()
            logger.error(f"[会员服务] 激活会员失败: {e}", exc_info=True)
            raise
        finally:
            conn.close()
    
    # ==================== 消费统计 ====================
    
    def get_current_consumption(self, user_id: str, device_id: Optional[str] = None) -> Dict[str, Any]:
        """获取当前月度消费情况
        
        Args:
            user_id: 用户ID
            device_id: 设备ID（可选，如果提供则只统计该设备）
        
        Returns:
            消费统计信息
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            year = datetime.now().year
            month = datetime.now().month
            
            # 获取月度汇总（按user_id汇总，不区分device_id）
            # device_id仅用于查询该设备的消费明细（从consumption_records表）
            cursor.execute('''
                SELECT * FROM monthly_consumption
                WHERE user_id = ? AND year = ? AND month = ?
            ''', (user_id, year, month))
            
            row = cursor.fetchone()
            if not row:
                # 没有记录
                asr_used = 0
                llm_used = 0
            else:
                asr_used = row['asr_duration_ms'] or 0
                llm_used = row['llm_total_tokens'] or 0
            
            # 如果指定了device_id，查询该设备的消费明细（从consumption_records表）
            device_detail = None
            if device_id:
                cursor.execute('''
                    SELECT 
                        SUM(CASE WHEN type = 'asr' THEN amount ELSE 0 END) as asr_ms,
                        SUM(CASE WHEN type = 'llm' THEN amount ELSE 0 END) as llm_tokens
                    FROM consumption_records
                    WHERE user_id = ? AND device_id = ? AND year = ? AND month = ?
                ''', (user_id, device_id, year, month))
                detail_row = cursor.fetchone()
                if detail_row:
                    device_detail = {
                        'device_id': device_id,
                        'asr_used_ms': int(detail_row[0] or 0),
                        'llm_used_tokens': int(detail_row[1] or 0)
                    }
            
            # 获取会员信息（获取额度限制）
            membership = self.get_membership(user_id)
            if not membership:
                raise ValueError(f"会员信息不存在: {user_id}")
            
            quota = membership['quota']
            asr_limit = quota.get('asr_duration_ms_monthly', 0)
            llm_limit = quota.get('llm_tokens_monthly', 0)
            
            # 计算剩余额度
            asr_remaining = max(0, asr_limit - asr_used)
            llm_remaining = max(0, llm_limit - llm_used)
            
            # 计算使用百分比
            asr_percentage = (asr_used / asr_limit * 100) if asr_limit > 0 else 0
            llm_percentage = (llm_used / llm_limit * 100) if llm_limit > 0 else 0
            
            # 计算下次重置时间（下月1日00:00:00）
            next_month = (datetime.now().replace(day=1) + timedelta(days=32)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            return {
                'user_id': user_id,
                'device_id': device_id,
                'year': year,
                'month': month,
                'asr': {
                    'used': asr_used,
                    'limit': asr_limit,
                    'remaining': asr_remaining,
                    'percentage': round(asr_percentage, 2)
                },
                'llm': {
                    'used': llm_used,
                    'limit': llm_limit,
                    'remaining': llm_remaining,
                    'percentage': round(llm_percentage, 2)
                },
                'is_active': membership['is_active'],
                'reset_at': next_month.strftime('%Y-%m-%d %H:%M:%S')
            }
            
        finally:
            conn.close()
    
    def check_quota(self, user_id: str, consumption_type: str, estimated_amount: int, model_source: str = 'vendor') -> Dict[str, Any]:
        """检查额度是否足够
        
        Args:
            user_id: 用户ID
            consumption_type: 消费类型（'asr'或'llm'）
            estimated_amount: 预估消费量
            model_source: 模型来源（'vendor'或'user'），仅LLM有效
        
        Returns:
            检查结果 {'allowed': bool, 'reason': str}
        """
        # 用户自备模型不检查额度
        if consumption_type == 'llm' and model_source == 'user':
            return {'allowed': True, 'reason': '用户自备模型，不限额度'}
        
        # 获取会员信息
        membership = self.get_membership(user_id)
        if not membership:
            return {'allowed': False, 'reason': '会员信息不存在'}
        
        # 检查会员是否有效
        if not membership['is_active']:
            return {'allowed': False, 'reason': '会员已过期，请续费'}
        
        # 获取当前消费
        consumption = self.get_current_consumption(user_id)
        
        # 检查额度
        if consumption_type == 'asr':
            if consumption['asr']['remaining'] < estimated_amount:
                return {
                    'allowed': False,
                    'reason': f"ASR额度不足，剩余{consumption['asr']['remaining']}ms，需要{estimated_amount}ms"
                }
        elif consumption_type == 'llm':
            if consumption['llm']['remaining'] < estimated_amount:
                return {
                    'allowed': False,
                    'reason': f"LLM额度不足，剩余{consumption['llm']['remaining']}tokens，需要{estimated_amount}tokens"
                }
        
        return {'allowed': True, 'reason': '额度充足'}
    
    # ==================== 工具方法 ====================
    
    def get_tier_name(self, tier: str) -> str:
        """获取会员等级名称"""
        names = {
            MembershipTier.FREE: '免费尝鲜',
            MembershipTier.VIP: 'VIP会员',
            MembershipTier.PRO: 'PRO会员',
            MembershipTier.PRO_PLUS: 'PRO+会员'
        }
        return names.get(tier, '未知')
