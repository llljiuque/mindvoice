#!/usr/bin/env python3
"""
火山引擎 ASR 认证测试脚本
用于验证 config.yml 中的凭证是否正确
"""
import asyncio
import sys
import os
from pathlib import Path

# 抑制 macOS IMK 警告（PyQt6 相关的无害警告）
# 这个警告出现在 macOS 上，与 Input Method Kit 相关，不影响功能
if sys.platform == 'darwin':
    # 设置环境变量以抑制 IMK 相关警告
    os.environ['QT_MAC_WANTS_LAYER'] = '1'
    
    # 过滤 stderr 中的特定 IMK 警告消息
    # 使用自定义 stderr 包装器来过滤该警告，同时保留其他错误信息
    class FilteredStderr:
        """过滤 stderr 中的 IMK 警告，保留其他输出"""
        def __init__(self, original_stderr):
            self.original_stderr = original_stderr
        
        def write(self, message):
            # 只过滤包含 IMKCFRunLoopWakeUpReliable 的消息
            if 'IMKCFRunLoopWakeUpReliable' not in message:
                self.original_stderr.write(message)
        
        def flush(self):
            self.original_stderr.flush()
        
        def __getattr__(self, name):
            # 代理其他属性到原始 stderr
            return getattr(self.original_stderr, name)
    
    # 替换 stderr 以过滤警告
    sys.stderr = FilteredStderr(sys.stderr)

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.config import Config
from src.providers.asr.volcano import VolcanoASRProvider


async def test_asr_auth():
    """测试 ASR 认证"""
    print("=" * 60)
    print("🔐 火山引擎 ASR 认证测试")
    print("=" * 60)
    
    # 加载配置
    config = Config()
    asr_config = {
        'base_url': config.get('asr.base_url', 'wss://openspeech.bytedance.com/api/v3/sauc/bigmodel'),
        'app_id': config.get('asr.app_id', ''),
        'app_key': config.get('asr.app_key', ''),
        'access_key': config.get('asr.access_key', '')
    }
    
    # 显示配置信息（部分隐藏）
    print("\n📋 配置信息：")
    print(f"  base_url: {asr_config['base_url']}")
    print(f"  app_id: {asr_config['app_id']}")
    
    if asr_config['app_key']:
        masked_app_key = asr_config['app_key'][:8] + '...' + asr_config['app_key'][-4:] if len(asr_config['app_key']) > 12 else '***'
        print(f"  app_key: {masked_app_key} ({len(asr_config['app_key'])} 字符)")
    else:
        print(f"  app_key: (未设置)")
    
    if asr_config['access_key']:
        masked_access_key = asr_config['access_key'][:8] + '...' + asr_config['access_key'][-4:] if len(asr_config['access_key']) > 12 else '***'
        print(f"  access_key: {masked_access_key} ({len(asr_config['access_key'])} 字符)")
    else:
        print(f"  access_key: (未设置)")
    
    # 验证配置完整性
    print("\n🔍 验证配置...")
    if not asr_config['access_key'] or not asr_config['access_key'].strip():
        print("❌ 错误: access_key 未设置或为空")
        print("   请检查 config.yml 中的 asr.access_key 配置")
        return False
    
    if not asr_config['app_key'] or not asr_config['app_key'].strip():
        print("❌ 错误: app_key 未设置或为空")
        print("   请检查 config.yml 中的 asr.app_key 配置")
        return False
    
    print("✅ 配置完整性检查通过")
    
    # 初始化 ASR 提供商
    print("\n🚀 初始化 ASR 提供商...")
    provider = VolcanoASRProvider()
    if not provider.initialize(asr_config):
        print("❌ ASR 提供商初始化失败")
        return False
    
    print("✅ ASR 提供商初始化成功")
    
    # 尝试连接
    print("\n🔌 尝试连接到火山引擎 ASR 服务...")
    print("   这可能需要几秒钟...")
    
    try:
        success = await provider._connect()
        if success:
            print("\n" + "=" * 60)
            print("✅ 认证成功！")
            print("=" * 60)
            print("\n你的凭证配置正确，可以正常使用 ASR 服务。")
            
            # 关闭连接
            if provider.conn:
                await provider.conn.close()
            if provider.session and not provider.session.closed:
                await provider.session.close()
            
            return True
        else:
            print("\n" + "=" * 60)
            print("❌ 认证失败")
            print("=" * 60)
            print("\n可能的原因：")
            print("  1. access_key 或 app_key 不正确")
            print("  2. 凭证已过期或被撤销")
            print("  3. 凭证没有访问 ASR 服务的权限")
            print("  4. 服务未开通或账户余额不足")
            print("  5. 可能需要使用 app_id 而不是 app_key（某些情况下）")
            print("\n建议：")
            print("  1. 登录火山引擎控制台检查凭证状态")
            print("  2. 确认服务已开通且有足够余额")
            print("  3. 检查是否需要使用 app_id 而不是 app_key")
            print("  4. 如有需要，重新生成 access_key 和 app_key")
            print("\n注意：")
            print("  - HTTP 401 表示认证失败，通常是凭证问题")
            print("  - 请确认从火山引擎控制台获取的是正确的凭证")
            print("  - 某些情况下可能需要使用 app_id 作为 app_key")
            return False
            
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ 测试过程中发生错误")
        print("=" * 60)
        print(f"\n错误信息: {str(e)}")
        print(f"错误类型: {type(e).__name__}")
        import traceback
        print("\n详细错误信息：")
        traceback.print_exc()
        return False
    finally:
        # 确保清理资源
        try:
            if provider.conn:
                await provider.conn.close()
            if provider.session and not provider.session.closed:
                await provider.session.close()
        except:
            pass


def main():
    """主函数"""
    try:
        result = asyncio.run(test_asr_auth())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 程序错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

