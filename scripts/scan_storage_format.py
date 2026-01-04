#!/usr/bin/env python3
"""
扫描项目中的存储格式使用情况
检查是否还有旧格式（.voice_assistant, storage.path, data/*）的引用
"""
import sys
from pathlib import Path

# 扫描结果
results = {
    'old_format': [],
    'new_format': [],
    'warnings': []
}

# 扫描所有Python文件
src_dir = Path(__file__).parent.parent / 'src'
for py_file in src_dir.rglob('*.py'):
    try:
        content = py_file.read_text(encoding='utf-8')
        relative_path = py_file.relative_to(src_dir.parent)
        
        # 检查旧格式
        if '.voice_assistant' in content:
            results['old_format'].append(f'{relative_path}: .voice_assistant')
        if "storage.path" in content or "storage['path']" in content or 'storage["path"]' in content:
            results['old_format'].append(f'{relative_path}: storage.path')
        if 'data/images' in content or 'data/knowledge' in content or 'data/database' in content:
            results['old_format'].append(f'{relative_path}: data/* 硬编码')
        
        # 检查新格式
        if 'storage.data_dir' in content or "storage['data_dir']" in content or 'storage["data_dir"]' in content:
            results['new_format'].append(f'{relative_path}: data_dir ✓')
        if 'storage.database' in content or "storage['database']" in content or 'storage["database"]' in content:
            results['new_format'].append(f'{relative_path}: database ✓')
        if 'storage.images' in content or "storage['images']" in content:
            results['new_format'].append(f'{relative_path}: images ✓')
        if 'storage.knowledge' in content or "storage['knowledge']" in content:
            results['new_format'].append(f'{relative_path}: knowledge ✓')
            
    except Exception as e:
        results['warnings'].append(f'{py_file}: 读取失败 ({e})')

print('=' * 60)
print('MindVoice 存储格式扫描报告')
print('=' * 60)
print()

print(f'❌ 发现旧格式引用: {len(results["old_format"])}')
if results['old_format']:
    for item in results['old_format']:
        print(f'  {item}')
else:
    print('  (无)')
print()

print(f'✅ 使用新格式: {len(results["new_format"])}')
if results['new_format']:
    for item in results['new_format'][:15]:  # 只显示前15个
        print(f'  {item}')
    if len(results['new_format']) > 15:
        remaining = len(results['new_format']) - 15
        print(f'  ... 还有 {remaining} 个引用')
else:
    print('  (无)')
print()

if results['warnings']:
    print(f'⚠️  警告: {len(results["warnings"])}')
    for item in results['warnings']:
        print(f'  {item}')
    print()

print('=' * 60)
if len(results['old_format']) == 0:
    print('✅ 扫描完成：所有文件已迁移到新格式！')
    sys.exit(0)
else:
    print('⚠️  警告：仍有文件使用旧格式，需要修复')
    sys.exit(1)

