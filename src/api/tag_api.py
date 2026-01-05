"""
标签管理API接口

提供标签的创建、更新、删除、查询等功能
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from src.providers.storage.tag_storage import TagStorageService
from src.core.config import Config
from src.core.logger import get_logger

logger = get_logger("TagAPI")

# 创建API路由器
router = APIRouter(prefix="/api/tags", tags=["标签管理"])

# 全局服务实例（由主应用初始化）
tag_storage: Optional[TagStorageService] = None


def init_tag_service(config: Config):
    """初始化标签服务（由主应用调用）"""
    global tag_storage
    
    try:
        # 从配置中获取数据库路径
        storage_config = config.get('storage', {})
        data_dir = storage_config.get('data_dir', '~/Library/Application Support/MindVoice')
        database = storage_config.get('database', 'database/history.db')
        
        from pathlib import Path
        data_dir_path = Path(data_dir).expanduser()
        db_path = data_dir_path / database
        
        tag_storage = TagStorageService(str(db_path))
        logger.info("[标签API] 服务初始化完成")
    except Exception as e:
        logger.error(f"[标签API] 服务初始化失败: {e}", exc_info=True)
        raise


# ==================== 请求/响应模型 ====================

class CreateTagRequest(BaseModel):
    """创建标签请求"""
    user_id: str = Field(..., description="用户ID")
    tag_name: str = Field(..., max_length=50, description="标签名称")
    color: Optional[str] = Field(None, description="颜色（如 #FF5733）")
    icon: Optional[str] = Field(None, description="图标（emoji或图标名）")


class UpdateTagRequest(BaseModel):
    """更新标签请求"""
    tag_name: Optional[str] = Field(None, max_length=50, description="新标签名称")
    color: Optional[str] = Field(None, description="新颜色")
    icon: Optional[str] = Field(None, description="新图标")


class TagResponse(BaseModel):
    """标签响应"""
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


class AddTagToRecordRequest(BaseModel):
    """给记录添加标签请求"""
    record_id: str = Field(..., description="记录ID")
    tag_id: int = Field(..., description="标签ID")


class UpdateTagOrderRequest(BaseModel):
    """更新标签排序请求"""
    tag_orders: List[dict] = Field(..., description="标签排序列表")


# ==================== API端点 ====================

@router.post("", response_model=TagResponse)
async def create_tag(request: CreateTagRequest):
    """创建标签"""
    if not tag_storage:
        raise HTTPException(status_code=503, detail="标签服务未初始化")
    
    try:
        tag_id = tag_storage.create_tag(
            user_id=request.user_id,
            tag_name=request.tag_name,
            color=request.color,
            icon=request.icon
        )
        
        return TagResponse(
            success=True,
            data={
                'tag_id': tag_id,
                'tag_name': request.tag_name,
                'color': request.color,
                'icon': request.icon
            }
        )
    except Exception as e:
        logger.error(f"[API] 创建标签失败: {e}", exc_info=True)
        return TagResponse(
            success=False,
            error=str(e)
        )


@router.put("/{tag_id}", response_model=TagResponse)
async def update_tag(tag_id: int, request: UpdateTagRequest):
    """更新标签"""
    if not tag_storage:
        raise HTTPException(status_code=503, detail="标签服务未初始化")
    
    try:
        success = tag_storage.update_tag(
            tag_id=tag_id,
            tag_name=request.tag_name,
            color=request.color,
            icon=request.icon
        )
        
        if success:
            return TagResponse(
                success=True,
                data={'tag_id': tag_id}
            )
        else:
            return TagResponse(
                success=False,
                error="标签不存在"
            )
    except Exception as e:
        logger.error(f"[API] 更新标签失败: {e}", exc_info=True)
        return TagResponse(
            success=False,
            error=str(e)
        )


@router.delete("/{tag_id}", response_model=TagResponse)
async def delete_tag(tag_id: int):
    """删除标签"""
    if not tag_storage:
        raise HTTPException(status_code=503, detail="标签服务未初始化")
    
    try:
        success = tag_storage.delete_tag(tag_id)
        
        if success:
            return TagResponse(
                success=True,
                data={'message': '删除成功'}
            )
        else:
            return TagResponse(
                success=False,
                error="标签不存在"
            )
    except Exception as e:
        logger.error(f"[API] 删除标签失败: {e}", exc_info=True)
        return TagResponse(
            success=False,
            error=str(e)
        )


@router.get("/user/{user_id}", response_model=TagResponse)
async def get_user_tags(user_id: str):
    """获取用户的所有标签"""
    if not tag_storage:
        raise HTTPException(status_code=503, detail="标签服务未初始化")
    
    try:
        tags = tag_storage.get_user_tags(user_id)
        
        return TagResponse(
            success=True,
            data={'tags': tags, 'count': len(tags)}
        )
    except Exception as e:
        logger.error(f"[API] 获取用户标签失败: {e}", exc_info=True)
        return TagResponse(
            success=False,
            error=str(e)
        )


@router.post("/record/add", response_model=TagResponse)
async def add_tag_to_record(request: AddTagToRecordRequest):
    """给记录添加标签"""
    if not tag_storage:
        raise HTTPException(status_code=503, detail="标签服务未初始化")
    
    try:
        success = tag_storage.add_tag_to_record(
            record_id=request.record_id,
            tag_id=request.tag_id
        )
        
        if success:
            return TagResponse(
                success=True,
                data={'message': '添加标签成功'}
            )
        else:
            return TagResponse(
                success=False,
                error="标签已存在或记录不存在"
            )
    except Exception as e:
        logger.error(f"[API] 添加标签失败: {e}", exc_info=True)
        return TagResponse(
            success=False,
            error=str(e)
        )


@router.delete("/record/{record_id}/{tag_id}", response_model=TagResponse)
async def remove_tag_from_record(record_id: str, tag_id: int):
    """从记录移除标签"""
    if not tag_storage:
        raise HTTPException(status_code=503, detail="标签服务未初始化")
    
    try:
        success = tag_storage.remove_tag_from_record(record_id, tag_id)
        
        if success:
            return TagResponse(
                success=True,
                data={'message': '移除标签成功'}
            )
        else:
            return TagResponse(
                success=False,
                error="标签关联不存在"
            )
    except Exception as e:
        logger.error(f"[API] 移除标签失败: {e}", exc_info=True)
        return TagResponse(
            success=False,
            error=str(e)
        )


@router.get("/record/{record_id}", response_model=TagResponse)
async def get_record_tags(record_id: str):
    """获取记录的所有标签"""
    if not tag_storage:
        raise HTTPException(status_code=503, detail="标签服务未初始化")
    
    try:
        tags = tag_storage.get_record_tags(record_id)
        
        return TagResponse(
            success=True,
            data={'tags': tags, 'count': len(tags)}
        )
    except Exception as e:
        logger.error(f"[API] 获取记录标签失败: {e}", exc_info=True)
        return TagResponse(
            success=False,
            error=str(e)
        )


@router.get("/query/{tag_id}", response_model=TagResponse)
async def get_records_by_tag(tag_id: int, limit: int = 100, offset: int = 0):
    """按标签查询记录"""
    if not tag_storage:
        raise HTTPException(status_code=503, detail="标签服务未初始化")
    
    try:
        record_ids = tag_storage.get_records_by_tag(tag_id, limit, offset)
        
        return TagResponse(
            success=True,
            data={'record_ids': record_ids, 'count': len(record_ids)}
        )
    except Exception as e:
        logger.error(f"[API] 按标签查询记录失败: {e}", exc_info=True)
        return TagResponse(
            success=False,
            error=str(e)
        )


@router.post("/reorder", response_model=TagResponse)
async def update_tag_order(request: UpdateTagOrderRequest):
    """更新标签排序"""
    if not tag_storage:
        raise HTTPException(status_code=503, detail="标签服务未初始化")
    
    try:
        success = tag_storage.update_tag_order(request.tag_orders)
        
        if success:
            return TagResponse(
                success=True,
                data={'message': '更新排序成功'}
            )
        else:
            return TagResponse(
                success=False,
                error="更新排序失败"
            )
    except Exception as e:
        logger.error(f"[API] 更新标签排序失败: {e}", exc_info=True)
        return TagResponse(
            success=False,
            error=str(e)
        )

