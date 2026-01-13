#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试TTS模块导入和初始化
"""
import sys
import io
from pathlib import Path

# 设置标准输出编码为UTF-8（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """测试导入"""
    print("=" * 60)
    print("测试TTS模块导入")
    print("=" * 60)
    
    try:
        # 测试提供商模块导入
        print("\n1. 测试提供商模块导入...")
        from src.providers.tts import get_tts_provider_class, list_available_tts_providers
        print("   ✓ 提供商模块导入成功")
        
        # 测试列出可用提供商
        print("\n2. 测试列出可用提供商...")
        providers = list_available_tts_providers()
        print(f"   ✓ 可用提供商: {providers}")
        
        # 测试获取提供商类
        print("\n3. 测试获取提供商类...")
        for provider_name in providers:
            provider_class = get_tts_provider_class(provider_name)
            if provider_class:
                print(f"   ✓ {provider_name}: {provider_class.__name__}")
                # 检查类属性
                display_name = getattr(provider_class, 'DISPLAY_NAME', None)
                description = getattr(provider_class, 'DESCRIPTION', None)
                if display_name:
                    print(f"     显示名称: {display_name}")
                if description:
                    print(f"     描述: {description}")
            else:
                print(f"   ✗ {provider_name}: 未找到")
        
        # 测试TTS服务导入
        print("\n4. 测试TTS服务导入...")
        from src.services.tts_service import TTSService
        print("   ✓ TTS服务导入成功")
        
        # 测试配置导入
        print("\n5. 测试配置导入...")
        from src.core.config import Config
        config = Config()
        print("   ✓ 配置导入成功")
        
        # 测试TTS服务初始化
        print("\n6. 测试TTS服务初始化...")
        tts_service = TTSService(config)
        print(f"   ✓ TTS服务初始化成功")
        print(f"   当前提供商: {tts_service.get_provider_name()}")
        is_available = tts_service.is_available()
        print(f"   服务可用: {is_available}")
        
        if not is_available:
            print("\n   ⚠️  警告：TTS服务不可用")
            print("   可能的原因：")
            print("   1. 缺少依赖（modelscope, funasr, soundfile等）")
            print("   2. 提供商初始化失败")
            print("   3. 配置错误")
            print("\n   建议运行诊断脚本：")
            print("   python tests/test_tts_diagnosis.py")
        
        print("\n" + "=" * 60)
        if is_available:
            print("✓ 所有测试通过！TTS服务可用")
        else:
            print("⚠️  模块导入测试通过，但TTS服务不可用")
            print("   请检查依赖安装和配置")
        return True
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
