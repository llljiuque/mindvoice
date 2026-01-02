"""
VAD过滤器 - 集成WebRTC VAD，过滤静音音频

本模块实现基于WebRTC VAD的语音活动检测，通过过滤静音音频来降低ASR调用成本。
主要特性：
1. 帧拆分：将200ms音频块拆分为20ms小帧进行检测
2. 状态机管理：SILENCE ↔ SPEECH 状态转换
3. 缓冲机制：前置/后置缓冲避免语音截断
4. 统计信息：记录过滤率等关键指标
"""
import logging
import webrtcvad
from collections import deque
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class VADState(Enum):
    """VAD状态枚举"""
    SILENCE = "silence"  # 静音状态
    SPEECH = "speech"    # 语音状态


class VADFilter:
    """
    VAD过滤器 - 使用WebRTC VAD进行语音活动检测
    
    工作原理：
    1. 将200ms音频块拆分为10个20ms小帧
    2. 对每个20ms帧进行VAD检测
    3. 使用状态机管理语音/静音转换
    4. 通过前后缓冲机制避免截断
    5. 只发送包含语音的音频数据
    
    设计目标：
    - 过滤60-80%的静音音频
    - 节约40-60%的ASR成本
    - 延迟增加 < 20ms
    - 无语音截断问题
    """
    
    def __init__(self, config: dict):
        """
        初始化VAD过滤器
        
        Args:
            config: VAD配置字典
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
        
        if not self.enabled:
            logger.info("[VAD] VAD功能未启用")
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
        
        logger.info("[VAD] 初始化成功")
        logger.info(f"[VAD] 配置: mode={vad_mode}, 帧长={self.frame_duration_ms}ms, "
                   f"开始阈值={self.speech_start_threshold}, 结束阈值={self.speech_end_threshold}")
        logger.info(f"[VAD] 缓冲: 前置={pre_padding_ms}ms({self.pre_buffer_frames}帧), "
                   f"后置={post_padding_ms}ms({self.post_buffer_frames}帧)")
    
    def process(self, audio_data: bytes) -> Optional[bytes]:
        """
        处理音频数据，返回过滤后的数据
        
        处理流程：
        1. 将200ms音频块添加到输入缓冲区
        2. 从缓冲区中提取20ms帧进行VAD检测
        3. 根据检测结果更新状态机
        4. 返回应该发送的音频数据（或None表示全部静音）
        
        Args:
            audio_data: 原始音频数据（通常为200ms块，6400字节）
        
        Returns:
            Optional[bytes]: 过滤后的音频数据
                - bytes: 包含语音的音频数据
                - None: 全部为静音，不发送
        """
        # 如果VAD未启用，直接返回原始数据
        if not self.enabled:
            return audio_data
        
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
            logger.error(f"[VAD] 检测失败: {e}")
            # 检测失败时假定为语音，避免丢失数据
            return True
    
    def _update_state(self, is_speech: bool, frame: bytes) -> Optional[bytes]:
        """
        更新VAD状态机
        
        状态转换逻辑：
        SILENCE → SPEECH: 连续检测到N个语音帧（speech_start_threshold）
        SPEECH → SILENCE: 连续检测到M个静音帧（speech_end_threshold）
        
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
                    logger.debug("[VAD] 语音开始")
                    self.state = VADState.SPEECH
                    
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
                    logger.debug(f"[VAD] 语音结束 (过滤率: {self.get_filter_rate():.1f}%)")
                    self.state = VADState.SILENCE
                    self.speech_frame_count = 0
                    self.silence_frame_count = 0
                    self.post_speech_counter = 0
                    return frame  # 发送最后一帧
                else:
                    # 还未满足结束条件
                    return frame
    
    def get_stats(self) -> dict:
        """
        获取VAD统计信息
        
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
        重置VAD状态
        
        在开始新的录音会话时调用，清空所有缓冲区和计数器
        """
        self.state = VADState.SILENCE
        self.input_buffer.clear()
        self.pre_buffer.clear()
        self.speech_frame_count = 0
        self.silence_frame_count = 0
        self.post_speech_counter = 0
        logger.debug("[VAD] 状态已重置")

