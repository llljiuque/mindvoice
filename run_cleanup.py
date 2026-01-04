#!/usr/bin/env python3
"""
手动清理脚本

直接调用清理服务执行清理任务，无需重启API服务器
"""
import sys
import asyncio
import logging
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.config import Config
from src.services.cleanup_service import CleanupService

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Cleanup")


async def main():
    """执行清理任务"""
    print("=" * 60)
    print("MindVoice 系统清理工具")
    print("=" * 60)
    print()
    
    try:
        # 加载配置
        config = Config()
        logger.info("[清理] 配置已加载")
        
        # 初始化清理服务
        cleanup_service = CleanupService(config._config)
        logger.info("[清理] 清理服务已初始化")
        print()
        
        # 显示清理配置
        print(f"配置信息:")
        print(f"  - 日志保留天数: {cleanup_service.log_retention_days} 天")
        print(f"  - 清理孤儿图片: {'是' if cleanup_service.orphan_images_enabled else '否'}")
        print(f"  - 日志目录: {cleanup_service.logs_dir}")
        print(f"  - 图片目录: {cleanup_service.images_dir}")
        print(f"  - 数据库路径: {cleanup_service.db_path}")
        print()
        
        # 确认执行
        response = input("是否开始清理？(y/N): ").strip().lower()
        if response != 'y':
            print("清理已取消")
            return
        
        print()
        print("开始清理...")
        print("-" * 60)
        
        # 执行清理
        result = await cleanup_service.manual_cleanup(
            clean_logs=True,
            clean_images=True
        )
        
        print()
        print("=" * 60)
        print("清理完成！")
        print("=" * 60)
        
        if result['success']:
            print()
            print("清理结果:")
            print(f"  📝 日志文件:")
            print(f"     - 删除数量: {result['logs']['deleted']} 个")
            print(f"     - 释放空间: {result['logs']['size_freed']:.2f} MB")
            print()
            print(f"  🖼️  图片文件:")
            print(f"     - 删除数量: {result['images']['deleted']} 个")
            print(f"     - 释放空间: {result['images']['size_freed']:.2f} MB")
            print()
            
            total_freed = result['logs']['size_freed'] + result['images']['size_freed']
            total_deleted = result['logs']['deleted'] + result['images']['deleted']
            
            if total_deleted > 0:
                print(f"  ✅ 总计: 删除 {total_deleted} 个文件，释放 {total_freed:.2f} MB 空间")
            else:
                print(f"  ✅ 没有需要清理的文件")
        else:
            print()
            print(f"  ❌ 清理失败: {result.get('error', '未知错误')}")
        
        print()
        
    except Exception as e:
        logger.error(f"[清理] 执行失败: {e}", exc_info=True)
        print()
        print(f"❌ 清理失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

