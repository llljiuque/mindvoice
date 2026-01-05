"""
用户资料API接口 (v1.2.1 重构版)

核心变化：
- 新增完整的用户注册流程
- 注册时自动授权免费会员

提供用户信息管理、设备绑定等功能
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, EmailStr
from src.providers.storage.user_storage import UserStorageService
from src.services.membership_service import MembershipService
from src.core.config import Config
from src.core.logger import get_logger

logger = get_logger("UserAPI")

# 创建API路由器
router = APIRouter(prefix="/api/user", tags=["用户管理"])

# 全局服务实例（由主应用初始化）
user_storage: Optional[UserStorageService] = None
membership_service: Optional[MembershipService] = None


def init_user_service(config: Config):
    """初始化用户服务（由主应用调用）"""
    global user_storage, membership_service
    
    try:
        # 从配置中获取数据库路径
        storage_config = config.get('storage', {})
        data_dir = storage_config.get('data_dir', '~/Library/Application Support/MindVoice')
        database = storage_config.get('database', 'database/history.db')
        
        # 使用与其他数据共享的数据库
        from pathlib import Path
        data_dir_path = Path(data_dir).expanduser()
        db_path = data_dir_path / database
        
        user_storage = UserStorageService(str(db_path))
        membership_service = MembershipService(config)
        logger.info("[用户API] 服务初始化完成 (v1.2.1)")
    except Exception as e:
        logger.error(f"[用户API] 服务初始化失败: {e}", exc_info=True)
        raise


# ==================== 请求/响应模型 ====================

class UserRegisterRequest(BaseModel):
    """用户注册请求"""
    device_id: str = Field(..., description="设备ID")
    machine_id: str = Field(..., description="机器ID")
    platform: str = Field(..., description="平台（darwin/win32/linux）")
    device_name: Optional[str] = Field(None, max_length=100, description="设备名称")
    nickname: Optional[str] = Field("新用户", max_length=50, description="昵称")
    email: Optional[str] = Field(None, description="邮箱")


class UserRegisterResponse(BaseModel):
    """用户注册响应"""
    success: bool
    user_id: Optional[str] = None
    device_id: Optional[str] = None
    membership: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class UserProfileRequest(BaseModel):
    """用户资料请求"""
    device_id: str = Field(..., description="设备ID")
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    email: Optional[str] = Field(None, description="邮箱")
    bio: Optional[str] = Field(None, max_length=500, description="个人简介")
    avatar_url: Optional[str] = Field(None, description="头像URL（相对路径）")


class UserProfileResponse(BaseModel):
    """用户资料响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class BindDeviceRequest(BaseModel):
    """绑定设备请求"""
    user_id: str = Field(..., description="用户ID")
    device_id: str = Field(..., description="设备ID")
    device_name: Optional[str] = Field(None, max_length=100, description="设备名称")


class GenericResponse(BaseModel):
    """通用响应"""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None


# ==================== API端点 ====================

@router.post("/register", response_model=UserRegisterResponse)
async def register_user(request: UserRegisterRequest):
    """用户注册（完整流程）
    
    流程：
    1. 创建用户（users表）
    2. 注册设备（devices表）
    3. 绑定设备（user_devices表）
    4. 授权免费会员（memberships表，user_id为主键）
    
    这是用户首次打开应用时调用的API
    """
    if not user_storage or not membership_service:
        raise HTTPException(status_code=503, detail="用户服务未初始化")
    
    try:
        # 1. 确保设备已注册到devices表（无论是否已绑定用户）
        membership_service.register_device(
            device_id=request.device_id,
            machine_id=request.machine_id,
            platform=request.platform
        )
        logger.info(f"[用户注册] 设备已注册: device_id={request.device_id}")
        
        # 2. 检查设备是否已绑定用户
        existing_user = user_storage.get_user_by_device(request.device_id)
        if existing_user:
            logger.info(f"[用户注册] 设备已绑定用户: device_id={request.device_id}, user_id={existing_user['user_id']}")
            # 返回现有用户信息
            membership = membership_service.get_membership(existing_user['user_id'])
            return UserRegisterResponse(
                success=True,
                user_id=existing_user['user_id'],
                device_id=request.device_id,
                membership=membership
            )
        
        # 3. 创建新用户
        user_id = user_storage.create_user(
            nickname=request.nickname or "新用户",
            email=request.email
        )
        logger.info(f"[用户注册] 用户已创建: user_id={user_id}")
        
        # 4. 绑定设备
        user_storage.bind_device(
            user_id=user_id,
            device_id=request.device_id,
            device_name=request.device_name
        )
        logger.info(f"[用户注册] 设备已绑定: user_id={user_id}, device_id={request.device_id}")
        
        # 5. 授权免费会员
        membership = membership_service.create_membership(
            user_id=user_id,
            tier='free'
        )
        logger.info(f"[用户注册] 免费会员已授权: user_id={user_id}")
        
        return UserRegisterResponse(
            success=True,
            user_id=user_id,
            device_id=request.device_id,
            membership=membership
        )
        
    except Exception as e:
        logger.error(f"[用户注册] 注册失败: {e}", exc_info=True)
        return UserRegisterResponse(
            success=False,
            error=str(e)
        )


@router.post("/profile", response_model=UserProfileResponse)
async def save_user_profile(request: UserProfileRequest):
    """保存用户资料（创建或更新）
    
    如果设备已绑定用户，则更新该用户信息
    如果设备未绑定，则创建新用户并绑定设备，并自动授权免费会员
    """
    if not user_storage or not membership_service:
        raise HTTPException(status_code=503, detail="用户服务未初始化")
    
    try:
        # 检查是否是新用户
        existing_user = user_storage.get_user_by_device(request.device_id)
        is_new_user = existing_user is None
        
        # 创建或更新用户
        user = user_storage.create_or_update_user_by_device(
            device_id=request.device_id,
            nickname=request.nickname,
            email=request.email,
            bio=request.bio,
            avatar_url=request.avatar_url
        )
        
        # 如果是新用户，自动创建免费会员
        if is_new_user and user:
            try:
                membership_service.create_membership(
                    user_id=user['user_id'],
                    tier='free'
                )
                logger.info(f"[用户资料] 已为新用户创建免费会员: user_id={user['user_id']}")
            except Exception as e:
                logger.error(f"[用户资料] 创建会员失败: {e}", exc_info=True)
                # 不中断流程，用户资料已保存成功
        
        return UserProfileResponse(
            success=True,
            data=user
        )
    except Exception as e:
        logger.error(f"[API] 保存用户资料失败: {e}", exc_info=True)
        return UserProfileResponse(
            success=False,
            error=str(e)
        )


@router.get("/profile/{device_id}", response_model=UserProfileResponse)
async def get_user_profile(device_id: str):
    """获取用户资料（通过设备ID）"""
    if not user_storage:
        raise HTTPException(status_code=503, detail="用户服务未初始化")
    
    try:
        user = user_storage.get_user_by_device(device_id)
        
        if not user:
            return UserProfileResponse(
                success=False,
                error="用户资料不存在"
            )
        
        return UserProfileResponse(
            success=True,
            data=user
        )
    except Exception as e:
        logger.error(f"[API] 获取用户资料失败: {e}", exc_info=True)
        return UserProfileResponse(
            success=False,
            error=str(e)
        )


@router.post("/bind-device", response_model=GenericResponse)
async def bind_device(request: BindDeviceRequest):
    """绑定设备到用户"""
    if not user_storage:
        raise HTTPException(status_code=503, detail="用户服务未初始化")
    
    try:
        success = user_storage.bind_device(
            user_id=request.user_id,
            device_id=request.device_id,
            device_name=request.device_name
        )
        
        if success:
            return GenericResponse(
                success=True,
                message="绑定设备成功"
            )
        else:
            return GenericResponse(
                success=False,
                error="绑定失败，用户不存在"
            )
    except Exception as e:
        logger.error(f"[API] 绑定设备失败: {e}", exc_info=True)
        return GenericResponse(
            success=False,
            error=str(e)
        )


@router.delete("/unbind-device/{device_id}", response_model=GenericResponse)
async def unbind_device(device_id: str):
    """解绑设备"""
    if not user_storage:
        raise HTTPException(status_code=503, detail="用户服务未初始化")
    
    try:
        success = user_storage.unbind_device(device_id)
        
        if success:
            return GenericResponse(
                success=True,
                message="解绑设备成功"
            )
        else:
            return GenericResponse(
                success=False,
                error="解绑失败，设备未绑定"
            )
    except Exception as e:
        logger.error(f"[API] 解绑设备失败: {e}", exc_info=True)
        return GenericResponse(
            success=False,
            error=str(e)
        )


@router.get("/devices/{user_id}")
async def get_user_devices(user_id: str):
    """获取用户的所有设备"""
    if not user_storage:
        raise HTTPException(status_code=503, detail="用户服务未初始化")
    
    try:
        devices = user_storage.get_user_devices(user_id)
        
        return {
            "success": True,
            "data": devices
        }
    except Exception as e:
        logger.error(f"[API] 获取用户设备失败: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@router.delete("/profile/{user_id}", response_model=GenericResponse)
async def delete_user_profile(user_id: str):
    """删除用户资料（级联删除绑定的设备）"""
    if not user_storage:
        raise HTTPException(status_code=503, detail="用户服务未初始化")
    
    try:
        success = user_storage.delete_user(user_id)
        
        if success:
            return GenericResponse(
                success=True,
                message="删除用户成功"
            )
        else:
            return GenericResponse(
                success=False,
                error="删除失败，用户不存在"
            )
    except Exception as e:
        logger.error(f"[API] 删除用户失败: {e}", exc_info=True)
        return GenericResponse(
            success=False,
            error=str(e)
        )


@router.post("/login/{device_id}", response_model=UserProfileResponse)
async def login(device_id: str):
    """用户登录（通过设备ID）
    
    自动更新登录次数和最后登录时间
    如果设备未绑定用户，返回错误
    """
    if not user_storage:
        raise HTTPException(status_code=503, detail="用户服务未初始化")
    
    try:
        user = user_storage.login_by_device(device_id)
        
        if not user:
            return UserProfileResponse(
                success=False,
                error="设备未绑定用户，请先创建用户资料"
            )
        
        return UserProfileResponse(
            success=True,
            data=user
        )
    except Exception as e:
        logger.error(f"[API] 用户登录失败: {e}", exc_info=True)
        return UserProfileResponse(
            success=False,
            error=str(e)
        )

