"""
FastAPI服务器 - 提供HTTP和WebSocket API
独立的后端服务，不依赖任何前端框架
"""
import asyncio
import logging
import sys
import os
from pathlib import Path
from typing import Set, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import Config
from src.core.base import RecordingState
from src.services.voice_service import VoiceService
from src.utils.audio_recorder import SoundDeviceRecorder

logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="语音桌面助手 API",
    version="1.0.0",
    description="独立的后端API服务，支持任何前端框架"
)

# 配置CORS（允许任何前端访问，便于后续更换前端框架）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境可以限制为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局服务实例
voice_service: Optional[VoiceService] = None
config: Optional[Config] = None
recorder: Optional[SoundDeviceRecorder] = None

# WebSocket连接管理
active_connections: Set[WebSocket] = set()


# ==================== API响应模型 ====================

class StatusResponse(BaseModel):
    """状态响应模型"""
    state: str
    current_text: str


class StartRecordingResponse(BaseModel):
    """开始录音响应"""
    success: bool
    message: str


class StopRecordingResponse(BaseModel):
    """停止录音响应"""
    success: bool
    final_text: Optional[str] = None
    message: str


class SyncEditRequest(BaseModel):
    """同步用户编辑请求"""
    text: str


class SyncEditResponse(BaseModel):
    """同步用户编辑响应"""
    success: bool
    message: str


class RecordItem(BaseModel):
    """记录项模型"""
    id: str
    text: str
    metadata: dict
    created_at: str


class ListRecordsResponse(BaseModel):
    """列出记录响应"""
    success: bool
    records: list[RecordItem]
    total: int
    limit: int
    offset: int


# ==================== WebSocket广播函数 ====================

def broadcast_text(text: str):
    """向所有WebSocket连接广播文本更新"""
    if active_connections:
        message = {"type": "text_update", "text": text}
        disconnected = set()
        for connection in active_connections:
            try:
                asyncio.create_task(connection.send_json(message))
            except Exception as e:
                logger.warning(f"发送WebSocket消息失败: {e}")
                disconnected.add(connection)
        
        active_connections.difference_update(disconnected)


def broadcast_state(state: str):
    """向所有WebSocket连接广播状态变化"""
    if active_connections:
        message = {"type": "state_change", "state": state}
        disconnected = set()
        for connection in active_connections:
            try:
                asyncio.create_task(connection.send_json(message))
            except Exception as e:
                logger.warning(f"发送WebSocket状态失败: {e}")
                disconnected.add(connection)
        
        active_connections.difference_update(disconnected)


def broadcast_error(error_type: str, message: str):
    """向所有WebSocket连接广播错误"""
    if active_connections:
        error_msg = {"type": "error", "error_type": error_type, "message": message}
        disconnected = set()
        for connection in active_connections:
            try:
                asyncio.create_task(connection.send_json(error_msg))
            except Exception as e:
                logger.warning(f"发送WebSocket错误失败: {e}")
                disconnected.add(connection)
        
        active_connections.difference_update(disconnected)


# ==================== 服务初始化 ====================

def setup_voice_service():
    """初始化语音服务"""
    global voice_service, config, recorder
    
    logger.info("[API] 初始化语音服务...")
    
    try:
        # 加载配置
        config = Config()
        
        # 初始化录音器
        recorder = SoundDeviceRecorder(
            rate=config.get('audio.rate', 16000),
            channels=config.get('audio.channels', 1),
            chunk=config.get('audio.chunk', 1024)
        )
        
        # 初始化语音服务
        voice_service = VoiceService(config)
        voice_service.set_recorder(recorder)
        
        # 设置回调 - 通过WebSocket广播
        voice_service.set_on_text_callback(lambda text: broadcast_text(text))
        voice_service.set_on_state_change_callback(
            lambda state: broadcast_state(state.value)
        )
        voice_service.set_on_error_callback(
            lambda error_type, msg: broadcast_error(error_type, msg)
        )
        
        logger.info("[API] 语音服务初始化完成")
    except Exception as e:
        logger.error(f"[API] 语音服务初始化失败: {e}", exc_info=True)
        raise


def setup_logging():
    """配置日志"""
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format=log_format,
        datefmt=date_format,
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    # 设置第三方库日志级别
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    logger.info(f"[API] 日志系统已初始化，日志级别: {log_level}")


# ==================== 生命周期事件 ====================

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    setup_logging()
    setup_voice_service()


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    global voice_service, recorder
    logger.info("[API] 正在关闭服务...")
    
    if voice_service:
        try:
            voice_service.cleanup()
        except Exception as e:
            logger.error(f"清理语音服务失败: {e}")
    
    if recorder:
        try:
            recorder.cleanup()
        except Exception as e:
            logger.error(f"清理录音器失败: {e}")
    
    logger.info("[API] 服务已关闭")


# ==================== HTTP REST API ====================

@app.get("/")
async def root():
    """根路径 - API信息"""
    return {
        "name": "语音桌面助手 API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "status": "/api/status",
            "start": "/api/recording/start",
            "pause": "/api/recording/pause",
            "resume": "/api/recording/resume",
            "stop": "/api/recording/stop",
            "list_records": "/api/records",
            "get_record": "/api/records/{record_id}",
            "delete_record": "/api/records/{record_id}",
            "websocket": "/ws"
        }
    }


@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """获取当前状态"""
    if not voice_service:
        raise HTTPException(status_code=503, detail="语音服务未初始化")
    
    state = voice_service.get_state()
    # 尝试获取当前文本（如果服务有存储）
    current_text = getattr(voice_service, '_current_text', '')
    
    return StatusResponse(
        state=state.value,
        current_text=current_text
    )


@app.post("/api/recording/start", response_model=StartRecordingResponse)
async def start_recording():
    """开始录音"""
    if not voice_service:
        raise HTTPException(status_code=503, detail="语音服务未初始化")
    
    try:
        success = voice_service.start_recording()
        if success:
            return StartRecordingResponse(
                success=True,
                message="录音已开始"
            )
        else:
            return StartRecordingResponse(
                success=False,
                message="启动录音失败，请检查配置和权限"
            )
    except Exception as e:
        logger.error(f"启动录音失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/recording/pause", response_model=StartRecordingResponse)
async def pause_recording():
    """暂停录音"""
    if not voice_service:
        raise HTTPException(status_code=503, detail="语音服务未初始化")
    
    try:
        success = voice_service.pause_recording()
        if success:
            return StartRecordingResponse(
                success=True,
                message="录音已暂停"
            )
        else:
            return StartRecordingResponse(
                success=False,
                message="暂停录音失败"
            )
    except Exception as e:
        logger.error(f"暂停录音失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/recording/resume", response_model=StartRecordingResponse)
async def resume_recording():
    """恢复录音"""
    if not voice_service:
        raise HTTPException(status_code=503, detail="语音服务未初始化")
    
    try:
        success = voice_service.resume_recording()
        if success:
            return StartRecordingResponse(
                success=True,
                message="录音已恢复"
            )
        else:
            return StartRecordingResponse(
                success=False,
                message="恢复录音失败"
            )
    except Exception as e:
        logger.error(f"恢复录音失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/recording/stop", response_model=StopRecordingResponse)
async def stop_recording():
    """停止录音"""
    if not voice_service:
        raise HTTPException(status_code=503, detail="语音服务未初始化")
    
    try:
        # 停止录音，获取ASR最终文本
        final_asr_text = voice_service.stop_recording()
        
        # 注意：这里返回的是ASR的最终文本
        # 如果前端有用户编辑版本，前端会在停止时同步用户编辑版本
        # 后端会保存ASR原始版本，用户编辑版本通过sync-edit接口保存
        return StopRecordingResponse(
            success=True,
            final_text=final_asr_text,
            message="录音已停止"
        )
    except Exception as e:
        logger.error(f"停止录音失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/recording/sync-edit", response_model=SyncEditResponse)
async def sync_user_edit(request: SyncEditRequest):
    """同步用户编辑的文本到当前会话记录"""
    if not voice_service:
        raise HTTPException(status_code=503, detail="语音服务未初始化")
    
    try:
        # 获取当前会话ID
        session_id = getattr(voice_service, '_current_session_id', None)
        if not session_id:
            return SyncEditResponse(
                success=False,
                message="当前没有活动的录音会话"
            )
        
        # 更新会话记录的用户编辑版本
        if voice_service.storage_provider:
            metadata = {
                'language': voice_service.config.get('asr.language', 'zh-CN'),
                'provider': 'volcano',
                'session_id': session_id,
                'is_session': True,
                'user_edited': True,  # 标记为用户编辑版本
                'updated_at': voice_service._get_timestamp()
            }
            
            # 更新记录
            if hasattr(voice_service.storage_provider, 'update_record'):
                success = voice_service.storage_provider.update_record(
                    session_id, 
                    request.text, 
                    metadata
                )
                if success:
                    logger.info(f"[API] 用户编辑已同步到会话记录: {session_id}")
                    return SyncEditResponse(
                        success=True,
                        message="用户编辑已同步"
                    )
        
        return SyncEditResponse(
            success=False,
            message="同步失败"
        )
    except Exception as e:
        logger.error(f"同步用户编辑失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/records", response_model=ListRecordsResponse)
async def list_records(limit: int = 50, offset: int = 0):
    """列出历史记录"""
    if not voice_service or not voice_service.storage_provider:
        raise HTTPException(status_code=503, detail="存储服务未初始化")
    
    try:
        records = voice_service.storage_provider.list_records(limit=limit, offset=offset)
        # 计算总数（简化实现，实际可以优化）
        all_records = voice_service.storage_provider.list_records(limit=10000, offset=0)
        total = len(all_records)
        
        record_items = [
            RecordItem(
                id=r['id'],
                text=r['text'],
                metadata=r.get('metadata', {}),
                created_at=r.get('created_at', '')
            )
            for r in records
        ]
        
        return ListRecordsResponse(
            success=True,
            records=record_items,
            total=total,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        logger.error(f"列出记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/records/{record_id}", response_model=RecordItem)
async def get_record(record_id: str):
    """获取单条记录"""
    if not voice_service or not voice_service.storage_provider:
        raise HTTPException(status_code=503, detail="存储服务未初始化")
    
    try:
        record = voice_service.storage_provider.get_record(record_id)
        if not record:
            raise HTTPException(status_code=404, detail="记录不存在")
        
        return RecordItem(
            id=record['id'],
            text=record['text'],
            metadata=record.get('metadata', {}),
            created_at=record.get('created_at', '')
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/records/{record_id}")
async def delete_record(record_id: str):
    """删除记录"""
    if not voice_service or not voice_service.storage_provider:
        raise HTTPException(status_code=503, detail="存储服务未初始化")
    
    try:
        success = voice_service.storage_provider.delete_record(record_id)
        if not success:
            raise HTTPException(status_code=404, detail="记录不存在")
        
        return {"success": True, "message": "记录已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== WebSocket API ====================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点 - 用于实时文本和状态更新"""
    await websocket.accept()
    active_connections.add(websocket)
    logger.info(f"[API] WebSocket连接已建立，当前连接数: {len(active_connections)}")
    
    try:
        # 发送初始状态
        if voice_service:
            state = voice_service.get_state()
            current_text = getattr(voice_service, '_current_text', '')
            await websocket.send_json({
                "type": "initial_state",
                "state": state.value,
                "text": current_text
            })
        
        # 保持连接，等待客户端消息
        while True:
            try:
                data = await websocket.receive_json()
                logger.debug(f"[API] 收到WebSocket消息: {data}")
                # 可以在这里处理客户端发送的消息（如ping/pong等）
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"[API] WebSocket消息处理错误: {e}")
                break
    except WebSocketDisconnect:
        pass
    finally:
        active_connections.discard(websocket)
        logger.info(f"[API] WebSocket连接已断开，当前连接数: {len(active_connections)}")


# ==================== 服务器启动 ====================

def run_server(host: str = "127.0.0.1", port: int = 8765):
    """运行API服务器"""
    logger.info(f"[API] 启动API服务器: http://{host}:{port}")
    logger.info(f"[API] WebSocket端点: ws://{host}:{port}/ws")
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )


if __name__ == "__main__":
    run_server()

