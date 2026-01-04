"""
AudioASRGateway - Audio到ASR的网关控制器

本模块作为Audio和ASR之间的统一网关，负责：
1. 语音活动检测（VAD，当启用时）
2. 控制ASR的启停（根据语音活动）
3. 音频流过滤和转发

架构设计：
Audio → AudioASRGateway → ASR
        ↑
    统一网关层：
    - enabled: 检测语音，动态控制ASR启停
    - disabled: 持续输出有效信号，ASR持续运行

主要特性：
1. 帧拆分：将200ms音频块拆分为20ms小帧进行检测
2. 状态机管理：SILENCE ↔ SPEECH 状态转换
3. 缓冲机制：前置/后置缓冲避免语音截断
4. ASR控制：通过回调机制控制ASR启停
5. 统计信息：记录过滤率等关键指标
"""
import logging
import webrtcvad
from collections import deque
from enum import Enum
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class VADState(Enum):
    """VAD状态枚举"""
    SILENCE = "silence"  # 静音状态
    SPEECH = "speech"    # 语音状态


class AudioASRGateway:
    """
    Audio到ASR的网关控制器
    
    工作原理：
    1. 当 enabled=True: 
       - 检测语音活动
       - 检测到语音 → 触发 on_speech_start → 启动ASR
       - 检测到静音 → 触发 on_speech_end → 停止ASR
       - 只传递包含语音的音频数据
    
    2. 当 enabled=False:
       - 持续输出有效信号
       - 初始化时立即触发 on_speech_start → 启动ASR
       - 传递所有音频数据（不过滤）
       - 直到 stop() 被调用才触发 on_speech_end
    
    设计目标：
    - 统一Audio和ASR之间的控制流
    - 当VAD启用时，节约40-60%的ASR成本
    - 延迟增加 < 20ms
    - 无语音截断问题
    """
    
    def __init__(self, config: dict):
        """
        初始化AudioASRGateway
        
        Args:
            config: 配置字典
                - enabled: 是否启用VAD（默认False）
                - mode: WebRTC VAD敏感度，0-3（默认2，0最宽松，3最严格）
                - frame_duration_ms: 检测帧长度，10/20/30ms（默认20ms）
                - speech_start_threshold: 语音开始阈值，连续N个块（默认2）
                - speech_end_threshold: 语音结束阈值，连续M个块（默认10）
                - min_speech_duration_ms: 最小语音时长（默认200ms）
                - pre_speech_padding_ms: 前置缓冲时长（默认100ms）
                - post_speech_padding_ms: 后置缓冲时长（默认300ms）
        """
        self.enabled = config.get('enabled', False)
        
        # ASR控制回调
        self._on_speech_start: Optional[Callable[[], None]] = None
        self._on_speech_end: Optional[Callable[[], None]] = None
        
        # 工作状态标志
        self._is_active = False
        self._speech_active = False  # 当前是否处于语音状态（enabled=False时始终为True）
        
        if not self.enabled:
            logger.info("[AudioASRGateway] VAD未启用，将作为直通网关运行")
            return
        
        # VAD核心参数
        vad_mode = config.get('mode', 2)
        self.vad = webrtcvad.Vad(vad_mode)
        self.frame_duration_ms = config.get('frame_duration_ms', 20)
        
        # 计算帧字节数：16kHz采样率 × 帧时长(秒) × 2字节/样本(16bit)
        self.frame_bytes = int(16000 * self.frame_duration_ms / 1000 * 2)
        
        # 检测阈值参数
        self.speech_start_threshold = config.get('speech_start_threshold', 2)
        self.speech_end_threshold = config.get('speech_end_threshold', 10)
        self.min_speech_duration_ms = config.get('min_speech_duration_ms', 200)
        
        # 缓冲机制参数
        pre_padding_ms = config.get('pre_speech_padding_ms', 100)
        post_padding_ms = config.get('post_speech_padding_ms', 300)
        
        # 计算缓冲帧数
        self.pre_buffer_frames = int(pre_padding_ms / self.frame_duration_ms)
        self.post_buffer_frames = int(post_padding_ms / self.frame_duration_ms)
        
        # 状态管理
        self.state = VADState.SILENCE
        self.input_buffer = bytearray()  # 输入缓冲区：用于帧拆分
        self.pre_buffer = deque(maxlen=self.pre_buffer_frames)  # 前置缓冲区
        
        # 状态计数器
        self.speech_frame_count = 0     # 连续语音帧计数
        self.silence_frame_count = 0    # 连续静音帧计数
        self.post_speech_counter = 0    # 语音后静音计数
        
        # 统计信息
        self.total_frames = 0      # 总处理帧数
        self.speech_frames = 0     # 语音帧数
        self.filtered_frames = 0   # 过滤（静音）帧数
        
        logger.info("[AudioASRGateway] 初始化成功（VAD启用）")
        logger.info(f"[AudioASRGateway] 配置: mode={vad_mode}, 帧长={self.frame_duration_ms}ms, "
                   f"开始阈值={self.speech_start_threshold}, 结束阈值={self.speech_end_threshold}")
        logger.info(f"[AudioASRGateway] 缓冲: 前置={pre_padding_ms}ms({self.pre_buffer_frames}帧), "
                   f"后置={post_padding_ms}ms({self.post_buffer_frames}帧)")
    
    def set_callbacks(self, 
                     on_speech_start: Optional[Callable[[], None]] = None,
                     on_speech_end: Optional[Callable[[], None]] = None):
        """
        设置ASR控制回调函数
        
        Args:
            on_speech_start: 语音开始回调（应启动ASR）
            on_speech_end: 语音结束回调（应停止ASR）
        """
        self._on_speech_start = on_speech_start
        self._on_speech_end = on_speech_end
        logger.debug("[AudioASRGateway] 回调函数已设置")
    
    def start(self):
        """
        开始工作
        
        当 enabled=False 时，立即触发 on_speech_start 以启动ASR
        当 enabled=True 时，等待检测到语音后再触发
        """
        if self._is_active:
            logger.warning("[AudioASRGateway] 已在运行中")
            return
        
        self._is_active = True
        
        if not self.enabled:
            # VAD未启用：立即启动ASR（持续有效信号模式）
            logger.info("[AudioASRGateway] 开始工作（直通模式，立即启动ASR）")
            self._speech_active = True
            if self._on_speech_start:
                try:
                    self._on_speech_start()
                    logger.debug("[AudioASRGateway] 已触发 on_speech_start 回调")
                except Exception as e:
                    logger.error(f"[AudioASRGateway] 触发 on_speech_start 回调失败: {e}", exc_info=True)
        else:
            # VAD启用：重置状态，等待检测到语音
            logger.info("[AudioASRGateway] 开始工作（VAD模式，等待语音）")
            self.reset()
    
    def stop(self):
        """
        停止工作
        
        触发 on_speech_end 以停止ASR
        """
        if not self._is_active:
            logger.warning("[AudioASRGateway] 未在运行中")
            return
        
        self._is_active = False
        
        if self._speech_active and self._on_speech_end:
            logger.info("[AudioASRGateway] 停止工作，触发 on_speech_end 回调")
            self._speech_active = False
            try:
                self._on_speech_end()
                logger.debug("[AudioASRGateway] 已触发 on_speech_end 回调")
            except Exception as e:
                logger.error(f"[AudioASRGateway] 触发 on_speech_end 回调失败: {e}", exc_info=True)
    
    def process(self, audio_data: bytes) -> Optional[bytes]:
        """
        处理音频数据，返回应该传递给ASR的数据
        
        处理流程：
        1. 当 enabled=False: 直接返回原始数据（直通模式）
        2. 当 enabled=True: 
           - 将200ms音频块拆分为20ms小帧
           - 进行VAD检测
           - 根据状态机决定是否传递数据
           - 触发相应的回调（语音开始/结束）
        
        Args:
            audio_data: 原始音频数据（通常为200ms块，6400字节）
        
        Returns:
            Optional[bytes]: 应该传递给ASR的音频数据
                - bytes: 包含语音的音频数据（应传递给ASR）
                - None: 全部为静音，不传递给ASR（enabled=True时）
        """
        if not self._is_active:
            return None
        
        # VAD未启用：直通模式，始终返回原始数据
        if not self.enabled:
            return audio_data
        
        # VAD启用：进行语音检测
        # 添加到输入缓冲区
        self.input_buffer.extend(audio_data)
        
        # 处理完整的20ms帧
        result = bytearray()
        while len(self.input_buffer) >= self.frame_bytes:
            # 提取一个完整的帧
            frame = bytes(self.input_buffer[:self.frame_bytes])
            self.input_buffer = self.input_buffer[self.frame_bytes:]
            
            # VAD检测
            is_speech = self._detect_speech(frame)
            
            # 状态机处理
            processed_frame = self._update_state(is_speech, frame)
            if processed_frame:
                result.extend(processed_frame)
            
            self.total_frames += 1
        
        # 返回处理结果
        return bytes(result) if result else None
    
    def _detect_speech(self, frame: bytes) -> bool:
        """
        检测单个帧是否包含语音
        
        Args:
            frame: 音频帧数据（20ms，640字节）
        
        Returns:
            bool: True表示包含语音，False表示静音
        """
        try:
            return self.vad.is_speech(frame, 16000)
        except Exception as e:
            logger.error(f"[AudioASRGateway] 检测失败: {e}")
            # 检测失败时假定为语音，避免丢失数据
            return True
    
    def _update_state(self, is_speech: bool, frame: bytes) -> Optional[bytes]:
        """
        更新VAD状态机，并触发相应的回调
        
        状态转换逻辑：
        SILENCE → SPEECH: 连续检测到N个语音帧（speech_start_threshold）
           → 触发 on_speech_start
        SPEECH → SILENCE: 连续检测到M个静音帧（speech_end_threshold）
           → 触发 on_speech_end
        
        Args:
            is_speech: 当前帧是否为语音
            frame: 当前帧数据
        
        Returns:
            Optional[bytes]: 应该发送的音频数据（可能包含缓冲区数据）
        """
        if is_speech:
            # 检测到语音
            self.speech_frames += 1
            self.speech_frame_count += 1
            self.silence_frame_count = 0
            
            if self.state == VADState.SILENCE:
                # 当前处于静音状态
                if self.speech_frame_count >= self.speech_start_threshold:
                    # 满足语音开始条件：连续N个语音帧
                    logger.debug("[AudioASRGateway] 检测到语音开始")
                    self.state = VADState.SPEECH
                    self._speech_active = True
                    
                    # 触发回调：启动ASR
                    if self._on_speech_start:
                        try:
                            self._on_speech_start()
                            logger.debug("[AudioASRGateway] 已触发 on_speech_start 回调")
                        except Exception as e:
                            logger.error(f"[AudioASRGateway] 触发 on_speech_start 回调失败: {e}", exc_info=True)
                    
                    # 组装发送数据：前置缓冲区 + 当前帧
                    result = bytearray()
                    for buffered_frame in self.pre_buffer:
                        result.extend(buffered_frame)
                    result.extend(frame)
                    
                    return bytes(result)
                else:
                    # 还未满足开始条件，添加到前置缓冲区
                    self.pre_buffer.append(frame)
                    return None
            else:
                # 当前处于语音状态，继续发送
                self.post_speech_counter = 0
                return frame
        else:
            # 检测到静音
            self.filtered_frames += 1
            self.silence_frame_count += 1
            self.speech_frame_count = 0
            
            if self.state == VADState.SILENCE:
                # 保持静音状态，添加到前置缓冲区
                self.pre_buffer.append(frame)
                return None
            else:
                # 语音状态后的静音（可能是语音结束）
                self.post_speech_counter += 1
                
                if self.post_speech_counter <= self.post_buffer_frames:
                    # 在后置缓冲区范围内，继续发送（可能只是短暂停顿）
                    return frame
                elif self.silence_frame_count >= self.speech_end_threshold:
                    # 满足语音结束条件：连续M个静音帧
                    logger.debug(f"[AudioASRGateway] 检测到语音结束 (过滤率: {self.get_filter_rate():.1f}%)")
                    self.state = VADState.SILENCE
                    self._speech_active = False
                    self.speech_frame_count = 0
                    self.silence_frame_count = 0
                    self.post_speech_counter = 0
                    
                    # 触发回调：停止ASR
                    if self._on_speech_end:
                        try:
                            self._on_speech_end()
                            logger.debug("[AudioASRGateway] 已触发 on_speech_end 回调")
                        except Exception as e:
                            logger.error(f"[AudioASRGateway] 触发 on_speech_end 回调失败: {e}", exc_info=True)
                    
                    return frame  # 发送最后一帧
                else:
                    # 还未满足结束条件
                    return frame
    
    def get_stats(self) -> dict:
        """
        获取统计信息
        
        Returns:
            dict: 统计信息字典
                - total_frames: 总处理帧数
                - speech_frames: 语音帧数
                - filtered_frames: 过滤帧数
                - filter_rate: 过滤率（%）
        """
        return {
            'total_frames': self.total_frames,
            'speech_frames': self.speech_frames,
            'filtered_frames': self.filtered_frames,
            'filter_rate': self.get_filter_rate()
        }
    
    def get_filter_rate(self) -> float:
        """
        计算过滤率
        
        Returns:
            float: 过滤率（百分比，0-100）
        """
        if self.total_frames == 0:
            return 0.0
        return (self.filtered_frames / self.total_frames) * 100
    
    def reset(self):
        """
        重置状态
        
        在开始新的录音会话时调用，清空所有缓冲区和计数器
        """
        if self.enabled:
            self.state = VADState.SILENCE
            self.input_buffer.clear()
            self.pre_buffer.clear()
            self.speech_frame_count = 0
            self.silence_frame_count = 0
            self.post_speech_counter = 0
            logger.debug("[AudioASRGateway] 状态已重置")
        self._speech_active = False
    
    def is_speech_active(self) -> bool:
        """
        获取当前是否处于语音活动状态
        
        Returns:
            bool: True表示当前有语音活动（ASR应运行），False表示静音（ASR应停止）
        """
        return self._speech_active

