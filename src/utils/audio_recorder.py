"""
音频录制器实现（基于 sounddevice）
"""
import threading
import queue
import logging
import sounddevice as sd
import numpy as np
from typing import Optional, Callable
from ..core.base import AudioRecorder, RecordingState
from ..core.logger import get_logger, get_system_logger
from ..core.error_codes import SystemError, SystemErrorInfo

logger = get_logger("AudioDevice")


class SoundDeviceRecorder(AudioRecorder):
    """基于 sounddevice 的音频录制器，支持可选的VAD过滤和音频处理（AGC+NS）"""
    
    def __init__(self, rate: int = 16000, channels: int = 1, chunk: int = 1024, 
                 device: Optional[int] = None, vad_config: Optional[dict] = None,
                 audio_processing_config: Optional[dict] = None,
                 max_buffer_seconds: int = 60):
        """初始化音频录制器
        
        Args:
            rate: 采样率
            channels: 声道数
            chunk: 每次读取的帧数
            device: 音频设备ID，None表示使用默认设备
            vad_config: VAD配置字典（可选），包含：
                - enabled: 是否启用VAD
                - mode: VAD敏感度（0-3）
                - 其他VAD参数...
            audio_processing_config: 音频处理配置字典（可选），包含：
                - enabled: 是否启用音频处理
                - enable_agc: 是否启用AGC
                - enable_ns: 是否启用NS
                - agc_level: AGC级别（0-3）
                - ns_level: NS级别（0-3）
            max_buffer_seconds: 最大缓冲时长（秒），超过后自动清理旧数据，默认60秒
        """
        self.rate = rate
        self.channels = channels
        self.chunk = chunk
        self.device = device
        self.state = RecordingState.IDLE
        
        self.stream: Optional[sd.InputStream] = None
        self.audio_buffer = bytearray()
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.audio_queue = queue.Queue()
        self.paused = False
        
        # 流式音频数据回调（用于实时 ASR）
        self.on_audio_chunk: Optional[Callable[[bytes], None]] = None
        
        # 缓冲区管理配置
        self.max_buffer_seconds = max_buffer_seconds
        # 计算最大缓冲区大小（字节）：采样率 * 通道数 * 2字节(int16) * 秒数
        self.max_buffer_size = rate * channels * 2 * max_buffer_seconds
        
        # 音频处理器（AGC + NS）
        self.audio_processor = None
        if audio_processing_config and audio_processing_config.get('enabled', False):
            try:
                from .audio_processor import AudioProcessor
                self.audio_processor = AudioProcessor(
                    sample_rate=rate,
                    channels=channels,
                    enable_agc=audio_processing_config.get('enable_agc', True),
                    enable_ns=audio_processing_config.get('enable_ns', True),
                    agc_level=audio_processing_config.get('agc_level', 2),
                    ns_level=audio_processing_config.get('ns_level', 2)
                )
                stats = self.audio_processor.get_stats()
                logger.info(f"[音频] 音频处理器已启用: {stats}")
            except Exception as e:
                logger.error(f"[音频] 初始化音频处理器失败: {e}", exc_info=True)
                self.audio_processor = None
        
        # AudioASRGateway（Audio到ASR的网关控制器，可选功能）
        self.asr_gateway = None
        if vad_config:
            try:
                from .audio_asr_gateway import AudioASRGateway
                self.asr_gateway = AudioASRGateway(vad_config)
                if self.asr_gateway.enabled:
                    logger.info("[音频] AudioASRGateway已启用（VAD模式）")
                else:
                    logger.info("[音频] AudioASRGateway已启用（直通模式）")
            except ImportError as e:
                logger.error(f"[音频] 导入AudioASRGateway失败: {e}")
                logger.error("[音频] 请确保已安装webrtcvad: pip install webrtcvad>=2.0.10")
                self.asr_gateway = None
            except Exception as e:
                logger.error(f"[音频] 初始化AudioASRGateway失败: {e}", exc_info=True)
                self.asr_gateway = None
        
        # 统计信息
        self._chunk_count = 0
        self._total_bytes = 0
        self._callback_errors = 0
        self._buffer_cleanups = 0  # 缓冲区清理次数
        
        logger.info(f"[音频] 初始化音频录制器: rate={rate}Hz, channels={channels}, chunk={chunk}, device={device}")
        logger.info(f"[音频] 缓冲区管理: 最大缓冲{max_buffer_seconds}秒 (约{self.max_buffer_size // 1024 // 1024}MB)")
        logger.info(f"[音频] 音频设备信息: {sd.query_devices(kind='input')}")
    
    @staticmethod
    def list_input_devices(force_refresh: bool = False) -> list[dict]:
        """获取所有输入音频设备列表
        
        Args:
            force_refresh: 是否强制刷新设备列表（重新初始化 PortAudio）
        
        Returns:
            设备列表，每个设备包含 id, name, channels, samplerate 等信息
        """
        try:
            # 如果需要强制刷新，重新初始化 PortAudio
            # 这会重新扫描系统的音频设备
            if force_refresh:
                try:
                    # 通过创建一个临时流来触发设备重新扫描
                    # 这是 sounddevice 推荐的刷新设备列表的方法
                    sd._terminate()
                    sd._initialize()
                    logger.info("[音频] 已强制刷新音频设备列表")
                except Exception as refresh_error:
                    logger.warning(f"[音频] 强制刷新设备列表时出现警告: {refresh_error}")
                    # 即使刷新失败，仍然尝试获取设备列表
            
            all_devices = sd.query_devices()
            result = []
            for device in all_devices:
                # 筛选出输入设备（max_input_channels > 0）
                if device.get('max_input_channels', 0) > 0:
                    result.append({
                        'id': device['index'],
                        'name': device['name'],
                        'channels': device['max_input_channels'],
                        'samplerate': device.get('default_samplerate', 44100.0),
                        'hostapi': device.get('hostapi', 0)
                    })
            return result
        except Exception as e:
            logger.error(f"[音频] 获取设备列表失败: {e}", exc_info=True)
            return []
    
    def set_device(self, device: Optional[int]):
        """设置音频设备
        
        Args:
            device: 音频设备ID，None表示使用默认设备
        """
        if self.state != RecordingState.IDLE:
            logger.warning(f"[音频] 无法更改设备: 当前状态为 {self.state.value}，请先停止录音")
            return False
        
        self.device = device
        logger.info(f"[音频] 音频设备已设置为: {device}")
        return True
    
    def start_recording(self) -> bool:
        """开始录音"""
        sys_logger = get_system_logger()
        
        if self.state != RecordingState.IDLE:
            logger.warning(f"[音频] 无法开始录音: 当前状态为 {self.state.value}")
            return False
        
        try:
            logger.info("[音频] 开始录音...")
            self.audio_buffer = bytearray()
            self.running = True
            self.paused = False
            self._chunk_count = 0
            self._total_bytes = 0
            self._callback_errors = 0
            self._buffer_cleanups = 0
            
            # 重置AudioASRGateway状态（如果启用）
            if self.asr_gateway:
                self.asr_gateway.reset()
                logger.debug("[音频] AudioASRGateway已重置")
            
            logger.info(f"[音频] 创建音频输入流: samplerate={self.rate}, channels={self.channels}, blocksize={self.chunk}, device={self.device}")
            
            try:
                self.stream = sd.InputStream(
                    samplerate=self.rate,
                    channels=self.channels,
                    dtype=np.int16,
                    blocksize=self.chunk,
                    device=self.device,
                    callback=self._audio_callback
                )
                self.stream.start()
            except sd.PortAudioError as e:
                # PortAudio特定错误处理
                error_msg = str(e)
                if "device" in error_msg.lower() or "找不到" in error_msg or "not found" in error_msg.lower():
                    error_info = SystemErrorInfo(
                        SystemError.AUDIO_DEVICE_NOT_FOUND,
                        details=f"音频设备不可用: {error_msg}",
                        technical_info=f"PortAudioError: {error_msg}, device_id={self.device}"
                    )
                elif "busy" in error_msg.lower() or "占用" in error_msg:
                    error_info = SystemErrorInfo(
                        SystemError.AUDIO_DEVICE_BUSY,
                        details=f"音频设备被占用: {error_msg}",
                        technical_info=f"PortAudioError: {error_msg}"
                    )
                elif "permission" in error_msg.lower() or "权限" in error_msg:
                    error_info = SystemErrorInfo(
                        SystemError.AUDIO_DEVICE_PERMISSION_DENIED,
                        details=f"无音频设备权限: {error_msg}",
                        technical_info=f"PortAudioError: {error_msg}"
                    )
                elif "format" in error_msg.lower() or "单声道" in error_msg:
                    error_info = SystemErrorInfo(
                        SystemError.AUDIO_DEVICE_FORMAT_NOT_SUPPORTED,
                        details=f"音频格式不支持: {error_msg}",
                        technical_info=f"PortAudioError: {error_msg}, rate={self.rate}, channels={self.channels}"
                    )
                else:
                    error_info = SystemErrorInfo(
                        SystemError.AUDIO_DEVICE_OPEN_FAILED,
                        details=f"无法打开音频设备: {error_msg}",
                        technical_info=f"PortAudioError: {error_msg}"
                    )
                
                sys_logger.log_error("AudioDevice", error_info)
                logger.error(f"[音频] 打开音频设备失败: {e}", exc_info=True)
                self.state = RecordingState.IDLE
                raise
            
            logger.info("[音频] 音频流已启动")
            
            self.thread = threading.Thread(target=self._consume_audio, daemon=True)
            self.thread.start()
            logger.info("[音频] 音频消费线程已启动")
            
            # 启动AudioASRGateway（会触发相应的回调）
            if self.asr_gateway:
                self.asr_gateway.start()
                logger.debug("[音频] AudioASRGateway已启动")
            
            self.state = RecordingState.RECORDING
            logger.info("[音频] 录音已开始，状态: RECORDING")
            
            sys_logger.log_audio_event("开始录音", 
                                       device=self.device, 
                                       rate=self.rate, 
                                       channels=self.channels)
            return True
            
        except Exception as e:
            error_info = SystemErrorInfo(
                SystemError.AUDIO_STREAM_ERROR,
                details=f"启动录音失败: {str(e)}",
                technical_info=f"{type(e).__name__}: {str(e)}"
            )
            sys_logger.log_error("AudioDevice", error_info)
            logger.error(f"[音频] 启动录音失败: {e}", exc_info=True)
            self.state = RecordingState.IDLE
            raise  # 重新抛出异常，让上层处理
    
    def pause_recording(self) -> bool:
        """暂停录音"""
        if self.state != RecordingState.RECORDING:
            logger.warning(f"[音频] 无法暂停录音: 当前状态为 {self.state.value}")
            return False
        
        logger.info("[音频] 暂停录音")
        self.paused = True
        self.state = RecordingState.PAUSED
        logger.info(f"[音频] 录音已暂停，已采集 {self._chunk_count} 个音频块，总计 {self._total_bytes} 字节")
        return True
    
    def resume_recording(self) -> bool:
        """恢复录音"""
        if self.state != RecordingState.PAUSED:
            logger.warning(f"[音频] 无法恢复录音: 当前状态为 {self.state.value}")
            return False
        
        logger.info("[音频] 恢复录音")
        self.paused = False
        self.state = RecordingState.RECORDING
        logger.info("[音频] 录音已恢复，状态: RECORDING")
        return True
    
    def stop_recording(self) -> bytes:
        """停止录音并返回音频数据"""
        if self.state == RecordingState.IDLE:
            logger.warning("[音频] 录音已处于 IDLE 状态，无需停止")
            return b""
        
        logger.info("[音频] 停止录音...")
        self.running = False
        
        # 停止AudioASRGateway（会触发相应的回调）
        if self.asr_gateway:
            self.asr_gateway.stop()
            logger.debug("[音频] AudioASRGateway已停止")
        
        if self.stream:
            try:
                logger.debug("[音频] 停止音频流...")
                self.stream.stop()
                self.stream.close()
                logger.info("[音频] 音频流已停止并关闭")
            except Exception as e:
                logger.warning(f"[音频] 停止音频流时出错: {e}")
            self.stream = None
        
        if self.thread:
            logger.debug("[音频] 等待音频消费线程结束...")
            self.thread.join(timeout=1.0)
            if self.thread.is_alive():
                logger.warning("[音频] 音频消费线程未在1秒内结束")
            else:
                logger.info("[音频] 音频消费线程已结束")
            self.thread = None
        
        # 返回录制的音频数据
        audio_data = bytes(self.audio_buffer)
        audio_size = len(audio_data)
        logger.info(f"[音频] 录音已停止，状态: IDLE")
        logger.info(f"[音频] 录音统计: 共采集 {self._chunk_count} 个音频块，总计 {self._total_bytes} 字节，最终音频数据 {audio_size} 字节")
        if self._callback_errors > 0:
            logger.warning(f"[音频] 音频回调错误次数: {self._callback_errors}")
        
        self.audio_buffer = bytearray()
        self.state = RecordingState.IDLE
        
        return audio_data
    
    def get_state(self) -> RecordingState:
        """获取当前状态"""
        return self.state
    
    def cleanup(self):
        """清理资源"""
        logger.info("[音频] 清理音频录制器资源...")
        if self.running:
            self.stop_recording()
        logger.info("[音频] 资源清理完成")
    
    def _audio_callback(self, indata, frames, time, status):
        """音频回调函数"""
        if status:
            logger.warning(f"[音频] 音频回调状态警告: {status}")
        
        if self.running and not self.paused:
            try:
                audio_data = indata.tobytes()
                audio_size = len(audio_data)
                self.audio_queue.put(audio_data)
                
                # 每100个块记录一次详细信息
                if self._chunk_count % 100 == 0:
                    logger.debug(f"[音频] 音频回调: 块#{self._chunk_count}, 帧数={frames}, 数据大小={audio_size}字节, 时间戳={time}")
                
                self._chunk_count += 1
                self._total_bytes += audio_size
            except Exception as e:
                self._callback_errors += 1
                logger.error(f"[音频] 音频回调错误 (第{self._callback_errors}次): {e}", exc_info=True)
    
    def _consume_audio(self):
        """消费音频数据"""
        logger.info("[音频] 音频消费线程开始运行")
        consumed_chunks = 0
        
        while self.running:
            try:
                data = self.audio_queue.get(timeout=0.1)
                if not self.paused:
                    # 保存到缓冲区（用于完整录音文件）
                    self.audio_buffer.extend(data)
                    consumed_chunks += 1
                    
                    # 缓冲区大小管理：如果超过最大限制，清理旧数据
                    buffer_size = len(self.audio_buffer)
                    if buffer_size > self.max_buffer_size:
                        # 保留最新的一半数据，删除旧的一半
                        keep_size = self.max_buffer_size // 2
                        remove_size = buffer_size - keep_size
                        self.audio_buffer = self.audio_buffer[remove_size:]
                        self._buffer_cleanups += 1
                        logger.info(f"[音频] 缓冲区清理: 删除了 {remove_size // 1024 // 1024}MB 旧数据, "
                                  f"保留最近 {keep_size // 1024 // 1024}MB, "
                                  f"累计清理 {self._buffer_cleanups} 次")
                    
                    # 每100个块记录一次详细信息
                    if consumed_chunks % 100 == 0:
                        logger.debug(f"[音频] 消费音频块 #{consumed_chunks}, 大小={len(data)}字节, 缓冲区总大小={len(self.audio_buffer)}字节")
                    
                    # 音频处理流程：原始音频 → AudioProcessor (AGC+NS) → AudioASRGateway (VAD) → ASR
                    processed_audio = data
                    
                    # 步骤1：应用音频处理（AGC + NS）
                    if self.audio_processor:
                        try:
                            processed_audio = self.audio_processor.process(processed_audio)
                        except Exception as e:
                            logger.error(f"[音频] 音频处理失败: {e}", exc_info=True)
                    
                    # 步骤2：实时发送音频数据块（通过AudioASRGateway进行VAD过滤）
                    if self.on_audio_chunk:
                        try:
                            # 通过AudioASRGateway处理音频数据
                            if self.asr_gateway:
                                final_data = self.asr_gateway.process(processed_audio)
                                # 只发送非None的数据（None表示静音，不发送）
                                if final_data is not None:
                                    self.on_audio_chunk(final_data)
                            else:
                                # AudioASRGateway未初始化，直接发送处理后的数据
                                self.on_audio_chunk(processed_audio)
                        except Exception as e:
                            logger.error(f"[音频] 音频数据块回调错误: {e}", exc_info=True)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"[音频] 消费音频数据时出错: {e}", exc_info=True)
                continue
        
        logger.info(f"[音频] 音频消费线程结束，共消费 {consumed_chunks} 个音频块")
        if self._buffer_cleanups > 0:
            logger.info(f"[音频] 缓冲区清理统计: 共清理 {self._buffer_cleanups} 次")
        
        # 输出AudioASRGateway统计信息（如果启用VAD）
        if self.asr_gateway and self.asr_gateway.enabled:
            stats = self.asr_gateway.get_stats()
            logger.info(f"[AudioASRGateway] 统计: 总帧数={stats['total_frames']}, "
                       f"语音帧={stats['speech_frames']}, "
                       f"过滤帧={stats['filtered_frames']}, "
                       f"过滤率={stats['filter_rate']:.1f}%")
    
    def set_asr_gateway_callbacks(self, 
                                  on_speech_start: Optional[Callable[[], None]] = None,
                                  on_speech_end: Optional[Callable[[], None]] = None):
        """
        设置AudioASRGateway的ASR控制回调函数
        
        Args:
            on_speech_start: 语音开始回调（应启动ASR）
            on_speech_end: 语音结束回调（应停止ASR）
        """
        if self.asr_gateway:
            self.asr_gateway.set_callbacks(on_speech_start, on_speech_end)
            logger.debug("[音频] AudioASRGateway回调已设置")
    
    def set_on_audio_chunk_callback(self, callback: Optional[Callable[[bytes], None]]):
        """设置音频数据块回调函数（用于流式 ASR）"""
        if callback:
            logger.info("[音频] 已设置音频数据块回调函数（用于流式 ASR）")
        else:
            logger.info("[音频] 已清除音频数据块回调函数")
        self.on_audio_chunk = callback
