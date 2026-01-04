#!/usr/bin/env python3
"""
配置文件初始化工具
自动检测操作系统并生成适合的 config.yml
"""
import sys
import os
from pathlib import Path
import shutil

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.platform_paths import get_default_data_dir, get_platform_info


def init_config():
    """初始化配置文件"""
    project_root = Path(__file__).parent.parent
    config_file = project_root / "config.yml"
    example_file = project_root / "config.yml.example"
    
    print("=" * 60)
    print("MindVoice 配置初始化工具")
    print("=" * 60)
    print()
    
    # 显示平台信息
    platform_info = get_platform_info()
    print(f"检测到操作系统: {platform_info['system']}")
    print(f"推荐数据目录: {platform_info['default_data_dir']}")
    print()
    
    # 检查 config.yml 是否已存在
    if config_file.exists():
        print("⚠️  config.yml 已存在")
        response = input("是否覆盖？(yes/NO): ").strip().lower()
        if response != "yes":
            print("❌ 已取消")
            return
        print()
    
    # 检查 config.yml.example 是否存在
    if not example_file.exists():
        print("❌ 错误: config.yml.example 不存在")
        return
    
    # 读取示例配置
    print("📄 读取配置模板...")
    with open(example_file, 'r', encoding='utf-8') as f:
        config_content = f.read()
    
    # 获取推荐的数据目录
    default_data_dir = get_default_data_dir()
    
    # 替换 data_dir（保留注释）
    if sys.platform == "darwin":
        # macOS: 使用默认路径
        print(f"✅ 使用 macOS 默认路径: {default_data_dir}")
    elif sys.platform.startswith("linux"):
        # Linux: 替换为 Linux 路径
        print(f"✅ 使用 Linux 默认路径: {default_data_dir}")
        config_content = config_content.replace(
            "data_dir: ~/Library/Application Support/MindVoice",
            f"data_dir: {default_data_dir}"
        )
    elif sys.platform == "win32":
        # Windows: 替换为 Windows 路径
        print(f"✅ 使用 Windows 默认路径: {default_data_dir}")
        config_content = config_content.replace(
            "data_dir: ~/Library/Application Support/MindVoice",
            f"data_dir: {default_data_dir}"
        )
    else:
        # 其他平台：使用简化路径
        simple_path = "~/MindVoice"
        print(f"✅ 使用通用路径: {simple_path}")
        config_content = config_content.replace(
            "data_dir: ~/Library/Application Support/MindVoice",
            f"data_dir: {simple_path}"
        )
    
    # 写入配置文件
    print(f"💾 生成配置文件: {config_file}")
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    print()
    print("=" * 60)
    print("✅ 配置文件已生成")
    print("=" * 60)
    print()
    print("⚠️  重要提示:")
    print("1. 请编辑 config.yml 填入以下配置:")
    print("   - ASR 配置（火山引擎）: app_id, app_key, access_key")
    print("   - LLM 配置: api_key, base_url, model")
    print()
    print("2. 数据目录已自动设置为:")
    print(f"   {default_data_dir}")
    print()
    print("3. 启动系统:")
    print("   ./quick_start.sh")
    print()


if __name__ == "__main__":
    try:
        init_config()
    except KeyboardInterrupt:
        print("\n\n❌ 用户取消")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)

