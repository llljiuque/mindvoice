#!/usr/bin/env python3
"""
测试 SmartChat 记录结构
验证 conversation_metadata 的完整性
"""

import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.config import Config


def test_smartchat_structure():
    """测试 SmartChat 记录结构"""
    print("=" * 80)
    print("SmartChat 记录结构测试")
    print("=" * 80)
    
    # 1. 加载配置
    config = Config()
    storage_config = config.get('storage', {})
    data_dir = Path(storage_config.get('data_dir', '~/MindVoice')).expanduser()
    db_path = data_dir / storage_config.get('database', 'database/history.db')
    
    print(f"\n📁 数据库路径: {db_path}")
    
    if not db_path.exists():
        print("❌ 数据库文件不存在")
        return
    
    # 2. 连接数据库
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 3. 查询 SmartChat 记录
    cursor.execute("""
        SELECT id, text, metadata, app_type, created_at
        FROM records
        WHERE app_type = 'smart-chat'
        ORDER BY created_at DESC
        LIMIT 5
    """)
    
    records = cursor.fetchall()
    
    print(f"\n📊 找到 {len(records)} 条 SmartChat 记录\n")
    
    if len(records) == 0:
        print("💡 提示: 暂无 SmartChat 记录，请先使用 SmartChat 进行对话并保存")
        conn.close()
        return
    
    # 4. 验证每条记录的结构
    for idx, (record_id, text, metadata_json, app_type, created_at) in enumerate(records, 1):
        print(f"\n{'=' * 80}")
        print(f"记录 #{idx}")
        print(f"{'=' * 80}")
        print(f"ID: {record_id}")
        print(f"App Type: {app_type}")
        print(f"创建时间: {created_at}")
        print(f"\n📝 纯文本内容 (前200字符):")
        print(f"{text[:200]}...")
        
        # 解析 metadata
        try:
            metadata = json.loads(metadata_json) if metadata_json else {}
        except json.JSONDecodeError as e:
            print(f"❌ metadata 解析失败: {e}")
            continue
        
        # 验证 messages
        messages = metadata.get('messages', [])
        print(f"\n💬 消息数量: {len(messages)}")
        
        if len(messages) > 0:
            print(f"   - 首条消息: {messages[0].get('role', 'unknown')} - {messages[0].get('content', '')[:50]}...")
            print(f"   - 末条消息: {messages[-1].get('role', 'unknown')} - {messages[-1].get('content', '')[:50]}...")
        
        # 验证 conversation_metadata
        conv_metadata = metadata.get('conversation_metadata', {})
        print(f"\n📊 对话元数据 (conversation_metadata):")
        
        # 基础统计
        print(f"   ✅ total_messages: {conv_metadata.get('total_messages', 'N/A')}")
        print(f"   ✅ total_turns: {conv_metadata.get('total_turns', 'N/A')}")
        
        # 时间信息
        print(f"   ✅ first_message_time: {conv_metadata.get('first_message_time', 'N/A')}")
        print(f"   ✅ last_message_time: {conv_metadata.get('last_message_time', 'N/A')}")
        print(f"   ✅ conversation_duration: {conv_metadata.get('conversation_duration', 'N/A')} 秒")
        
        # 功能配置
        print(f"   ✅ use_knowledge: {conv_metadata.get('use_knowledge', 'N/A')}")
        print(f"   ✅ use_history: {conv_metadata.get('use_history', 'N/A')}")
        
        # LLM 配置
        print(f"   ✅ llm_provider: {conv_metadata.get('llm_provider', 'N/A')}")
        print(f"   ✅ llm_model: {conv_metadata.get('llm_model', 'N/A')}")
        print(f"   ✅ temperature: {conv_metadata.get('temperature', 'N/A')}")
        
        # 其他信息
        print(f"   ✅ language: {conv_metadata.get('language', 'N/A')}")
        print(f"   ✅ session_id: {conv_metadata.get('session_id', 'N/A')}")
        print(f"   ✅ title: {conv_metadata.get('title', 'N/A')}")
        
        # 检查完整性
        required_fields = [
            'total_messages', 'total_turns', 'first_message_time', 
            'last_message_time', 'conversation_duration', 'use_knowledge',
            'use_history', 'llm_provider', 'llm_model', 'language'
        ]
        
        missing_fields = [f for f in required_fields if f not in conv_metadata]
        
        if missing_fields:
            print(f"\n⚠️  缺失字段: {', '.join(missing_fields)}")
        else:
            print(f"\n✅ 所有必需字段完整")
        
        # 验证 messages 结构
        print(f"\n🔍 消息结构验证:")
        if len(messages) > 0:
            sample_msg = messages[0]
            msg_fields = ['id', 'role', 'content', 'timestamp']
            msg_missing = [f for f in msg_fields if f not in sample_msg]
            
            if msg_missing:
                print(f"   ⚠️  消息缺失字段: {', '.join(msg_missing)}")
            else:
                print(f"   ✅ 消息结构完整")
    
    conn.close()
    
    print(f"\n{'=' * 80}")
    print("✅ 测试完成")
    print(f"{'=' * 80}\n")


def show_metadata_example():
    """显示标准的 metadata 结构示例"""
    print("\n" + "=" * 80)
    print("标准 SmartChat metadata 结构示例")
    print("=" * 80)
    
    example = {
        "messages": [
            {
                "id": "1736121234567",
                "role": "user",
                "content": "你好，请介绍一下Python",
                "timestamp": 1736121234567
            },
            {
                "id": "1736121234568",
                "role": "assistant",
                "content": "你好！Python是一种高级编程语言...",
                "timestamp": 1736121234568
            }
        ],
        "conversation_metadata": {
            "total_messages": 10,
            "total_turns": 5,
            "first_message_time": "2026-01-06T02:00:00.000Z",
            "last_message_time": "2026-01-06T02:15:00.000Z",
            "conversation_duration": 900,
            "use_knowledge": True,
            "use_history": True,
            "knowledge_top_k": 3,
            "llm_provider": "deepseek",
            "llm_model": "deepseek-chat",
            "temperature": 0.7,
            "max_tokens": 2000,
            "max_history_turns": 10,
            "language": "zh-CN",
            "session_id": "session-20260106-020000",
            "title": "Python 基础学习对话"
        },
        "message_count": 10,
        "use_knowledge": True
    }
    
    print(json.dumps(example, ensure_ascii=False, indent=2))
    print("=" * 80 + "\n")


if __name__ == '__main__':
    show_metadata_example()
    test_smartchat_structure()

