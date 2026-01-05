"""
消费计量服务模块 (v1.2.1 重构版)

核心变化：
- 消费记录同时记录 user_id 和 device_id
- 月度汇总按 user_id + device_id 统计

功能：
- ASR消费记录
- LLM消费记录
- 月度汇总更新
- 消费历史查询
"""

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from src.core.config import Config
from src.core.logger import get_logger

logger = get_logger("ConsumptionService")


class ConsumptionService:
    """消费计量服务（v1.2.1 重构：记录用户和设备）"""
    
    def __init__(self, config: Config):
        """初始化消费服务
        
        Args:
            config: 配置对象
        """
        self.config = config
        
        # 获取数据库路径
        data_dir = Path(config.get('storage.data_dir')).expanduser()
        database_relative = Path(config.get('storage.database'))
        self.db_path = data_dir / database_relative
        
        logger.info(f"[消费服务] 初始化 (v1.2.1)，数据库: {self.db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA foreign_keys=ON')
        return conn
    
    def record_asr_consumption(
        self,
        user_id: str,
        device_id: str,
        duration_ms: int,
        start_time: int,
        end_time: int,
        provider: str = 'volcano',
        language: str = 'zh-CN',
        session_id: Optional[str] = None
    ) -> str:
        """记录ASR消费
        
        Args:
            user_id: 用户ID
            device_id: 设备ID
            duration_ms: 时长（毫秒）
            start_time: 开始时间（毫秒时间戳）
            end_time: 结束时间（毫秒时间戳）
            provider: ASR提供商
            language: 语言
            session_id: 会话ID
        
        Returns:
            消费记录ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            record_id = str(uuid.uuid4())
            now = datetime.now()
            year = now.year
            month = now.month
            timestamp = now.timestamp()
            created_at = now.strftime('%Y-%m-%d %H:%M:%S')
            
            # 构建详情JSON
            details = {
                'duration_ms': duration_ms,
                'start_time': start_time,
                'end_time': end_time,
                'provider': provider,
                'language': language
            }
            
            import json
            details_json = json.dumps(details, ensure_ascii=False)
            
            # 插入消费记录
            cursor.execute('''
                INSERT INTO consumption_records 
                (id, user_id, device_id, year, month, type, amount, unit, model_source, details, session_id, timestamp, created_at)
                VALUES (?, ?, ?, ?, ?, 'asr', ?, 'ms', 'vendor', ?, ?, ?, ?)
            ''', (record_id, user_id, device_id, year, month, duration_ms, details_json, session_id, timestamp, created_at))
            
            # 更新月度汇总
            self._update_monthly_asr_with_cursor(cursor, user_id, device_id, year, month, duration_ms)
            
            conn.commit()
            
            logger.info(f"[消费服务] ASR消费已记录: user_id={user_id}, device_id={device_id}, {duration_ms}ms")
            
            return record_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"[消费服务] 记录ASR消费失败: {e}", exc_info=True)
            raise
        finally:
            conn.close()
    
    def record_llm_consumption(
        self,
        user_id: str,
        device_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        model: str,
        provider: str = 'openai',
        model_source: str = 'vendor',
        request_id: Optional[str] = None
    ) -> str:
        """记录LLM消费
        
        Args:
            user_id: 用户ID
            device_id: 设备ID
            prompt_tokens: 输入tokens
            completion_tokens: 输出tokens
            total_tokens: 总tokens
            model: 模型名称
            provider: LLM提供商
            model_source: 模型来源（'vendor'或'user'）
            request_id: 请求ID
        
        Returns:
            消费记录ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            record_id = str(uuid.uuid4())
            now = datetime.now()
            year = now.year
            month = now.month
            timestamp = now.timestamp()
            created_at = now.strftime('%Y-%m-%d %H:%M:%S')
            
            # 构建详情JSON
            details = {
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'total_tokens': total_tokens,
                'model': model,
                'provider': provider,
                'model_source': model_source
            }
            
            import json
            details_json = json.dumps(details, ensure_ascii=False)
            
            # 插入消费记录（用户自备模型也记录，但不计入额度）
            cursor.execute('''
                INSERT INTO consumption_records 
                (id, user_id, device_id, year, month, type, amount, unit, model_source, details, session_id, timestamp, created_at)
                VALUES (?, ?, ?, ?, ?, 'llm', ?, 'tokens', ?, ?, ?, ?, ?)
            ''', (record_id, user_id, device_id, year, month, total_tokens, model_source, details_json, request_id, timestamp, created_at))
            
            # 仅平台模型计入额度
            if model_source == 'vendor':
                self._update_monthly_llm_with_cursor(cursor, user_id, device_id, year, month, prompt_tokens, completion_tokens, total_tokens)
            
            conn.commit()
            
            logger.info(f"[消费服务] LLM消费已记录: user_id={user_id}, device_id={device_id}, {total_tokens} tokens, model_source={model_source}")
            
            return record_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"[消费服务] 记录LLM消费失败: {e}", exc_info=True)
            raise
        finally:
            conn.close()
    
    def _update_monthly_asr_with_cursor(
        self, 
        cursor: sqlite3.Cursor, 
        user_id: str,
        device_id: str, 
        year: int, 
        month: int, 
        duration_ms: int
    ) -> None:
        """使用提供的游标更新月度ASR汇总（按user_id汇总，device_id仅用于记录）"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 尝试更新（按user_id汇总，不区分device_id）
        cursor.execute('''
            UPDATE monthly_consumption
            SET asr_duration_ms = asr_duration_ms + ?,
                record_count = record_count + 1,
                updated_at = ?
            WHERE user_id = ? AND year = ? AND month = ?
        ''', (duration_ms, now, user_id, year, month))
        
        # 如果没有更新任何行，说明记录不存在，需要插入
        if cursor.rowcount == 0:
            cursor.execute('''
                INSERT INTO monthly_consumption 
                (user_id, year, month, asr_duration_ms, llm_prompt_tokens, llm_completion_tokens, llm_total_tokens, record_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, 0, 0, 0, 1, ?, ?)
            ''', (user_id, year, month, duration_ms, now, now))
    
    def _update_monthly_llm_with_cursor(
        self,
        cursor: sqlite3.Cursor,
        user_id: str,
        device_id: str,
        year: int,
        month: int,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int
    ) -> None:
        """使用提供的游标更新月度LLM汇总（按user_id汇总，device_id仅用于记录）"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 尝试更新（按user_id汇总，不区分device_id）
        cursor.execute('''
            UPDATE monthly_consumption
            SET llm_prompt_tokens = llm_prompt_tokens + ?,
                llm_completion_tokens = llm_completion_tokens + ?,
                llm_total_tokens = llm_total_tokens + ?,
                record_count = record_count + 1,
                updated_at = ?
            WHERE user_id = ? AND year = ? AND month = ?
        ''', (prompt_tokens, completion_tokens, total_tokens, now, user_id, year, month))
        
        # 如果没有更新任何行，说明记录不存在，需要插入
        if cursor.rowcount == 0:
            cursor.execute('''
                INSERT INTO monthly_consumption 
                (user_id, year, month, asr_duration_ms, llm_prompt_tokens, llm_completion_tokens, llm_total_tokens, record_count, created_at, updated_at)
                VALUES (?, ?, ?, 0, ?, ?, ?, 1, ?, ?)
            ''', (user_id, year, month, prompt_tokens, completion_tokens, total_tokens, now, now))
    
    def get_monthly_consumption(
        self, 
        user_id: str, 
        device_id: Optional[str] = None,
        year: Optional[int] = None, 
        month: Optional[int] = None
    ) -> Dict[str, Any]:
        """获取月度消费汇总（以user_id为主，device_id仅用于查询明细）
        
        Args:
            user_id: 用户ID
            device_id: 设备ID（可选，用于查询该设备的消费明细，不影响汇总结果）
            year: 年份（默认当前年）
            month: 月份（默认当前月）
        
        Returns:
            月度消费统计（按user_id汇总，包含所有设备的消费）
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            year = year or datetime.now().year
            month = month or datetime.now().month
            
            # 计算下次重置时间（下月1号）
            from calendar import monthrange
            if month == 12:
                next_year, next_month = year + 1, 1
            else:
                next_year, next_month = year, month + 1
            reset_at = f"{next_year}-{next_month:02d}-01 00:00:00"
            
            # 查询用户月度汇总（按user_id汇总，不区分device_id）
            cursor.execute('''
                SELECT * FROM monthly_consumption
                WHERE user_id = ? AND year = ? AND month = ?
            ''', (user_id, year, month))
            row = cursor.fetchone()
            
            if not row:
                # 新用户没有消费记录，返回默认值
                return {
                    'user_id': user_id,
                    'device_id': device_id,  # 保留device_id用于标识查询的设备
                    'year': year,
                    'month': month,
                    'asr_used_ms': 0,
                    'llm_used_tokens': 0,
                    'reset_at': reset_at
                }
            
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
            
            # 返回数据，统一字段名
            result = {
                'user_id': row['user_id'],
                'year': row['year'],
                'month': row['month'],
                'asr_used_ms': row['asr_duration_ms'] or 0,
                'llm_used_tokens': row['llm_total_tokens'] or 0,
                'reset_at': reset_at
            }
            
            # 如果查询了设备明细，添加到结果中
            if device_detail:
                result['device_detail'] = device_detail
            
            return result
            
        finally:
            conn.close()
    
    def get_consumption_records(
        self,
        user_id: str,
        device_id: Optional[str] = None,
        consumption_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取消费记录列表
        
        Args:
            user_id: 用户ID
            device_id: 设备ID（可选）
            consumption_type: 消费类型（'asr'或'llm'，可选）
            limit: 返回数量限制
            offset: 偏移量
        
        Returns:
            消费记录列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 构建查询条件
            where_clauses = ['user_id = ?']
            params = [user_id]
            
            if device_id:
                where_clauses.append('device_id = ?')
                params.append(device_id)
            
            if consumption_type:
                where_clauses.append('type = ?')
                params.append(consumption_type)
            
            where_sql = ' AND '.join(where_clauses)
            
            # 执行查询
            cursor.execute(f'''
                SELECT * FROM consumption_records
                WHERE {where_sql}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            ''', params + [limit, offset])
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        finally:
            conn.close()
