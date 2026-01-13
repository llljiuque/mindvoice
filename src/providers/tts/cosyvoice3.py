"""
Fun-CosyVoice3 TTS 提供商实现
基于 ModelScope 的 Fun-CosyVoice3-0.5B-2512 模型
"""
import asyncio
import os
from typing import Dict, Any, Optional, AsyncIterator
from pathlib import Path
import io

# 条件导入，避免依赖缺失时阻止服务器启动
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False
    sf = None

from .base_tts import BaseTTSProvider
from ...core.logger import get_logger

logger = get_logger("TTS.CosyVoice3")

# 分别检查 ModelScope 和 FunASR 的可用性
try:
    from modelscope import snapshot_download
    MODELSCOPE_AVAILABLE = True
except ImportError:
    MODELSCOPE_AVAILABLE = False
    logger.warning("ModelScope 未安装，Fun-CosyVoice3 TTS 将不可用")

try:
    # 先检查torch是否可用（funasr的依赖）
    try:
        import torch
    except (ImportError, OSError) as e:
        raise ImportError(f"torch未安装或加载失败，funasr需要torch作为依赖: {e}")
    
    # 导入funasr
    from funasr import AutoModel
    FUNASR_AVAILABLE = True
except (ImportError, OSError) as e:
    FUNASR_AVAILABLE = False
    AutoModel = None
    logger.warning(f"FunASR 未安装或依赖缺失，Fun-CosyVoice3 TTS 将不可用: {e}")


class CosyVoice3Provider(BaseTTSProvider):
    """Fun-CosyVoice3 TTS 提供商"""
    
    PROVIDER_NAME = "cosyvoice3"
    DISPLAY_NAME = "Fun-CosyVoice3"
    DESCRIPTION = "基于ModelScope的Fun-CosyVoice3模型，支持流式合成、多语言和零样本音色克隆"
    
    def __init__(self):
        super().__init__()
        self.model = None
        self.model_dir = None
        self._default_voice = None
    
    @property
    def name(self) -> str:
        return "cosyvoice3"
    
    @property
    def supported_languages(self) -> list[str]:
        return ["zh-CN", "en-US", "ja-JP", "ko-KR"]
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化 Fun-CosyVoice3 模型"""
        if not MODELSCOPE_AVAILABLE:
            logger.error("ModelScope 未安装，无法初始化 CosyVoice3")
            return False
        
        if not FUNASR_AVAILABLE:
            logger.error("FunASR 未安装，无法初始化 CosyVoice3")
            return False
        
        if not NUMPY_AVAILABLE:
            logger.error("numpy 未安装，无法初始化 CosyVoice3")
            return False
        
        if not SOUNDFILE_AVAILABLE:
            logger.error("soundfile 未安装，无法初始化 CosyVoice3")
            return False
        
        try:
            # ========== 添加 CosyVoice 代码路径到 sys.path ==========
            import sys
            from pathlib import Path
            
            # 获取项目根目录（从当前文件向上4级）
            # src/providers/tts/cosyvoice3.py -> src/providers/tts -> src/providers -> src -> 项目根目录
            project_root = Path(__file__).parent.parent.parent.parent
            
            # CosyVoice 仓库路径（注意：ZIP 下载后目录名是 CosyVoice-main）
            cosyvoice_dir = project_root / 'third_party' / 'CosyVoice-main'
            
            # Matcha-TTS 子模块路径（如果存在）
            matcha_dir = cosyvoice_dir / 'third_party' / 'Matcha-TTS'
            
            # 添加路径到 sys.path（如果存在）
            paths_added = []
            
            if cosyvoice_dir.exists():
                cosyvoice_str = str(cosyvoice_dir.resolve())
                if cosyvoice_str not in sys.path:
                    sys.path.insert(0, cosyvoice_str)
                    paths_added.append(cosyvoice_str)
                    logger.info(f"[TTS] 已添加 CosyVoice 路径: {cosyvoice_str}")
            else:
                logger.warning(f"[TTS] CosyVoice 目录不存在: {cosyvoice_dir}")
                logger.warning("[TTS] 请确保已下载 CosyVoice 仓库到 third_party/CosyVoice-main")
            
            if matcha_dir.exists():
                matcha_str = str(matcha_dir.resolve())
                if matcha_str not in sys.path:
                    sys.path.insert(0, matcha_str)
                    paths_added.append(matcha_str)
                    logger.info(f"[TTS] 已添加 Matcha-TTS 路径: {matcha_str}")
            else:
                logger.debug(f"[TTS] Matcha-TTS 子模块不存在（可选）: {matcha_dir}")
            
            # 验证路径是否生效
            if paths_added:
                logger.debug(f"[TTS] 已添加 {len(paths_added)} 个路径到 sys.path")
            # ========== 路径添加完成 ==========
            
            # 从配置获取模型路径或模型ID
            model_id = config.get("model_id", "FunAudioLLM/Fun-CosyVoice3-0.5B-2512")
            model_dir = config.get("model_dir")
            device = config.get("device", "cpu")  # cpu 或 cuda
            cache_dir = config.get("cache_dir", os.path.expanduser("~/.cache/modelscope"))
            
            # 先下载模型到本地，然后使用本地路径加载
            # AutoModel 可能不支持直接使用模型ID，需要使用本地路径
            if model_dir and Path(model_dir).exists():
                # 使用指定的本地路径
                self.model_dir = str(Path(model_dir).resolve())
                logger.info(f"[TTS] 使用指定的本地模型路径: {self.model_dir}")
            else:
                # 从 ModelScope 下载模型到本地
                logger.info(f"[TTS] 正在从 ModelScope 下载模型: {model_id}")
                cache_dir_abs = str(Path(cache_dir).expanduser().resolve())
                downloaded_path = snapshot_download(
                    model_id,
                    cache_dir=cache_dir_abs
                )
                # 处理下载路径
                model_path = Path(downloaded_path)
                if not model_path.is_absolute():
                    model_path = Path(str(model_path).replace('~', str(Path.home()))).resolve()
                else:
                    model_path = model_path.expanduser().resolve()
                
                # 如果路径不存在，尝试查找实际下载的目录（Windows路径转换问题）
                if not model_path.exists():
                    cache_path = Path(cache_dir_abs)
                    possible_dirs = list(cache_path.rglob('Fun-CosyVoice3*'))
                    if possible_dirs:
                        # 选择最完整的目录（通常是hub/models下的）
                        model_path = max(possible_dirs, key=lambda p: len(str(p)))
                        logger.info(f"[TTS] 找到实际下载路径: {model_path}")
                
                # 确保使用绝对路径
                self.model_dir = str(model_path.resolve() if model_path.exists() else model_path)
                logger.info(f"[TTS] 模型下载完成: {self.model_dir}")
                logger.debug(f"[TTS] 模型路径（验证）: {Path(self.model_dir).exists()}")
            
            # 验证路径存在
            if not Path(self.model_dir).exists():
                raise FileNotFoundError(f"模型路径不存在: {self.model_dir}")
            
            # 初始化模型
            # 根据官方文档和测试，CosyVoice3 需要使用本地路径，并指定 hub='ms'
            # 注意：可能需要将 CosyVoice 代码路径添加到 sys.path（如果需要）
            logger.info(f"[TTS] 正在加载 Fun-CosyVoice3 模型...")
            logger.debug(f"[TTS] 模型路径: {self.model_dir}")
            
            # 尝试多种加载方式
            model_loaded = False
            last_error = None
            
            # 方式1: 使用本地路径 + hub='ms'（推荐方式）
            if not model_loaded:
                try:
                    logger.debug("[TTS] 尝试方式1: 本地路径 + hub='ms'")
                    self.model = AutoModel(
                        model=self.model_dir,
                        device=device,
                        hub='ms'  # 指定使用 ModelScope hub
                    )
                    model_loaded = True
                    logger.info("[TTS] 模型加载成功（方式1：本地路径 + hub='ms'）")
                except Exception as e:
                    last_error = e
                    logger.debug(f"[TTS] 方式1失败: {e}")
            
            # 方式2: 使用本地路径 + trust_remote_code
            if not model_loaded:
                try:
                    logger.debug("[TTS] 尝试方式2: 本地路径 + trust_remote_code=True")
                    self.model = AutoModel(
                        model=self.model_dir,
                        trust_remote_code=True,
                        device=device
                    )
                    model_loaded = True
                    logger.info("[TTS] 模型加载成功（方式2）")
                except Exception as e:
                    last_error = e
                    logger.debug(f"[TTS] 方式2失败: {e}")
            
            # 方式3: 使用模型ID + hub='ms'
            if not model_loaded:
                try:
                    logger.debug("[TTS] 尝试方式3: 模型ID + hub='ms'")
                    self.model = AutoModel(
                        model=model_id,
                        device=device,
                        hub='ms'
                    )
                    model_loaded = True
                    logger.info("[TTS] 模型加载成功（方式3）")
                except Exception as e:
                    last_error = e
                    logger.debug(f"[TTS] 方式3失败: {e}")
            
            # 方式4: 只使用本地路径（最后尝试）
            if not model_loaded:
                try:
                    logger.debug("[TTS] 尝试方式4: 仅本地路径")
                    self.model = AutoModel(
                        model=self.model_dir,
                        device=device
                    )
                    model_loaded = True
                    logger.info("[TTS] 模型加载成功（方式4）")
                except Exception as e:
                    last_error = e
                    logger.debug(f"[TTS] 方式4失败: {e}")
            
            if not model_loaded:
                error_msg = f"所有加载方式都失败，最后错误: {last_error}"
                logger.error(f"[TTS] {error_msg}")
                logger.error("[TTS] 提示：CosyVoice3 可能需要安装额外的依赖或代码库")
                logger.error("[TTS] 请参考: https://github.com/FunAudioLLM/CosyVoice")
                raise RuntimeError(error_msg)
            
            # 设置默认音色（如果有）
            self._default_voice = config.get("default_voice")
            
            self._initialized = True
            logger.info("[TTS] Fun-CosyVoice3 模型初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"[TTS] Fun-CosyVoice3 初始化失败: {e}", exc_info=True)
            self._initialized = False
            return False
    
    async def synthesize(self, text: str, language: str = "zh-CN", voice: Optional[str] = None,
                        speed: float = 1.0, **kwargs) -> bytes:
        """合成语音（非流式）"""
        if not self.is_available():
            raise RuntimeError("TTS provider not initialized")
        
        # 在事件循环中运行同步代码
        loop = asyncio.get_event_loop()
        audio_data, sample_rate = await loop.run_in_executor(
            None,
            self._synthesize_sync,
            text,
            language,
            voice or self._default_voice,
            speed,
            **kwargs
        )
        
        # 转换为 WAV 格式字节流
        wav_bytes = self._audio_to_wav_bytes(audio_data, sample_rate=sample_rate)
        return wav_bytes
    
    async def synthesize_stream(self, text: str, language: str = "zh-CN", voice: Optional[str] = None,
                               speed: float = 1.0, **kwargs) -> AsyncIterator[bytes]:
        """流式合成语音"""
        if not self.is_available():
            raise RuntimeError("TTS provider not initialized")
        
        # Fun-CosyVoice3 支持流式输出
        # 将文本分块处理，逐步生成音频
        chunk_size = kwargs.get("chunk_size", 50)  # 每次处理50个字符
        
        for i in range(0, len(text), chunk_size):
            chunk_text = text[i:i + chunk_size]
            if not chunk_text.strip():
                continue
            
            # 合成当前块的音频
            audio_data = await self.synthesize(
                chunk_text,
                language=language,
                voice=voice,
                speed=speed,
                **kwargs
            )
            
            yield audio_data
    
    async def list_voices(self, language: Optional[str] = None) -> list[Dict[str, Any]]:
        """列出可用的音色"""
        if not self.is_available():
            return []
        
        # Fun-CosyVoice3 支持零样本语音克隆
        # 这里返回默认音色列表
        voices = [
            {
                "id": "default",
                "name": "默认音色",
                "language": "zh-CN",
                "gender": "neutral"
            }
        ]
        
        # 如果指定了语言，过滤音色
        if language:
            voices = [v for v in voices if v["language"] == language]
        
        return voices
    
    def _synthesize_sync(self, text: str, language: str, voice: Optional[str],
                        speed: float, **kwargs):
        """同步合成语音（内部方法）
        
        Returns:
            tuple: (audio_data, sample_rate) 音频数据和采样率
        """
        if not NUMPY_AVAILABLE:
            raise RuntimeError("numpy 未安装，无法进行语音合成")
        
        try:
            # 调用 Fun-CosyVoice3 模型进行语音合成
            # 根据官方文档，generate 方法返回格式为: res[0]['wav'] 和 res[0]['sample_rate']
            ref_audio = kwargs.get("ref_audio")
            
            if ref_audio:
                # 零样本语音克隆模式
                result = self.model.generate(
                    input=text,
                    voice=ref_audio,
                    language=language
                )
            else:
                # 默认音色模式
                result = self.model.generate(
                    input=text,
                    language=language
                )
            
            # 根据官方 API，返回格式是列表，第一个元素是字典
            # res[0]['wav'] 是音频数据，res[0]['sample_rate'] 是采样率
            if isinstance(result, list) and len(result) > 0:
                if isinstance(result[0], dict):
                    audio_data = result[0].get("wav")
                    sample_rate = result[0].get("sample_rate", 24000)  # 默认 24000 Hz
                else:
                    # 如果第一个元素不是字典，尝试直接使用
                    audio_data = result[0]
                    sample_rate = 24000
            elif isinstance(result, dict):
                # 兼容直接返回字典的情况
                audio_data = result.get("wav", result.get("audio"))
                sample_rate = result.get("sample_rate", 24000)
            elif isinstance(result, np.ndarray):
                # 兼容直接返回 numpy 数组的情况
                audio_data = result
                sample_rate = 24000
            else:
                raise ValueError(f"无法识别的返回格式: {type(result)}")
            
            if audio_data is None:
                raise ValueError("无法从模型输出中提取音频数据")
            
            # 确保是 numpy 数组
            if not isinstance(audio_data, np.ndarray):
                audio_data = np.array(audio_data)
            
            # 应用语速调整（如果需要）
            if speed != 1.0:
                try:
                    from scipy import signal
                    num_samples = int(len(audio_data) / speed)
                    audio_data = signal.resample(audio_data, num_samples)
                except ImportError:
                    logger.warning(f"[TTS] scipy 未安装，无法调整语速，使用原始语速")
            
            return audio_data, sample_rate
            
        except Exception as e:
            logger.error(f"[TTS] 语音合成失败: {e}", exc_info=True)
            raise
    
    def _audio_to_wav_bytes(self, audio_data, sample_rate: int = 24000) -> bytes:
        """将音频数组转换为 WAV 格式字节流"""
        if not NUMPY_AVAILABLE or not SOUNDFILE_AVAILABLE:
            raise RuntimeError("numpy 或 soundfile 未安装，无法转换音频格式")
        
        # 确保音频数据是 float32 格式，范围在 [-1, 1]
        if audio_data.dtype != np.float32:
            if audio_data.dtype == np.int16:
                audio_data = audio_data.astype(np.float32) / 32768.0
            else:
                audio_data = audio_data.astype(np.float32)
        
        # 确保是单声道
        if len(audio_data.shape) > 1:
            audio_data = audio_data[:, 0] if audio_data.shape[1] > 0 else audio_data.flatten()
        
        # 写入内存中的 WAV 文件
        wav_buffer = io.BytesIO()
        sf.write(wav_buffer, audio_data, sample_rate, format='WAV', subtype='PCM_16')
        wav_bytes = wav_buffer.getvalue()
        wav_buffer.close()
        
        return wav_bytes
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self._initialized and self.model is not None
