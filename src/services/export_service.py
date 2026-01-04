"""
Markdown 导出服务
纯 Python 实现，零外部依赖
"""
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
import json
import io
import zipfile


class MarkdownExportService:
    """Markdown 导出服务"""
    
    @staticmethod
    def export_record_to_markdown(record: Dict[str, Any]) -> str:
        """
        将 record 转换为 Markdown 格式
        
        Args:
            record: 数据库记录，包含 text, metadata, created_at 等字段
            
        Returns:
            Markdown 格式的字符串
        """
        lines = []
        metadata = record.get('metadata', {})
        
        # 如果 metadata 是字符串，尝试解析
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        blocks = metadata.get('blocks', [])
        
        # 1. 添加 YAML Front Matter（笔记元信息）
        note_info_block = next((b for b in blocks if b.get('type') == 'note-info'), None)
        if note_info_block and note_info_block.get('noteInfo'):
            lines.extend(MarkdownExportService._format_note_info(note_info_block['noteInfo']))
        
        # 添加导出信息
        lines.append(f"*导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append('')
        lines.append('---')
        lines.append('')
        
        # 2. 遍历 blocks，转换内容
        for block in blocks:
            block_type = block.get('type')
            
            # 跳过特殊块
            if block_type == 'note-info' or block.get('isBufferBlock'):
                continue
            
            # 处理小结块
            if block.get('isSummary'):
                lines.extend(MarkdownExportService._format_summary_block(block))
                continue
            
            # 处理其他类型
            formatted = MarkdownExportService._format_block(block)
            if formatted:
                lines.extend(formatted)
        
        return '\n'.join(lines)
    
    @staticmethod
    def _format_note_info(note_info: Dict[str, Any]) -> List[str]:
        """格式化笔记信息为 YAML Front Matter"""
        lines = ['---']
        
        if note_info.get('title'):
            # 转义双引号
            title = note_info['title'].replace('"', '\\"')
            lines.append(f'title: "{title}"')
        if note_info.get('type'):
            lines.append(f"type: {note_info['type']}")
        if note_info.get('relatedPeople'):
            lines.append(f"people: {note_info['relatedPeople']}")
        if note_info.get('location'):
            lines.append(f"location: {note_info['location']}")
        if note_info.get('startTime'):
            lines.append(f"start_time: {note_info['startTime']}")
        if note_info.get('endTime'):
            lines.append(f"end_time: {note_info['endTime']}")
        
        lines.append('---')
        lines.append('')
        
        return lines
    
    @staticmethod
    def _format_summary_block(block: Dict[str, Any]) -> List[str]:
        """格式化小结块"""
        lines = ['---', '']
        lines.append('> **📝 小结**')
        lines.append('>')
        
        content = block.get('content', '')
        for line in content.split('\n'):
            lines.append(f"> {line}")
        
        lines.append('')
        lines.append('---')
        lines.append('')
        
        return lines
    
    @staticmethod
    def _format_block(block: Dict[str, Any]) -> List[str]:
        """格式化普通块"""
        block_type = block.get('type')
        content = block.get('content', '').strip()
        
        if not content and block_type != 'image':
            return []
        
        lines = []
        
        if block_type == 'paragraph':
            lines.append(content)
            lines.append('')
        
        elif block_type == 'h1':
            lines.append(f"# {content}")
            lines.append('')
        
        elif block_type == 'h2':
            lines.append(f"## {content}")
            lines.append('')
        
        elif block_type == 'h3':
            lines.append(f"### {content}")
            lines.append('')
        
        elif block_type == 'bulleted-list':
            lines.append(f"- {content}")
        
        elif block_type == 'numbered-list':
            lines.append(f"1. {content}")
        
        elif block_type == 'code':
            lines.append('```')
            lines.append(content)
            lines.append('```')
            lines.append('')
        
        elif block_type == 'image':
            image_url = block.get('imageUrl', '')
            image_caption = block.get('imageCaption', '图片')
            
            # 如果是相对路径，转换为完整的 API URL
            if image_url and not image_url.startswith('http'):
                # 转换为 API 服务器的完整 URL
                image_url = f"http://127.0.0.1:8765/api/{image_url}"
            
            lines.append(f"![{image_caption}]({image_url})")
            if image_caption:
                lines.append(f"*{image_caption}*")
            lines.append('')
        
        return lines
    
    @staticmethod
    def export_record_to_zip(record: Dict[str, Any], data_dir: Path) -> bytes:
        """
        将 record 打包为 ZIP 文件（包含 Markdown 和图片）
        
        Args:
            record: 数据库记录
            data_dir: 数据根目录（用于查找图片文件）
            
        Returns:
            ZIP 文件的字节流
        """
        # 1. 生成 Markdown 内容（使用相对路径）
        markdown_content = MarkdownExportService._export_with_relative_paths(record)
        
        # 2. 收集所有图片路径
        image_paths = MarkdownExportService._extract_image_paths(record)
        
        # 3. 创建 ZIP 文件
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # 添加 Markdown 文件
            zip_file.writestr('笔记.md', markdown_content.encode('utf-8'))
            
            # 添加图片文件
            for image_rel_path in image_paths:
                # 构建图片的完整路径
                image_full_path = data_dir / image_rel_path
                
                if image_full_path.exists():
                    # 读取图片并添加到 ZIP
                    with open(image_full_path, 'rb') as img_file:
                        zip_file.writestr(image_rel_path, img_file.read())
                else:
                    print(f"[Export] 警告: 图片不存在 {image_full_path}")
        
        zip_buffer.seek(0)
        return zip_buffer.getvalue()
    
    @staticmethod
    def _export_with_relative_paths(record: Dict[str, Any]) -> str:
        """
        导出 Markdown，图片使用相对路径（用于 ZIP 打包）
        """
        lines = []
        metadata = record.get('metadata', {})
        
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        blocks = metadata.get('blocks', [])
        
        # 添加笔记信息
        note_info_block = next((b for b in blocks if b.get('type') == 'note-info'), None)
        if note_info_block and note_info_block.get('noteInfo'):
            lines.extend(MarkdownExportService._format_note_info(note_info_block['noteInfo']))
        
        # 添加导出信息
        lines.append(f"*导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append('')
        lines.append('---')
        lines.append('')
        
        # 遍历 blocks
        for block in blocks:
            block_type = block.get('type')
            
            if block_type == 'note-info' or block.get('isBufferBlock'):
                continue
            
            if block.get('isSummary'):
                lines.extend(MarkdownExportService._format_summary_block(block))
                continue
            
            # 特殊处理图片块：使用相对路径
            if block_type == 'image':
                image_url = block.get('imageUrl', '')
                image_caption = block.get('imageCaption', '图片')
                
                # 保持相对路径不变
                lines.append(f"![{image_caption}]({image_url})")
                if image_caption:
                    lines.append(f"*{image_caption}*")
                lines.append('')
            else:
                formatted = MarkdownExportService._format_block(block)
                if formatted:
                    lines.extend(formatted)
        
        return '\n'.join(lines)
    
    @staticmethod
    def _extract_image_paths(record: Dict[str, Any]) -> List[str]:
        """
        从记录中提取所有图片路径
        
        Returns:
            图片相对路径列表，如 ['images/xxx.png', 'images/yyy.png']
        """
        metadata = record.get('metadata', {})
        
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                return []
        
        blocks = metadata.get('blocks', [])
        image_paths = []
        
        for block in blocks:
            if block.get('type') == 'image' and block.get('imageUrl'):
                image_url = block['imageUrl']
                # 只处理相对路径
                if not image_url.startswith('http'):
                    image_paths.append(image_url)
        
        return image_paths

