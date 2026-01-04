"""
音频处理模块 - 使用 WebRTC Audio Processing

提供完整的音频处理功能：
- AGC (Automatic Gain Control) - 自动增益控制
- NS (Noise Suppression) - 噪声抑制
- VAD (Voice Activity Detection) - 语音活动检测

支持两种模式：
1. WebRTC APM (首选，需要安装 webrtc-audio-processing)
2. 简化版 (备用，纯 Python 实现)
"""
import logging
import numpy as np
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class AudioProcessor:
    """
    音频处理器
    
    自动尝试使用 WebRTC APM，如果不可用则使用简化版实现
    """
    
    def __init__(self, 
                 sample_rate: int = 16000,
                 channels: int = 1,
                 enable_agc: bool = True,
                 enable_ns: bool = True,
                 agc_level: int = 2,
                 ns_level: int = 2):
        """
        初始化音频处理器
        
        Args:
            sample_rate: 采样率 (Hz)
            channels: 声道数 (1=单声道, 2=立体声)
            enable_agc: 是否启用自动增益控制
            enable_ns: 是否启用噪声抑制
            agc_level: AGC 级别 (0-3, 0=最小, 3=最大)
            ns_level: NS 级别 (0-3, 0=最小, 3=最大)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.enable_agc = enable_agc
        self.enable_ns = enable_ns
        self.agc_level = agc_level
        self.ns_level = ns_level
        
        # 尝试使用 WebRTC APM
        self.apm = None
        self.use_webrtc = False
        
        try:
            from webrtc_audio_processing import AudioProcessingModule as AP
            self.apm = AP(
                enable_ns=enable_ns,
                enable_agc=enable_agc,
                enable_aec=False  # 不需要回声消除（非通话场景）
            )
            self.apm.set_stream_format(sample_rate, channels)
            if enable_agc:
                self.apm.set_agc_level(agc_level)
            if enable_ns:
                self.apm.set_ns_level(ns_level)
            
            self.use_webrtc = True
            logger.info(f"[AudioProcessor] 使用 WebRTC APM (AGC={enable_agc}, NS={enable_ns})")
        except ImportError:
            logger.warning("[AudioProcessor] WebRTC APM 不可用，使用简化版实现")
            self._init_fallback()
    
    def _init_fallback(self):
        """初始化简化版实现（纯 Python）"""
        # AGC 参数
        self.target_rms = 3000  # 目标 RMS 值
        self.current_gain = 1.0
        self.gain_smooth_factor = 0.1  # 增益平滑系数
        
        # 噪声门限（简单的噪声抑制）
        self.noise_gate_threshold = 500  # RMS 阈值
        
        logger.info(f"[AudioProcessor] 使用简化版实现 (AGC={self.enable_agc}, NS={self.enable_ns})")
    
    def process(self, audio_data: bytes) -> bytes:
        """
        处理音频数据
        
        Args:
            audio_data: 原始音频数据 (16-bit PCM)
        
        Returns:
            bytes: 处理后的音频数据
        """
        if self.use_webrtc and self.apm:
            return self._process_webrtc(audio_data)
        else:
            return self._process_fallback(audio_data)
    
    def _process_webrtc(self, audio_data: bytes) -> bytes:
        """使用 WebRTC APM 处理"""
        try:
            processed = self.apm.process_stream(audio_data)
            return processed
        except Exception as e:
            logger.error(f"[AudioProcessor] WebRTC 处理失败: {e}")
            return audio_data
    
    def _process_fallback(self, audio_data: bytes) -> bytes:
        """使用简化版实现处理"""
        # 转换为 numpy 数组
        audio = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
        
        # 应用 AGC
        if self.enable_agc:
            audio = self._apply_agc(audio)
        
        # 应用噪声门限
        if self.enable_ns:
            audio = self._apply_noise_gate(audio)
        
        # 转换回 bytes
        audio = np.clip(audio, -32768, 32767).astype(np.int16)
        return audio.tobytes()
    
    def _apply_agc(self, audio: np.ndarray) -> np.ndarray:
        """
        应用自动增益控制（简化版）
        
        原理：
        1. 计算当前帧的 RMS（均方根）
        2. 根据目标 RMS 计算需要的增益
        3. 平滑调整增益（避免突变）
        4. 应用增益到音频
        """
        # 计算当前 RMS
        rms = np.sqrt(np.mean(audio ** 2))
        
        if rms > 0:
            # 计算目标增益
            target_gain = self.target_rms / rms
            
            # 限制增益范围（避免过度放大或衰减）
            target_gain = np.clip(target_gain, 0.1, 10.0)
            
            # 平滑调整增益
            self.current_gain = (
                self.gain_smooth_factor * target_gain +
                (1 - self.gain_smooth_factor) * self.current_gain
            )
            
            # 应用增益
            audio = audio * self.current_gain
        
        return audio
    
    def _apply_noise_gate(self, audio: np.ndarray) -> np.ndarray:
        """
        应用噪声门限（简化版噪声抑制）
        
        原理：
        1. 计算当前帧的 RMS
        2. 如果低于阈值，认为是噪声，大幅衰减
        3. 如果高于阈值，正常通过
        """
        rms = np.sqrt(np.mean(audio ** 2))
        
        if rms < self.noise_gate_threshold:
            # 低于阈值，衰减 80%
            audio = audio * 0.2
        
        return audio
    
    def get_stats(self) -> dict:
        """
        获取处理器统计信息
        
        Returns:
            dict: 统计信息
        """
        return {
            'use_webrtc': self.use_webrtc,
            'enable_agc': self.enable_agc,
            'enable_ns': self.enable_ns,
            'sample_rate': self.sample_rate,
            'current_gain': getattr(self, 'current_gain', None)
        }


def create_audio_processor(config: dict) -> Optional[AudioProcessor]:
    """
    从配置创建音频处理器
    
    Args:
        config: 配置字典，应包含：
            - sample_rate: 采样率
            - channels: 声道数
            - audio_processing.enable_agc: 是否启用 AGC
            - audio_processing.enable_ns: 是否启用 NS
            - audio_processing.agc_level: AGC 级别 (0-3)
            - audio_processing.ns_level: NS 级别 (0-3)
    
    Returns:
        AudioProcessor: 音频处理器实例，如果禁用则返回 None
    """
    # 检查是否启用音频处理
    if not config.get('audio_processing', {}).get('enabled', False):
        logger.info("[AudioProcessor] 音频处理已禁用")
        return None
    
    try:
        processor = AudioProcessor(
            sample_rate=config.get('sample_rate', 16000),
            channels=config.get('channels', 1),
            enable_agc=config.get('audio_processing', {}).get('enable_agc', True),
            enable_ns=config.get('audio_processing', {}).get('enable_ns', True),
            agc_level=config.get('audio_processing', {}).get('agc_level', 2),
            ns_level=config.get('audio_processing', {}).get('ns_level', 2)
        )
        return processor
    except Exception as e:
        logger.error(f"[AudioProcessor] 创建失败: {e}", exc_info=True)
        return None

