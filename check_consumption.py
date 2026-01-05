#!/usr/bin/env python3
"""
检查系统消费数据脚本

功能：
- 显示消费记录统计
- 显示月度汇总统计
- 显示用户和设备消费分布
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# 从配置文件读取数据库路径
def get_db_path():
    """从config.yml读取数据库路径"""
    import yaml
    
    config_path = Path(__file__).parent / 'config.yml'
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        return None
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    data_dir = Path(config.get('storage', {}).get('data_dir', '~/Library/Application Support/MindVoice')).expanduser()
    database_relative = Path(config.get('storage', {}).get('database', 'database/history.db'))
    db_path = data_dir / database_relative
    
    return db_path


def format_number(num):
    """格式化数字显示"""
    if num is None:
        return 0
    if num >= 1000000:
        return f"{num/1000000:.2f}M"
    elif num >= 1000:
        return f"{num/1000:.2f}K"
    return str(num)


def format_duration(ms):
    """格式化时长显示"""
    if ms is None or ms == 0:
        return "0ms"
    
    if ms >= 3600000:  # 小时
        hours = ms // 3600000
        minutes = (ms % 3600000) // 60000
        return f"{hours}h {minutes}m"
    elif ms >= 60000:  # 分钟
        minutes = ms // 60000
        seconds = (ms % 60000) // 1000
        return f"{minutes}m {seconds}s"
    elif ms >= 1000:  # 秒
        seconds = ms // 1000
        return f"{seconds}s"
    return f"{ms}ms"


def check_consumption_records(conn):
    """检查消费记录表"""
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("📊 消费记录统计 (consumption_records)")
    print("="*80)
    
    # 总记录数
    cursor.execute("SELECT COUNT(*) as total FROM consumption_records")
    total = cursor.fetchone()[0]
    print(f"\n总记录数: {total}")
    
    if total == 0:
        print("⚠️  暂无消费记录")
        return
    
    # 按类型统计
    cursor.execute("""
        SELECT type, COUNT(*) as count, 
               SUM(amount) as total_amount,
               AVG(amount) as avg_amount
        FROM consumption_records
        GROUP BY type
    """)
    
    print("\n按类型统计:")
    print("-" * 80)
    for row in cursor.fetchall():
        type_name = row[0]
        count = row[1]
        total_amount = row[2] or 0
        avg_amount = row[3] or 0
        
        if type_name == 'asr':
            print(f"  ASR: {count} 条记录, 总时长: {format_duration(int(total_amount))}, 平均: {format_duration(int(avg_amount))}")
        else:
            print(f"  LLM: {count} 条记录, 总tokens: {format_number(int(total_amount))}, 平均: {format_number(int(avg_amount))}")
    
    # 按模型来源统计
    cursor.execute("""
        SELECT model_source, COUNT(*) as count, 
               SUM(amount) as total_amount
        FROM consumption_records
        WHERE type = 'llm'
        GROUP BY model_source
    """)
    
    print("\nLLM按模型来源统计:")
    print("-" * 80)
    for row in cursor.fetchall():
        source = row[0] or 'unknown'
        count = row[1]
        total_amount = row[2] or 0
        print(f"  {source}: {count} 条记录, 总tokens: {format_number(int(total_amount))}")
    
    # 按用户统计
    cursor.execute("""
        SELECT user_id, COUNT(*) as count,
               SUM(CASE WHEN type = 'asr' THEN amount ELSE 0 END) as asr_total,
               SUM(CASE WHEN type = 'llm' THEN amount ELSE 0 END) as llm_total
        FROM consumption_records
        GROUP BY user_id
        ORDER BY count DESC
        LIMIT 10
    """)
    
    print("\n按用户统计 (Top 10):")
    print("-" * 80)
    for row in cursor.fetchall():
        user_id = row[0]
        count = row[1]
        asr_total = row[2] or 0
        llm_total = row[3] or 0
        print(f"  {user_id[:8]}...: {count} 条记录, ASR: {format_duration(int(asr_total))}, LLM: {format_number(int(llm_total))} tokens")
    
    # 按设备统计（device_id仅用于记录消费发生的设备）
    cursor.execute("""
        SELECT device_id, COUNT(*) as count,
               SUM(CASE WHEN type = 'asr' THEN amount ELSE 0 END) as asr_total,
               SUM(CASE WHEN type = 'llm' THEN amount ELSE 0 END) as llm_total
        FROM consumption_records
        GROUP BY device_id
        ORDER BY count DESC
        LIMIT 10
    """)
    
    print("\n按设备统计 (Top 10) - device_id仅用于标识消费发生的设备:")
    print("-" * 80)
    for row in cursor.fetchall():
        device_id = row[0]
        count = row[1]
        asr_total = row[2] or 0
        llm_total = row[3] or 0
        print(f"  {device_id[:8]}...: {count} 条记录, ASR: {format_duration(int(asr_total))}, LLM: {format_number(int(llm_total))} tokens")
    
    # 最近10条记录
    cursor.execute("""
        SELECT id, user_id, device_id, type, amount, unit, model_source, created_at
        FROM consumption_records
        ORDER BY timestamp DESC
        LIMIT 10
    """)
    
    print("\n最近10条记录:")
    print("-" * 80)
    for row in cursor.fetchall():
        record_id = row[0]
        user_id = row[1]
        device_id = row[2]
        type_name = row[3]
        amount = row[4]
        unit = row[5]
        model_source = row[6] or 'vendor'
        created_at = row[7]
        
        amount_str = format_duration(int(amount)) if unit == 'ms' else format_number(int(amount))
        print(f"  [{created_at}] {type_name.upper()} | {user_id[:8]}... | {device_id[:8]}... | {amount_str} {unit} | {model_source}")


def check_monthly_consumption(conn):
    """检查月度汇总表"""
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("📅 月度消费汇总 (monthly_consumption)")
    print("="*80)
    
    # 总记录数
    cursor.execute("SELECT COUNT(*) as total FROM monthly_consumption")
    total = cursor.fetchone()[0]
    print(f"\n总记录数: {total}")
    
    if total == 0:
        print("⚠️  暂无月度汇总记录")
        return
    
    # 按年月统计
    cursor.execute("""
        SELECT year, month, 
               COUNT(*) as record_count,
               SUM(asr_duration_ms) as total_asr,
               SUM(llm_total_tokens) as total_llm,
               SUM(record_count) as total_records
        FROM monthly_consumption
        GROUP BY year, month
        ORDER BY year DESC, month DESC
    """)
    
    print("\n按年月统计:")
    print("-" * 80)
    for row in cursor.fetchall():
        year = row[0]
        month = row[1]
        record_count = row[2]
        total_asr = row[3] or 0
        total_llm = row[4] or 0
        total_records = row[5] or 0
        print(f"  {year}-{month:02d}: {record_count} 条汇总记录, ASR: {format_duration(int(total_asr))}, LLM: {format_number(int(total_llm))} tokens, 明细记录: {total_records}")
    
    # 按用户统计（月度汇总以user_id为主）
    cursor.execute("""
        SELECT user_id, 
               COUNT(*) as month_count,
               SUM(asr_duration_ms) as total_asr,
               SUM(llm_total_tokens) as total_llm
        FROM monthly_consumption
        GROUP BY user_id
        ORDER BY total_llm DESC
        LIMIT 10
    """)
    
    print("\n按用户统计 (Top 10) - 月度汇总以user_id为主:")
    print("-" * 80)
    for row in cursor.fetchall():
        user_id = row[0]
        month_count = row[1]
        total_asr = row[2] or 0
        total_llm = row[3] or 0
        print(f"  {user_id[:8]}...: {month_count} 个月, ASR: {format_duration(int(total_asr))}, LLM: {format_number(int(total_llm))} tokens")
    
    # 当前月份汇总（按user_id汇总，不区分device_id）
    now = datetime.now()
    cursor.execute("""
        SELECT user_id, asr_duration_ms, llm_total_tokens, record_count, updated_at
        FROM monthly_consumption
        WHERE year = ? AND month = ?
        ORDER BY llm_total_tokens DESC
    """, (now.year, now.month))
    
    print(f"\n当前月份 ({now.year}-{now.month:02d}) 汇总（按user_id汇总，包含所有设备）:")
    print("-" * 80)
    rows = cursor.fetchall()
    if rows:
        for row in rows:
            user_id = row[0]
            asr_ms = row[1] or 0
            llm_tokens = row[2] or 0
            record_count = row[3] or 0
            updated_at = row[4]
            print(f"  {user_id[:8]}... | ASR: {format_duration(int(asr_ms))}, LLM: {format_number(int(llm_tokens))} tokens, 记录数: {record_count}, 更新: {updated_at}")
    else:
        print("  ⚠️  当前月份暂无汇总记录")


def check_system_status(conn):
    """检查系统状态"""
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("📋 系统状态")
    print("="*80)
    
    # 用户数
    cursor.execute("SELECT COUNT(*) as count FROM users")
    user_count = cursor.fetchone()[0]
    print(f"\n用户数: {user_count}")
    
    # 设备数
    cursor.execute("SELECT COUNT(*) as count FROM devices")
    device_count = cursor.fetchone()[0]
    print(f"设备数: {device_count}")
    
    # 会员数
    cursor.execute("SELECT COUNT(*) as count FROM memberships")
    membership_count = cursor.fetchone()[0]
    print(f"会员数: {membership_count}")
    
    # 会员详情
    if membership_count > 0:
        cursor.execute("""
            SELECT user_id, tier, status, expires_at, activated_at
            FROM memberships
            ORDER BY activated_at DESC
            LIMIT 5
        """)
        print("\n会员详情:")
        print("-" * 80)
        for row in cursor.fetchall():
            user_id = row[0]
            tier = row[1]
            status = row[2]
            expires_at = row[3] or '永久'
            activated_at = row[4]
            print(f"  {user_id[:8]}... | {tier} | {status} | 激活: {activated_at} | 到期: {expires_at}")


def main():
    """主函数"""
    print("="*80)
    print("🔍 MindVoice 消费数据检查工具")
    print("="*80)
    
    # 获取数据库路径
    db_path = get_db_path()
    if not db_path:
        return
    
    print(f"\n数据库路径: {db_path}")
    
    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return
    
    # 连接数据库
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        
        # 检查系统状态
        check_system_status(conn)
        
        # 检查表是否存在
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('consumption_records', 'monthly_consumption')
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        if 'consumption_records' not in tables:
            print("\n⚠️  消费记录表不存在，可能尚未初始化数据库")
        else:
            check_consumption_records(conn)
        
        if 'monthly_consumption' not in tables:
            print("\n⚠️  月度汇总表不存在，可能尚未初始化数据库")
        else:
            check_monthly_consumption(conn)
        
        conn.close()
        
        print("\n" + "="*80)
        print("✅ 检查完成")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

