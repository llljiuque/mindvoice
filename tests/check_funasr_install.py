#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查funasr安装情况
"""
import sys
import os

# 设置编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("=" * 60)
print("检查FunASR安装情况")
print("=" * 60)

print(f"\nPython可执行文件: {sys.executable}")
print(f"Python版本: {sys.version}")

# 检查torch（funasr的必需依赖）
print("\n1. 检查torch包（funasr的必需依赖）...")
try:
    import torch
    print(f"   ✓ torch导入成功")
    print(f"   版本: {torch.__version__}")
except (ImportError, OSError) as e:
    print(f"   ✗ torch导入失败: {e}")
    print(f"   请运行: pip install torch>=2.0.0")
    print(f"   注意：funasr需要torch作为依赖")
    print(f"   如果出现DLL错误，可能需要：")
    print(f"   1. 安装Visual C++ Redistributable")
    print(f"   2. 重新安装torch: pip uninstall torch && pip install torch")
    print(f"   3. 或使用CPU版本: pip install torch --index-url https://download.pytorch.org/whl/cpu")

# 检查torchaudio（funasr的必需依赖）
print("\n1.5. 检查torchaudio包（funasr的必需依赖）...")
try:
    import torchaudio
    print(f"   ✓ torchaudio导入成功")
    print(f"   版本: {torchaudio.__version__}")
except (ImportError, OSError) as e:
    print(f"   ✗ torchaudio导入失败: {e}")
    print(f"   请运行: pip install torchaudio>=2.0.0")
    print(f"   注意：funasr需要torchaudio作为依赖")
    print(f"   如果使用CPU版本的torch，也使用CPU版本的torchaudio:")
    print(f"   pip install torchaudio --index-url https://download.pytorch.org/whl/cpu")

# 检查funasr
print("\n2. 检查funasr包...")
try:
    import funasr
    print(f"   ✓ funasr导入成功")
    print(f"   包位置: {funasr.__file__}")
    
    # 尝试导入AutoModel
    try:
        from funasr import AutoModel
        print(f"   ✓ AutoModel导入成功")
    except ImportError as e:
        print(f"   ✗ AutoModel导入失败: {e}")
        print(f"   尝试其他导入方式...")
        # 尝试其他可能的导入路径
        try:
            from funasr.auto import AutoModel
            print(f"   ✓ 从funasr.auto导入AutoModel成功")
        except:
            pass
except (ImportError, OSError) as e:
    print(f"   ✗ funasr导入失败: {e}")
    print(f"   请运行: pip install funasr>=1.0.0")
    print(f"   注意：如果提示缺少torch或DLL错误，请先安装: pip install torch>=2.0.0")
    print(f"   如果torch DLL加载失败，尝试CPU版本: pip install torch --index-url https://download.pytorch.org/whl/cpu")

# 检查modelscope
print("\n3. 检查modelscope包...")
try:
    from modelscope import snapshot_download
    print(f"   ✓ modelscope导入成功")
except ImportError as e:
    print(f"   ✗ modelscope导入失败: {e}")
    print(f"   请运行: pip install modelscope>=1.9.0")

# 检查其他依赖
print("\n4. 检查其他依赖...")
deps = {
    'soundfile': 'soundfile>=0.12.0',
    'scipy': 'scipy>=1.10.0',
    'numpy': 'numpy>=1.24.0'
}

for dep, requirement in deps.items():
    try:
        __import__(dep)
        print(f"   ✓ {dep}已安装")
    except ImportError:
        print(f"   ✗ {dep}未安装 (需要: {requirement})")

print("\n" + "=" * 60)
print("检查完成")
