#!/usr/bin/env python3
"""
火山引擎 ASR 认证测试脚本（使用 app_id）
尝试使用 app_id 而不是 app_key 进行认证
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.config import Config
from src.providers.asr.volcano import VolcanoASRProvider, RequestBuilder
import aiohttp
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_with_app_id():
    """使用 app_id 测试认证"""
    print("=" * 60)
    print("🔐 火山引擎 ASR 认证测试（使用 app_id）")
    print("=" * 60)
    
    # 加载配置
    config = Config()
    asr_config = {
        'base_url': config.get('asr.base_url', 'wss://openspeech.bytedance.com/api/v3/sauc/bigmodel'),
        'app_id': config.get('asr.app_id', ''),
        'app_key': config.get('asr.app_key', ''),
        'access_key': config.get('asr.access_key', '')
    }
    
    app_id = asr_config['app_id']
    access_key = asr_config['access_key']
    
    print("\n📋 配置信息：")
    print(f"  base_url: {asr_config['base_url']}")
    print(f"  app_id: {app_id}")
    print(f"  access_key: {access_key[:8]}...{access_key[-4:] if len(access_key) > 12 else '***'}")
    
    if not access_key or not access_key.strip():
        print("❌ 错误: access_key 未设置")
        return False
    
    if not app_id or not app_id.strip():
        print("❌ 错误: app_id 未设置")
        return False
    
    # 尝试使用 app_id 作为 app_key
    print("\n🔌 尝试连接（使用 app_id 作为 app_key）...")
    
    try:
        # 使用 app_id 而不是 app_key
        headers = RequestBuilder.new_auth_headers(access_key, app_id)
        
        print(f"  认证头: X-Api-Access-Key={access_key[:8]}...")
        print(f"  认证头: X-Api-App-Key={app_id}")
        
        timeout = aiohttp.ClientTimeout(total=30)
        session = aiohttp.ClientSession(timeout=timeout)
        
        try:
            conn = await session.ws_connect(asr_config['base_url'], headers=headers)
            print("\n" + "=" * 60)
            print("✅ 认证成功！（使用 app_id）")
            print("=" * 60)
            print("\n解决方案：需要在 config.yml 中将 app_key 设置为 app_id 的值")
            await conn.close()
            await session.close()
            return True
        except aiohttp.ClientResponseError as e:
            print(f"\n❌ 连接失败: HTTP {e.status}: {e.message}")
            await session.close()
            return False
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_with_app_key():
    """使用 app_key 测试认证"""
    print("\n" + "=" * 60)
    print("🔐 火山引擎 ASR 认证测试（使用 app_key）")
    print("=" * 60)
    
    # 加载配置
    config = Config()
    asr_config = {
        'base_url': config.get('asr.base_url', 'wss://openspeech.bytedance.com/api/v3/sauc/bigmodel'),
        'app_id': config.get('asr.app_id', ''),
        'app_key': config.get('asr.app_key', ''),
        'access_key': config.get('asr.access_key', '')
    }
    
    app_key = asr_config['app_key']
    access_key = asr_config['access_key']
    
    print("\n📋 配置信息：")
    print(f"  base_url: {asr_config['base_url']}")
    print(f"  app_key: {app_key[:8]}...{app_key[-4:] if len(app_key) > 12 else '***'}")
    print(f"  access_key: {access_key[:8]}...{access_key[-4:] if len(access_key) > 12 else '***'}")
    
    if not access_key or not access_key.strip():
        print("❌ 错误: access_key 未设置")
        return False
    
    if not app_key or not app_key.strip():
        print("❌ 错误: app_key 未设置")
        return False
    
    # 尝试使用 app_key
    print("\n🔌 尝试连接（使用 app_key）...")
    
    try:
        headers = RequestBuilder.new_auth_headers(access_key, app_key)
        
        print(f"  认证头: X-Api-Access-Key={access_key[:8]}...")
        print(f"  认证头: X-Api-App-Key={app_key[:8]}...")
        
        timeout = aiohttp.ClientTimeout(total=30)
        session = aiohttp.ClientSession(timeout=timeout)
        
        try:
            conn = await session.ws_connect(asr_config['base_url'], headers=headers)
            print("\n" + "=" * 60)
            print("✅ 认证成功！（使用 app_key）")
            print("=" * 60)
            await conn.close()
            await session.close()
            return True
        except aiohttp.ClientResponseError as e:
            print(f"\n❌ 连接失败: HTTP {e.status}: {e.message}")
            await session.close()
            return False
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    # 先测试使用 app_id
    result1 = await test_with_app_id()
    
    # 再测试使用 app_key
    result2 = await test_with_app_key()
    
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    print(f"  使用 app_id: {'✅ 成功' if result1 else '❌ 失败'}")
    print(f"  使用 app_key: {'✅ 成功' if result2 else '❌ 失败'}")
    
    if result1:
        print("\n💡 建议：在 config.yml 中设置 app_key 为 app_id 的值")
    elif result2:
        print("\n💡 当前配置正确，但可能凭证本身有问题")
    else:
        print("\n💡 两种方式都失败，可能是凭证问题，建议：")
        print("  1. 检查凭证是否正确")
        print("  2. 检查凭证是否过期")
        print("  3. 检查服务是否已开通")
        print("  4. 在火山引擎控制台重新生成凭证")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 程序错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

