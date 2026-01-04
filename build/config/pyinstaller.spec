# -*- mode: python ; coding: utf-8 -*-
"""
MindVoice Python Backend Build Specification
用于 PyInstaller 打包 Python 后端为独立可执行文件

作者：深圳王哥 & AI
日期：2026-01-04
版本：1.0.0
"""

import sys
from pathlib import Path

# 项目路径
project_root = Path('.').absolute()
block_cipher = None

# 需要额外包含的数据文件
datas = [
    (str(project_root / 'config.yml.example'), '.'),
]

# 需要额外包含的二进制文件
binaries = []

# 隐藏导入（动态导入的模块需要显式声明）
hiddenimports = [
    # LLM 相关
    'litellm',
    'litellm.llms',
    'litellm.llms.openai',
    'litellm.llms.anthropic',
    'litellm.integrations',
    
    # 知识库相关
    'chromadb',
    'chromadb.config',
    'chromadb.api',
    'sentence_transformers',
    'sentence_transformers.models',
    
    # ASR 相关
    'sounddevice',
    'webrtcvad',
    
    # API 相关
    'fastapi',
    'fastapi.responses',
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.protocols',
    'websockets',
    'aiohttp',
    
    # 工具库
    'numpy',
    'yaml',
    'pydantic',
    'pydantic.fields',
    'pydantic_core',
]

# 分析
a = Analysis(
    [str(project_root / 'api_server.py')],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的模块以减小体积
        'matplotlib',
        'PIL',
        'tkinter',
        'PyQt5',
        'pandas',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 去重
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 可执行文件
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='mindvoice-api',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # 使用 UPX 压缩
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 保留控制台输出（方便调试）
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

