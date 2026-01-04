"""
跨平台数据目录工具
自动检测操作系统并返回合适的默认数据目录
"""
import os
import sys
from pathlib import Path


def get_default_data_dir(app_name: str = "MindVoice") -> str:
    """获取跨平台的默认数据目录
    
    Args:
        app_name: 应用名称
    
    Returns:
        适合当前平台的数据目录路径（字符串，包含 ~）
    
    平台规范：
    - macOS: ~/Library/Application Support/AppName
    - Linux: ~/.local/share/AppName
    - Windows: %APPDATA%/AppName (通常是 C:/Users/username/AppData/Roaming/AppName)
    - iOS: ~/Documents/AppName
    - Android: /data/data/com.mindvoice.app/files/AppName (需要包名)
    """
    system = sys.platform
    
    if system == "darwin":  # macOS
        return f"~/Library/Application Support/{app_name}"
    elif system.startswith("linux"):  # Linux (包括 Android)
        # 检测是否是 Android
        if os.path.exists('/system/build.prop'):  # Android 特征文件
            # Android: 使用应用私有目录
            # 注意：实际 Android 应用应该使用 Context.getFilesDir()
            return f"/data/data/com.mindvoice.app/files/{app_name}"
        else:
            # 标准 Linux
            return f"~/.local/share/{app_name}"
    elif system == "win32":  # Windows
        # Windows 上返回 APPDATA 环境变量，使用正斜杠
        appdata = os.getenv('APPDATA')
        if appdata:
            # 转换为正斜杠，避免转义问题
            return os.path.join(appdata, app_name).replace('\\', '/')
        else:
            # 降级方案
            return f"~/{app_name}"
    elif system == "ios":  # iOS (如果使用 Python for iOS)
        return f"~/Documents/{app_name}"
    else:
        # 其他平台：使用用户主目录下的隐藏文件夹
        return f"~/.{app_name.lower()}"


def expand_data_dir(data_dir: str) -> Path:
    """展开数据目录路径
    
    Args:
        data_dir: 数据目录路径（可能包含 ~ 或环境变量）
    
    Returns:
        展开后的 Path 对象
    """
    # 1. 展开环境变量（Windows）
    expanded = os.path.expandvars(data_dir)
    
    # 2. 展开用户目录（~）
    expanded = os.path.expanduser(expanded)
    
    # 3. 转换为 Path 对象
    return Path(expanded)


def get_platform_info() -> dict:
    """获取平台信息
    
    Returns:
        包含平台信息的字典
    """
    return {
        "system": sys.platform,
        "python_version": sys.version,
        "default_data_dir": get_default_data_dir(),
    }


if __name__ == "__main__":
    # 测试
    print("跨平台数据目录检测")
    print("=" * 50)
    
    info = get_platform_info()
    print(f"操作系统: {info['system']}")
    print(f"Python 版本: {info['python_version']}")
    print(f"默认数据目录: {info['default_data_dir']}")
    print(f"展开后: {expand_data_dir(info['default_data_dir'])}")
    
    print("\n各平台默认路径：")
    print(f"  macOS: ~/Library/Application Support/MindVoice")
    print(f"  Linux: ~/.local/share/MindVoice")
    print(f"  Windows: %APPDATA%/MindVoice")
    print(f"  iOS: ~/Documents/MindVoice")
    print(f"  Android: /data/data/com.mindvoice.app/files/MindVoice")

