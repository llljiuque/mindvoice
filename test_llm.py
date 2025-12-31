#!/usr/bin/env python3
"""
LLM 集成测试脚本
用于测试 LiteLLM 集成是否正常工作
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.config import Config
from src.services.llm_service import LLMService


async def test_llm_service():
    """测试 LLM 服务"""
    print("=" * 60)
    print("LLM 集成测试")
    print("=" * 60)
    
    # 初始化配置
    print("\n1. 加载配置...")
    config = Config()
    llm_config = config.get('llm')
    
    if llm_config:
        print(f"   ✓ LLM 配置已加载")
        print(f"   - 提供商: {llm_config.get('provider')}")
        print(f"   - 模型: {llm_config.get('model')}")
        print(f"   - Base URL: {llm_config.get('base_url')}")
    else:
        print("   ✗ 未找到 LLM 配置")
        return
    
    # 初始化 LLM 服务
    print("\n2. 初始化 LLM 服务...")
    llm_service = LLMService(config)
    
    if llm_service.is_available():
        print("   ✓ LLM 服务初始化成功")
        info = llm_service.get_provider_info()
        print(f"   - 服务可用: {info['available']}")
        print(f"   - 提供商名称: {info['name']}")
    else:
        print("   ✗ LLM 服务不可用")
        return
    
    # 测试简单对话
    print("\n3. 测试简单对话...")
    try:
        response = await llm_service.simple_chat(
            user_message="你好！请用一句话介绍你自己。",
            system_prompt="你是一个友好的AI助手。",
            temperature=0.7
        )
        print(f"   ✓ 对话成功")
        print(f"   用户: 你好！请用一句话介绍你自己。")
        print(f"   助手: {response}")
    except Exception as e:
        print(f"   ✗ 对话失败: {e}")
        return
    
    # 测试多轮对话
    print("\n4. 测试多轮对话...")
    try:
        messages = [
            {"role": "system", "content": "你是一个数学老师。"},
            {"role": "user", "content": "1+1等于几？"},
            {"role": "assistant", "content": "1+1等于2。"},
            {"role": "user", "content": "那2+2呢？"}
        ]
        
        response = await llm_service.chat(
            messages=messages,
            temperature=0.3
        )
        print(f"   ✓ 多轮对话成功")
        print(f"   用户: 那2+2呢？")
        print(f"   助手: {response}")
    except Exception as e:
        print(f"   ✗ 多轮对话失败: {e}")
        return
    
    # 测试流式输出
    print("\n5. 测试流式输出...")
    try:
        print("   助手: ", end="", flush=True)
        stream = await llm_service.simple_chat(
            user_message="用一句话解释什么是人工智能",
            stream=True,
            temperature=0.7
        )
        
        full_response = ""
        async for chunk in stream:
            print(chunk, end="", flush=True)
            full_response += chunk
        
        print()  # 换行
        print(f"   ✓ 流式输出成功（共 {len(full_response)} 字符）")
    except Exception as e:
        print(f"\n   ✗ 流式输出失败: {e}")
        return
    
    print("\n" + "=" * 60)
    print("✓ 所有测试通过！LLM 集成工作正常。")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(test_llm_service())
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n\n测试失败: {e}")
        import traceback
        traceback.print_exc()

