#!/usr/bin/env python3
"""
ASR 配置助手脚本
用于交互式设置火山引擎 ASR 配置（保存到 config.yml）
"""
import yaml
from pathlib import Path


def get_config_path():
    """获取配置文件路径（项目根目录的 config.yml）"""
    project_root = Path(__file__).parent
    return project_root / 'config.yml'


def load_config():
    """加载配置文件"""
    config_path = get_config_path()
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"❌ 读取配置文件失败: {e}")
            return None
    return None


def save_config(config):
    """保存配置文件（保存到 config.yml）"""
    config_path = get_config_path()
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, 
                     allow_unicode=True, sort_keys=False)
        print(f"✅ 配置已保存到: {config_path}")
        print(f"⚠️  注意：此文件包含敏感信息，请勿提交到版本控制系统")
        return True
    except Exception as e:
        print(f"❌ 保存配置文件失败: {e}")
        return False


def get_default_config():
    """获取默认配置"""
    config_dir = Path.home() / '.voice_assistant'
    return {
        'asr': {
            'base_url': 'wss://openspeech.bytedance.com/api/v3/sauc/bigmodel',
            'app_id': '',
            'app_key': '',
            'access_key': '',
            'language': 'zh-CN'
        },
        'storage': {
            'path': str(config_dir / 'history.db')
        },
        'audio': {
            'format': 'WAV',
            'channels': 1,
            'rate': 16000,
            'chunk': 1024
        },
        'ui': {
            'theme': 'light',
            'position': {'x': 100, 'y': 100},
            'size': {'width': 500, 'height': 400}
        }
    }


def setup_volcano_asr():
    """设置火山引擎 ASR"""
    print("\n📝 配置火山引擎 ASR")
    print("=" * 50)
    print("提示：如果不知道这些信息，请访问火山引擎控制台获取")
    print("=" * 50)
    
    app_id = input("请输入 app_id: ").strip()
    app_key = input("请输入 app_key: ").strip()
    access_key = input("请输入 access_key: ").strip()
    
    if not app_id or not access_key:
        print("❌ app_id 和 access_key 不能为空")
        return None
    
    if not app_key:
        app_key = app_id  # 如果未输入 app_key，使用 app_id
    
    return {
        'base_url': 'wss://openspeech.bytedance.com/api/v3/sauc/bigmodel',
        'app_id': app_id,
        'app_key': app_key,
        'access_key': access_key
    }


def select_language():
    """选择语言"""
    print("\n请选择识别语言：")
    print("1. 中文 (zh-CN)")
    print("2. 英语 (en-US)")
    
    choice = input("\n请输入选项 (1/2，默认1): ").strip() or '1'
    
    if choice == '1':
        return 'zh-CN'
    elif choice == '2':
        return 'en-US'
    else:
        return 'zh-CN'


def main():
    """主函数"""
    print("=" * 50)
    print("🎤 macOS 语音桌面助手 - ASR 配置助手")
    print("=" * 50)
    print("⚠️  配置将保存到项目根目录的 config.yml")
    print("⚠️  此文件包含敏感信息，已添加到 .gitignore")
    print("=" * 50)
    
    # 加载现有配置
    config = load_config()
    if config is None:
        print("\n📄 未找到配置文件，将创建新配置")
        config = get_default_config()
    else:
        print(f"\n📄 已加载现有配置: {get_config_path()}")
    
    # 显示当前配置
    if config and 'asr' in config:
        current_language = config['asr'].get('language', 'zh-CN')
        print(f"当前语言: {current_language}")
        
        # 显示已配置的令牌（部分隐藏）
        if config['asr'].get('access_key'):
            masked_key = config['asr']['access_key'][:8] + '...' if len(config['asr']['access_key']) > 8 else '***'
            print(f"已配置火山引擎令牌: {masked_key}")
    
    # 设置火山引擎配置
    volcano_config = setup_volcano_asr()
    if volcano_config is None:
        print("❌ 配置取消")
        return
    
    # 选择语言
    language = select_language()
    
    # 更新配置
    config['asr'] = {
        **volcano_config,
        'language': language
    }
    
    # 保存配置
    print("\n" + "=" * 50)
    print("配置摘要：")
    print(f"  app_id: {volcano_config.get('app_id', '')}")
    print(f"  access_key: {'*' * len(volcano_config.get('access_key', ''))}")
    print(f"  语言: {language}")
    print("=" * 50)
    
    confirm = input("\n确认保存配置到 config.yml？(y/n): ").strip().lower()
    if confirm == 'y' or confirm == 'yes':
        if save_config(config):
            print("\n✅ 配置完成！")
            print("\n下一步：")
            print("  运行应用: ./quick_start.sh")
            print("  或: python api_server.py")
        else:
            print("\n❌ 配置保存失败")
    else:
        print("\n❌ 配置已取消")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ 配置已取消")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")