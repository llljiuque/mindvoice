"""
语音服务 - 整合录音、ASR、存储等功能
"""
import asyncio
import logging
from typing import Optional, Callable, Union
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
        
        self._on_text_callback: Optional[Callable[[str, bool, dict], None]] = None
        self._on_state_change_callback: Optional[Callable[[RecordingState], None]] = None
        self._on_error_callback: Optional[Callable[[str, str], None]] = None
        
        self._streaming_active = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._current_text = ""
        self._current_session_id: Optional[str] = None
        self._current_app_id: Optional[str] = None  # 当前使用ASR的应用ID
        
        self._initialize_providers()
    
    def _initialize_providers(self):
        """初始化提供商"""
        logger.info("[语音服务] 初始化提供商...")
        # 根据配置源自动选择使用用户配置还是厂商配置
        config_source = self.config.get_asr_config_source()
        use_user_config = (config_source == 'user')
        self._initialize_asr_provider(use_user_config=use_user_config)
        
        storage_config = {
            'path': self.config.get('storage.path', '~/.voice_assistant/history.db')
        }
        logger.info(f"[语音服务] 初始化存储提供商: path={storage_config['path']}")
        self.storage_provider = SQLiteStorageProvider()
        self.storage_provider.initialize(storage_config)
        logger.info("[语音服务] 存储提供商初始化完成")
    
    def _initialize_asr_provider(self, use_user_config: bool = True):
        """初始化ASR提供商
        
        Args:
            use_user_config: 是否使用用户自定义配置
        """
        # 获取ASR配置（根据use_user_config决定使用用户配置还是厂商配置）
        asr_config = self.config.get_asr_config(use_user_config=use_user_config)
        config_source = self.config.get_asr_config_source()
        
        logger.info(f"[语音服务] ASR配置源: {config_source}, base_url={asr_config.get('base_url', '')}, "
                   f"app_id={'已设置' if asr_config.get('app_id') else '未设置'}, "
                   f"app_key={'已设置' if asr_config.get('app_key') else '未设置'}, "
                   f"access_key={'已设置' if asr_config.get('access_key') else '未设置'}")
        
        if asr_config.get('access_key') and asr_config.get('app_key'):
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
            self.asr_provider = None
    
    def reload_asr_provider(self, use_user_config: bool = True):
        """重新加载ASR提供商（用于配置更改后）
        
        Args:
            use_user_config: 是否使用用户自定义配置
        """
        logger.info(f"[语音服务] 重新加载ASR提供商，使用{'用户' if use_user_config else '厂商'}配置")
        # 如果正在录音，先停止
        if self.get_state() != RecordingState.IDLE:
            logger.warning("[语音服务] 正在录音，无法重新加载ASR提供商")
            return False
        
        # 清理旧的提供商
        if self.asr_provider:
            try:
                self.asr_provider.cleanup()
            except Exception as e:
                logger.warning(f"[语音服务] 清理旧ASR提供商失败: {e}")
            self.asr_provider = None
        
        # 重新初始化
        self._initialize_asr_provider(use_user_config=use_user_config)
        return True
    
    def set_recorder(self, recorder: AudioRecorder):
        """设置录音器"""
        logger.info("[语音服务] 设置录音器")
        self.recorder = recorder
    
    def set_on_text_callback(self, callback: Callable[[str, bool, dict], None]):
        """设置文本回调函数
        
        Args:
            callback: 回调函数 (text: str, is_definite_utterance: bool, time_info: dict)
                      text: 识别的文本（已在后端累加处理）
                      is_definite_utterance: 是否为确定的utterance（当ASR服务返回definite=True时，此值为True）
                                             表示一个完整的、确定的语音识别单元已完成
                      time_info: 时间信息字典，包含:
                                - start_time: 开始时间（毫秒）
                                - end_time: 结束时间（毫秒）
                                注意：仅在 is_definite_utterance=True 时有值
        """
        self._on_text_callback = callback
    
    def set_on_state_change_callback(self, callback: Callable[[RecordingState], None]):
        """设置状态变化回调函数"""
        self._on_state_change_callback = callback
    
    def set_on_error_callback(self, callback: Callable[[str, str], None]):
        """设置错误回调函数"""
        self._on_error_callback = callback
    
    def start_recording(self, app_id: str = None) -> bool:
        """
        开始录音（流式识别）
        
        Args:
            app_id: 应用ID ('voice-note', 'voice-chat', 'smart-chat' 等)
        
        新架构流程：
        1. Audio 先启动（保证缓冲）
        2. 设置 AudioASRGateway 回调
        3. AudioASRGateway 根据配置决定何时启动 ASR
           - enabled=False: 立即启动 ASR（直通模式）
           - enabled=True: 等待检测到语音后启动 ASR（VAD模式）
        """
        logger.info(f"[语音服务] 开始录音... (app_id={app_id})")
        
        # 记录当前应用ID
        self._current_app_id = app_id
        
        if not self.recorder:
            logger.error("[语音服务] 录音器未设置，无法开始录音")
            return False
        
        if self.recorder.get_state() == RecordingState.RECORDING:
            logger.warning("[语音服务] 录音已在进行中，无法重复开始")
            return False
        
        self._current_session_id = None
        
        # 获取事件循环（用于ASR异步操作）
        if self.asr_provider:
            try:
                try:
                    self._loop = asyncio.get_running_loop()
                except RuntimeError:
                    try:
                        self._loop = asyncio.get_event_loop()
                        if not self._loop.is_running():
                            # 创建新的事件循环
                            self._loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(self._loop)
                    except RuntimeError:
                        self._loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(self._loop)
            except Exception as e:
                logger.error(f"[语音服务] 获取事件循环失败: {e}", exc_info=True)
                self._loop = None
            
            # 设置ASR文本回调
            self.asr_provider.set_on_text_callback(self._on_asr_text_received)
            
            # 设置ASR断开连接回调
            if hasattr(self.asr_provider, 'set_on_disconnected_callback'):
                self.asr_provider.set_on_disconnected_callback(self._on_asr_disconnected)
            
            # 设置 AudioASRGateway 回调（控制ASR启停）
            self.recorder.set_asr_gateway_callbacks(
                on_speech_start=self._on_speech_start,
                on_speech_end=self._on_speech_end
            )
        
        # 设置音频数据回调（用于发送音频到ASR）
        self.recorder.set_on_audio_chunk_callback(self._on_audio_chunk)
        
        # 开始录音（Audio 先启动）
        logger.info("[语音服务] 启动录音器（Audio先行启动，保证缓冲）...")
        success = self.recorder.start_recording()
        if success:
            logger.info("[语音服务] 录音已开始，状态: RECORDING")
            logger.info("[语音服务] AudioASRGateway 将根据配置控制 ASR 启停")
            self._notify_state_change(RecordingState.RECORDING)
        else:
            logger.error("[语音服务] 录音器启动失败")
        return success
    
    def _on_speech_start(self):
        """
        AudioASRGateway 回调：语音开始（应启动ASR）
        
        当 VAD 检测到语音，或 VAD 未启用时（直通模式）会触发此回调
        """
        if not self.asr_provider:
            logger.warning("[语音服务] ASR提供商未初始化，无法启动ASR")
            return
        
        # 检查 ASR provider 的实际状态（而不仅仅是 _streaming_active）
        # 因为可能存在时序问题：_streaming_active 已设置为 False，但 ASR 还在关闭中
        if self._streaming_active or (hasattr(self.asr_provider, '_streaming_active') and self.asr_provider._streaming_active):
            logger.debug("[语音服务] ASR已在运行中或正在关闭，跳过重复启动")
            return
        
        logger.info("[语音服务] AudioASRGateway 触发：启动ASR")
        language = self.config.get('asr.language', 'zh-CN')
        
        try:
            if not self._loop:
                logger.error("[语音服务] 事件循环未设置，无法启动ASR")
                return
            
            async def start_async():
                result = await self.asr_provider.start_streaming_recognition(language)
                if not result:
                    error_msg = "启动流式 ASR 识别失败，请检查网络连接和ASR服务配置"
                    logger.error(f"[语音服务] {error_msg}")
                    if self._on_error_callback:
                        self._on_error_callback("ASR启动失败", error_msg)
                else:
                    self._streaming_active = True
                    logger.info("[语音服务] ✓ ASR已启动（由AudioASRGateway触发）")
            
            # 使用 run_coroutine_threadsafe 从任何线程安全调用
            # 因为回调可能在音频消费线程中触发
            if self._loop.is_running():
                # 事件循环正在运行，使用线程安全方式
                future = asyncio.run_coroutine_threadsafe(start_async(), self._loop)
                # 不等待结果，让它在后台运行
            else:
                # 事件循环未运行，使用 run_until_complete
                if not self._loop.run_until_complete(self.asr_provider.start_streaming_recognition(language)):
                    error_msg = "启动流式 ASR 识别失败，请检查网络连接和ASR服务配置"
                    logger.error(f"[语音服务] {error_msg}")
                    if self._on_error_callback:
                        self._on_error_callback("ASR启动失败", error_msg)
                    return
                
                self._streaming_active = True
                logger.info("[语音服务] ✓ ASR已启动（由AudioASRGateway触发）")
        except Exception as e:
            error_msg = f"启动ASR失败: {str(e)}"
            logger.error(f"[语音服务] {error_msg}", exc_info=True)
            if self._on_error_callback:
                self._on_error_callback("ASR启动失败", error_msg)
    
    def _on_speech_end(self):
        """
        AudioASRGateway 回调：语音结束（应停止ASR）
        
        当 VAD 检测到静音结束，或用户停止工作时会触发此回调
        
        ⭐ 正确的流程：
        1. 发送结束标记（None）到音频队列
        2. ASR发送器会发送负包 (seq=-N, is_last=True)
        3. ASR接收器等待服务器的最后响应 (is_last_package=True)
        4. 接收到最后响应后，ASR才会真正断开
        5. ASR的_on_disconnected回调会通知VoiceService重置状态
        
        注意：不要在这里立即设置 _streaming_active = False，
        因为ASR还在等待服务器的最后响应！
        """
        if not self._streaming_active:
            logger.debug("[语音服务] ASR未在运行，跳过停止")
            return
        
        logger.info("[语音服务] AudioASRGateway 触发：停止ASR（发送结束标记）")
        
        try:
            if self.asr_provider and self._loop:
                # 发送结束标记（触发负包发送）
                if hasattr(self.asr_provider, '_audio_queue') and self.asr_provider._audio_queue:
                    try:
                        queue_size = self.asr_provider._audio_queue.qsize()
                        queue_id = id(self.asr_provider._audio_queue)
                        logger.info(f"[语音服务] 准备发送结束标记，ASR队列当前深度={queue_size}, 队列ID={queue_id}")
                        self.asr_provider._audio_queue.put_nowait(None)
                        new_queue_size = self.asr_provider._audio_queue.qsize()
                        logger.info(f"[语音服务] 已发送结束标记，队列深度: {queue_size} -> {new_queue_size}")
                    except Exception as e:
                        logger.warning(f"[语音服务] 发送结束标记失败: {e}")
                
                # ⚠️ 不要在这里设置 _streaming_active = False！
                # ASR的_on_disconnected回调会在断开后重置状态
                
        except Exception as e:
            logger.error(f"[语音服务] 停止ASR失败: {e}", exc_info=True)
            # 异常情况下立即重置状态
            self._streaming_active = False
            if hasattr(self.asr_provider, '_streaming_active'):
                self.asr_provider._streaming_active = False
    
    def _on_audio_chunk(self, audio_data: bytes):
        """
        音频数据块回调
        
        接收到来自 AudioASRGateway 的音频数据（已过滤或直通）
        """
        # 如果录音器处于暂停状态，不发送音频数据
        if self.recorder and self.recorder.get_state() == RecordingState.PAUSED:
            return
        
        # 如果ASR未激活，不发送音频数据
        if not self._streaming_active:
            return
        
        if self.asr_provider and self._loop:
            try:
                if not self._loop.is_closed():
                    if self._loop.is_running():
                        # 异步发送到ASR队列
                        future = asyncio.run_coroutine_threadsafe(
                            self.asr_provider.send_audio_chunk(audio_data),
                            self._loop
                        )
                        # 不等待结果，避免阻塞音频线程
                    else:
                        self._loop.run_until_complete(
                            self.asr_provider.send_audio_chunk(audio_data)
                        )
            except Exception as e:
                error_msg = f"发送音频数据块失败: {str(e)}"
                logger.error(f"[语音服务] {error_msg}", exc_info=True)
                if self._on_error_callback:
                    self._on_error_callback("音频传输失败", error_msg)
    
    def _on_asr_text_received(self, text: str, is_definite_utterance: bool, time_info: dict):
        """ASR文本接收回调"""
        if is_definite_utterance:
            time_info_str = ""
            if time_info:
                time_info_str = f", start_time={time_info.get('start_time', 0)}ms, end_time={time_info.get('end_time', 0)}ms"
            logger.info(f"[语音服务] 收到确定utterance: '{text}'{time_info_str}")
        self._current_text = text
        
        if self._on_text_callback:
            self._on_text_callback(text, is_definite_utterance, time_info)
    
    def _on_asr_disconnected(self):
        """
        ASR断开连接回调
        
        当ASR接收器完成并断开连接时调用此回调，确保VoiceService的状态被正确重置
        """
        logger.info("[语音服务] ASR已断开连接，重置状态")
        self._streaming_active = False
    
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
        """
        停止录音并获取最终识别结果
        
        新架构停止流程：
        1. Audio 先停止
        2. AudioASRGateway.stop() 会触发 on_speech_end，停止 ASR
        3. 等待 ASR 完成最后几个包的识别（等待3-5秒或超时）
        """
        logger.info(f"[语音服务] 停止录音... (app_id={self._current_app_id})")
        
        # 清除应用ID
        self._current_app_id = None
        
        if not self.recorder:
            logger.error("[语音服务] 录音器未设置，无法停止")
            return None
        
        try:
            self._notify_state_change(RecordingState.STOPPING)
            logger.info("[语音服务] 状态: STOPPING")
            
            # 停止录音（Audio 先停止）
            # 这会触发 AudioASRGateway.stop()，进而触发 on_speech_end 回调停止 ASR
            logger.info("[语音服务] 停止录音器（Audio先行停止）...")
            self.recorder.stop_recording()
            
            # 清除音频回调
            self.recorder.set_on_audio_chunk_callback(None)
            logger.debug("[语音服务] 已清除音频数据块回调")
            
            # 等待 ASR 完成最后几个包的识别
            final_text = None
            if self._streaming_active and self.asr_provider:
                logger.info("[语音服务] 等待 ASR 完成最后几个包的识别...")
                import time
                
                # 等待一段时间让 ASR 处理最后的音频包
                # 通常 ASR 服务需要 2-3 秒来返回最终结果
                max_wait_time = 5.0  # 最大等待5秒
                wait_interval = 0.1  # 每100ms检查一次
                waited_time = 0.0
                
                while waited_time < max_wait_time and self._streaming_active:
                    time.sleep(wait_interval)
                    waited_time += wait_interval
                
                final_text = self._current_text
                if waited_time >= max_wait_time:
                    logger.warning(f"[语音服务] 等待ASR完成超时（{max_wait_time}秒），使用当前文本")
                else:
                    logger.info(f"[语音服务] ASR已完成，等待时间: {waited_time:.2f}秒")
                logger.info(f"[语音服务] ✓ 最终文本: '{final_text}'")
            else:
                if not self.asr_provider:
                    logger.info("[语音服务] ASR提供商未初始化，跳过等待")
                elif not self._streaming_active:
                    logger.info("[语音服务] ASR未激活，跳过等待")
                final_text = self._current_text
            
            self._current_session_id = None
            if final_text:
                self._current_text = final_text
            
            return final_text
        except Exception as e:
            logger.error(f"[语音服务] 停止录音过程发生异常: {e}", exc_info=True)
            # 确保流式识别被标记为非激活状态
            self._streaming_active = False
            return None
        finally:
            # 确保流式识别被标记为非激活状态
            self._streaming_active = False
            # 无论如何都要确保状态被重置为IDLE
            self._notify_state_change(RecordingState.IDLE)
            logger.info("[语音服务] 录音已停止，状态: IDLE")
    
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
        """更新会话记录"""
        if not self._current_session_id or not self.storage_provider:
            return
        
        try:
            existing_record = self.storage_provider.get_record(self._current_session_id)
            language = self.config.get('asr.language', 'zh-CN')
            metadata = {
                'language': language,
                'provider': 'volcano',
                'session_id': self._current_session_id,
                'is_session': True,
                'updated_at': self._get_timestamp() if existing_record else None
            }
            
            if existing_record:
                if hasattr(self.storage_provider, 'update_record'):
                    self.storage_provider.update_record(self._current_session_id, text, metadata)
                else:
                    self.storage_provider.delete_record(self._current_session_id)
                    self.storage_provider.save_record(text, metadata)
            else:
                metadata['is_session'] = True
                self.storage_provider.save_record(text, metadata)
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