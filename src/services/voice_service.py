"""
语音服务 - 整合录音、ASR、存储等功能
"""
import asyncio
import logging
from typing import Optional, Callable
from ..core.base import RecordingState, AudioRecorder
from ..core.config import Config
from ..providers.asr.volcano import VolcanoASRProvider
from ..providers.storage.sqlite import SQLiteStorageProvider

logger = logging.getLogger(__name__)


class VoiceService:
    """语音服务主类"""
    
    def __init__(self, config: Config):
        """初始化语音服务
        
        Args:
            config: 配置对象
        """
        self.config = config
        
        self.recorder: Optional[AudioRecorder] = None
        self.asr_provider: Optional[VolcanoASRProvider] = None
        self.storage_provider: Optional[SQLiteStorageProvider] = None
        
        self._on_text_callback: Optional[Callable[[str], None]] = None  # 保持向后兼容，但实际会传递累积文本
        self._on_state_change_callback: Optional[Callable[[RecordingState], None]] = None
        self._on_error_callback: Optional[Callable[[str, str], None]] = None  # error_type, message
        
        # 流式识别相关
        self._streaming_active = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        # 当前文本（用于API查询）
        self._current_text = ""
        
        # 当前会话记录ID（用于增量保存）
        self._current_session_id: Optional[str] = None
        
        self._initialize_providers()
    
    def _initialize_providers(self):
        """初始化提供商"""
        logger.info("[语音服务] 初始化提供商...")
        
        # 初始化火山引擎 ASR
        asr_config = {
            'base_url': self.config.get('asr.base_url', 'wss://openspeech.bytedance.com/api/v3/sauc/bigmodel'),
            'app_id': self.config.get('asr.app_id', ''),
            'app_key': self.config.get('asr.app_key', ''),
            'access_key': self.config.get('asr.access_key', '')
        }
        
        logger.info(f"[语音服务] ASR配置: base_url={asr_config['base_url']}, "
                   f"app_id={'已设置' if asr_config['app_id'] else '未设置'}, "
                   f"app_key={'已设置' if asr_config['app_key'] else '未设置'}, "
                   f"access_key={'已设置' if asr_config['access_key'] else '未设置'}")
        
        if asr_config['access_key'] and asr_config['app_key']:
            logger.info("[语音服务] 初始化火山引擎 ASR 提供商...")
            self.asr_provider = VolcanoASRProvider()
            if not self.asr_provider.initialize(asr_config):
                error_msg = "火山引擎 ASR 初始化失败，请检查配置"
                logger.error(f"[语音服务] {error_msg}")
                if self._on_error_callback:
                    self._on_error_callback("ASR初始化失败", error_msg)
                self.asr_provider = None
            else:
                logger.info("[语音服务] 火山引擎 ASR 提供商初始化成功")
        else:
            logger.warning("[语音服务] ASR配置不完整，ASR功能将不可用")
            # 不在这里显示错误，让主程序在用户尝试使用时再提示
            self.asr_provider = None
        
        # 初始化存储提供商
        storage_config = {
            'path': self.config.get('storage.path', '~/.voice_assistant/history.db')
        }
        logger.info(f"[语音服务] 初始化存储提供商: path={storage_config['path']}")
        self.storage_provider = SQLiteStorageProvider()
        self.storage_provider.initialize(storage_config)
        logger.info("[语音服务] 存储提供商初始化完成")
    
    def set_recorder(self, recorder: AudioRecorder):
        """设置录音器"""
        logger.info("[语音服务] 设置录音器")
        self.recorder = recorder
    
    def set_on_text_callback(self, callback: Callable[[str], None]):
        """设置文本回调函数"""
        self._on_text_callback = callback
    
    def set_on_state_change_callback(self, callback: Callable[[RecordingState], None]):
        """设置状态变化回调函数"""
        self._on_state_change_callback = callback
    
    def set_on_error_callback(self, callback: Callable[[str, str], None]):
        """设置错误回调函数"""
        self._on_error_callback = callback
    
    def start_recording(self) -> bool:
        """开始录音（流式识别）"""
        logger.info("[语音服务] 开始录音...")
        
        if not self.recorder:
            logger.error("[语音服务] 录音器未设置，无法开始录音")
            return False
        
        if self.recorder.get_state() == RecordingState.RECORDING:
            logger.warning("[语音服务] 录音已在进行中，无法重复开始")
            return False
        
        # 重置会话ID（开始新会话）
        self._current_session_id = None
        
        # 启动流式 ASR 识别
        if self.asr_provider:
            logger.info("[语音服务] 启动流式 ASR 识别...")
            try:
                # 获取事件循环
                try:
                    self._loop = asyncio.get_running_loop()
                    logger.debug("[语音服务] 获取运行中的事件循环（FastAPI环境）")
                    loop_running = True
                except RuntimeError:
                    # 没有运行中的事件循环，尝试获取或创建
                    try:
                        self._loop = asyncio.get_event_loop()
                        loop_running = self._loop.is_running()
                        logger.debug(f"[语音服务] 获取事件循环，运行状态: {loop_running}")
                    except RuntimeError:
                        self._loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(self._loop)
                        loop_running = False
                        logger.info("[语音服务] 创建新事件循环")
                
                # 设置文本回调
                self.asr_provider.set_on_text_callback(self._on_asr_text_received)
                logger.debug("[语音服务] 已设置ASR文本回调")
                
                # 启动流式识别
                language = self.config.get('asr.language', 'zh-CN')
                logger.info(f"[语音服务] 启动流式识别，语言: {language}")
                
                # 根据事件循环状态选择不同的执行方式
                if loop_running:
                    # 事件循环正在运行（FastAPI环境），使用create_task
                    async def start_async():
                        result = await self.asr_provider.start_streaming_recognition(language)
                        if not result:
                            error_msg = "启动流式 ASR 识别失败，请检查网络连接和ASR服务配置"
                            logger.error(f"[语音服务] {error_msg}")
                            if self._on_error_callback:
                                self._on_error_callback("ASR启动失败", error_msg)
                        else:
                            self._streaming_active = True
                            logger.info("[语音服务] 流式识别已启动")
                    
                    asyncio.create_task(start_async())
                    # 假设启动成功，实际结果会在异步任务中处理
                    self._streaming_active = True
                    logger.info("[语音服务] 已提交流式识别启动任务")
                else:
                    # 事件循环未运行，使用run_until_complete
                    if not self._loop.run_until_complete(self.asr_provider.start_streaming_recognition(language)):
                        error_msg = "启动流式 ASR 识别失败，请检查网络连接和ASR服务配置"
                        logger.error(f"[语音服务] {error_msg}")
                        if self._on_error_callback:
                            self._on_error_callback("ASR启动失败", error_msg)
                        return False
                    
                    self._streaming_active = True
                    logger.info("[语音服务] 流式识别已启动")
                
                # 设置音频数据回调（实时发送音频块）
                self.recorder.set_on_audio_chunk_callback(self._on_audio_chunk)
                logger.info("[语音服务] 已设置音频数据块回调")
            except Exception as e:
                error_msg = f"启动流式识别失败: {str(e)}"
                logger.error(f"[语音服务] {error_msg}", exc_info=True)
                if self._on_error_callback:
                    self._on_error_callback("ASR启动失败", error_msg)
                return False
        else:
            logger.warning("[语音服务] ASR提供商未初始化，将仅录音不进行识别")
        
        # 开始录音
        logger.info("[语音服务] 启动录音器...")
        success = self.recorder.start_recording()
        if success:
            logger.info("[语音服务] 录音已开始，状态: RECORDING")
            self._notify_state_change(RecordingState.RECORDING)
        else:
            logger.error("[语音服务] 录音器启动失败")
        return success
    
    def _on_audio_chunk(self, audio_data: bytes):
        """音频数据块回调（实时发送到 ASR）"""
        if self._streaming_active and self.asr_provider and self._loop:
            try:
                # 异步发送音频数据块（使用线程安全的方式）
                if not self._loop.is_closed():
                    # 如果事件循环正在运行，使用 call_soon_threadsafe
                    if self._loop.is_running():
                        logger.debug(f"[语音服务] 发送音频数据块到ASR: {len(audio_data)} 字节")
                        future = asyncio.run_coroutine_threadsafe(
                            self.asr_provider.send_audio_chunk(audio_data),
                            self._loop
                        )
                        # 不等待结果，避免阻塞
                    else:
                        # 如果事件循环未运行，直接运行
                        logger.debug(f"[语音服务] 发送音频数据块到ASR（直接运行）: {len(audio_data)} 字节")
                        self._loop.run_until_complete(
                            self.asr_provider.send_audio_chunk(audio_data)
                        )
            except Exception as e:
                error_msg = f"发送音频数据块失败: {str(e)}"
                logger.error(f"[语音服务] {error_msg}", exc_info=True)
                if self._on_error_callback:
                    self._on_error_callback("音频传输失败", error_msg)
    
    def _on_asr_text_received(self, text: str, is_final: bool):
        """ASR 文本接收回调
        
        Args:
            text: 识别文本（ASR提供商已经累积了所有片段的文本）
            is_final: 是否为最终结果（一个片段的最终结果）
        """
        logger.info(f"[语音服务] 收到ASR文本: '{text}', is_final={is_final}")
        # 更新当前文本（ASR提供商已经累积了所有片段的文本）
        # 对于流式识别，text 已经是累积后的完整文本（accumulated_text + current_segment_text）
        self._current_text = text
        
        # 分句固化时自动增量保存（音频笔记本的核心功能）
        if is_final and text and self.storage_provider:
            # 如果是新会话，创建新记录
            if not self._current_session_id:
                import uuid
                self._current_session_id = str(uuid.uuid4())
                language = self.config.get('asr.language', 'zh-CN')
                metadata = {
                    'language': language,
                    'provider': 'volcano',
                    'session_id': self._current_session_id,
                    'is_session': True  # 标记为会话记录
                }
                logger.info(f"[语音服务] 创建新会话记录: {self._current_session_id}")
                # 保存初始记录（可能为空文本）
                self.storage_provider.save_record("", metadata)
            else:
                # 更新现有会话记录
                logger.debug(f"[语音服务] 更新会话记录: {self._current_session_id}, 文本长度: {len(text)}")
                self._update_session_record(text)
        
        if self._on_text_callback:
            # 直接传递累积后的文本，前端会直接显示
            self._on_text_callback(text)
    
    def pause_recording(self) -> bool:
        """暂停录音"""
        logger.info("[语音服务] 暂停录音...")
        if not self.recorder:
            logger.error("[语音服务] 录音器未设置，无法暂停")
            return False
        
        success = self.recorder.pause_recording()
        if success:
            logger.info("[语音服务] 录音已暂停，状态: PAUSED")
            self._notify_state_change(RecordingState.PAUSED)
        else:
            logger.warning("[语音服务] 暂停录音失败")
        return success
    
    def resume_recording(self) -> bool:
        """恢复录音"""
        logger.info("[语音服务] 恢复录音...")
        if not self.recorder:
            logger.error("[语音服务] 录音器未设置，无法恢复")
            return False
        
        success = self.recorder.resume_recording()
        if success:
            logger.info("[语音服务] 录音已恢复，状态: RECORDING")
            self._notify_state_change(RecordingState.RECORDING)
        else:
            logger.warning("[语音服务] 恢复录音失败")
        return success
    
    def stop_recording(self) -> Optional[str]:
        """停止录音并获取最终识别结果"""
        logger.info("[语音服务] 停止录音...")
        if not self.recorder:
            logger.error("[语音服务] 录音器未设置，无法停止")
            return None
        
        self._notify_state_change(RecordingState.PROCESSING)
        logger.info("[语音服务] 状态: PROCESSING")
        
        # 停止录音
        logger.info("[语音服务] 停止录音器...")
        self.recorder.stop_recording()
        
        # 停止流式识别并获取最终结果
        final_text = None
        if self._streaming_active and self.asr_provider and self._loop:
            logger.info("[语音服务] 停止流式识别...")
            try:
                # 清除音频回调
                self.recorder.set_on_audio_chunk_callback(None)
                logger.debug("[语音服务] 已清除音频数据块回调")
                
                # 停止流式识别
                if not self._loop.is_closed():
                    logger.info("[语音服务] 等待ASR最终结果...")
                    # 检查事件循环是否正在运行
                    if self._loop.is_running():
                        # 事件循环正在运行（FastAPI环境），使用线程安全的方式
                        logger.debug("[语音服务] 事件循环正在运行，使用线程安全方式停止流式识别")
                        future = asyncio.run_coroutine_threadsafe(
                            self.asr_provider.stop_streaming_recognition(),
                            self._loop
                        )
                        # 等待结果（最多5秒）
                        try:
                            final_text = future.result(timeout=5.0)
                            logger.info(f"[语音服务] ASR最终结果: '{final_text}'")
                        except Exception as e:
                            error_msg = f"等待ASR最终结果超时或失败: {str(e)}"
                            logger.error(f"[语音服务] {error_msg}", exc_info=True)
                            if self._on_error_callback:
                                self._on_error_callback("ASR停止失败", error_msg)
                    else:
                        # 事件循环未运行，使用run_until_complete
                        logger.debug("[语音服务] 事件循环未运行，使用run_until_complete")
                        final_text = self._loop.run_until_complete(
                            self.asr_provider.stop_streaming_recognition()
                        )
                        logger.info(f"[语音服务] ASR最终结果: '{final_text}'")
                self._streaming_active = False
                logger.info("[语音服务] 流式识别已停止")
            except Exception as e:
                error_msg = f"停止流式识别失败: {str(e)}"
                logger.error(f"[语音服务] {error_msg}", exc_info=True)
                if self._on_error_callback:
                    self._on_error_callback("ASR停止失败", error_msg)
                self._streaming_active = False
        else:
            logger.info("[语音服务] 流式识别未激活，跳过停止ASR")
        
        # 最终保存记录（如果会话记录已存在，则更新；否则创建新记录）
        if final_text and self.storage_provider:
            if self._current_session_id:
                # 更新会话记录为最终版本
                logger.info(f"[语音服务] 更新会话记录为最终版本: {self._current_session_id}")
                self._update_session_record(final_text)
                logger.info("[语音服务] 会话记录已更新为最终版本")
            else:
                # 如果没有会话记录（可能是非流式识别），创建新记录
                language = self.config.get('asr.language', 'zh-CN')
                metadata = {
                    'language': language,
                    'provider': 'volcano'
                }
                logger.info(f"[语音服务] 保存识别结果到存储: '{final_text}'")
                self.storage_provider.save_record(final_text, metadata)
                logger.info("[语音服务] 识别结果已保存")
        
        # 重置会话ID
        self._current_session_id = None
        
        # 更新当前文本
        if final_text:
            self._current_text = final_text
        
        self._notify_state_change(RecordingState.IDLE)
        logger.info("[语音服务] 录音已停止，状态: IDLE")
        return final_text
    
    def get_state(self) -> RecordingState:
        """获取当前状态"""
        if not self.recorder:
            return RecordingState.IDLE
        return self.recorder.get_state()
    
    def _notify_state_change(self, state: RecordingState):
        """通知状态变化"""
        if self._on_state_change_callback:
            self._on_state_change_callback(state)
    
    def _update_session_record(self, text: str):
        """更新会话记录（增量保存）"""
        if not self._current_session_id or not self.storage_provider:
            return
        
        try:
            # 获取现有记录
            existing_record = self.storage_provider.get_record(self._current_session_id)
            if existing_record:
                # 更新文本
                language = self.config.get('asr.language', 'zh-CN')
                metadata = {
                    'language': language,
                    'provider': 'volcano',
                    'session_id': self._current_session_id,
                    'is_session': True,
                    'updated_at': self._get_timestamp()
                }
                # 使用存储提供商的更新方法（如果支持）
                if hasattr(self.storage_provider, 'update_record'):
                    self.storage_provider.update_record(self._current_session_id, text, metadata)
                else:
                    # 如果不支持更新，删除旧记录并创建新记录
                    self.storage_provider.delete_record(self._current_session_id)
                    self.storage_provider.save_record(text, metadata)
                    logger.debug(f"[语音服务] 会话记录已更新（通过删除重建）: {self._current_session_id}")
            else:
                # 如果记录不存在，创建新记录
                language = self.config.get('asr.language', 'zh-CN')
                metadata = {
                    'language': language,
                    'provider': 'volcano',
                    'session_id': self._current_session_id,
                    'is_session': True
                }
                self.storage_provider.save_record(text, metadata)
                logger.debug(f"[语音服务] 会话记录已创建: {self._current_session_id}")
        except Exception as e:
            logger.error(f"[语音服务] 更新会话记录失败: {e}", exc_info=True)
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def cleanup(self):
        """清理资源"""
        logger.info("[语音服务] 清理资源...")
        
        # 停止流式识别
        if self._streaming_active and self.asr_provider and self._loop:
            logger.info("[语音服务] 清理流式识别...")
            try:
                if not self._loop.is_closed():
                    # 检查事件循环是否正在运行
                    if self._loop.is_running():
                        # 事件循环正在运行，使用线程安全的方式
                        logger.debug("[语音服务] 事件循环正在运行，使用线程安全方式清理流式识别")
                        future = asyncio.run_coroutine_threadsafe(
                            self.asr_provider.stop_streaming_recognition(),
                            self._loop
                        )
                        try:
                            future.result(timeout=5.0)
                        except Exception as e:
                            logger.warning(f"[语音服务] 清理流式识别时出错: {e}")
                    else:
                        # 事件循环未运行，使用run_until_complete
                        logger.debug("[语音服务] 事件循环未运行，使用run_until_complete清理流式识别")
                        self._loop.run_until_complete(
                            self.asr_provider.stop_streaming_recognition()
                        )
            except Exception as e:
                logger.warning(f"[语音服务] 清理流式识别时出错: {e}")
            self._streaming_active = False
        
        if self.recorder:
            logger.info("[语音服务] 清理录音器...")
            self.recorder.cleanup()
        
        logger.info("[语音服务] 资源清理完成")