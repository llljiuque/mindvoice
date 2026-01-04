#!/usr/bin/env python3
"""
ASR 连接超时功能测试脚本

测试 ASR 连接时长限制功能是否正常工作。
为了快速测试，将超时时间设置为 30 秒。

使用方法：
1. 临时修改 config.yml 中的 asr.max_connection_duration 为 30
2. 运行此脚本：python test_asr_timeout.py
3. 观察 30 秒后是否自动停止并触发超时回调
4. 测试完成后恢复 config.yml 中的配置
"""

import sys
import time
import asyncio
import logging
from pathlib import Path

# 添加项目路径到 sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.config import Config
from src.services.voice_service import VoiceService
from src.utils.audio_recorder import SoundDeviceRecorder

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def test_asr_timeout():
    """测试 ASR 超时功能"""
    
    logger.info("=" * 60)
    logger.info("ASR 连接超时功能测试")
    logger.info("=" * 60)
    
    # 加载配置
    config = Config()
    max_duration = config.get('asr.max_connection_duration', 5400)
    
    logger.info(f"配置的最大连接时长: {max_duration}秒 ({max_duration//60}分钟)")
    
    if max_duration > 60:
        logger.warning("⚠️  为了快速测试，建议将 config.yml 中的 asr.max_connection_duration 设置为 30")
        response = input("是否继续测试？(y/n): ")
        if response.lower() != 'y':
            logger.info("测试取消")
            return
    
    # 初始化录音器
    vad_config = {
        'enabled': config.get('audio.vad.enabled', False),
        'mode': config.get('audio.vad.mode', 2),
        'frame_duration_ms': config.get('audio.vad.frame_duration_ms', 20),
        'speech_start_threshold': config.get('audio.vad.speech_start_threshold', 2),
        'speech_end_threshold': config.get('audio.vad.speech_end_threshold', 10),
        'min_speech_duration_ms': config.get('audio.vad.min_speech_duration_ms', 200),
        'pre_speech_padding_ms': config.get('audio.vad.pre_speech_padding_ms', 100),
        'post_speech_padding_ms': config.get('audio.vad.post_speech_padding_ms', 300)
    }
    
    audio_device = config.get('audio.device', None)
    if audio_device is not None:
        try:
            audio_device = int(audio_device)
        except (ValueError, TypeError):
            audio_device = None
    
    recorder = SoundDeviceRecorder(
        rate=config.get('audio.rate', 16000),
        channels=config.get('audio.channels', 1),
        chunk=config.get('audio.chunk', 1024),
        device=audio_device,
        vad_config=vad_config,
        audio_processing_config=config.get('audio.audio_processing'),
        max_buffer_seconds=config.get('audio.max_buffer_seconds', 60)
    )
    
    # 初始化语音服务
    voice_service = VoiceService(config)
    voice_service.set_recorder(recorder)
    
    # 超时标志
    timeout_triggered = {'value': False}
    
    # 设置回调
    def on_text_callback(text: str, is_definite: bool, time_info: dict):
        if is_definite:
            logger.info(f"✓ 收到确定utterance: {text[:50]}...")
        else:
            logger.debug(f"  中间结果: {text[:30]}...")
    
    def on_timeout_callback():
        logger.warning("🔔 超时回调触发！ASR 连接已达到最大时长")
        timeout_triggered['value'] = True
    
    voice_service.set_on_text_callback(on_text_callback)
    voice_service.set_on_timeout_callback(on_timeout_callback)
    
    # 开始录音
    logger.info("▶️  开始录音...")
    success = voice_service.start_recording(app_id='test')
    
    if not success:
        logger.error("❌ 启动录音失败")
        return
    
    logger.info("✓ 录音已启动")
    logger.info(f"⏱️  等待 {max_duration} 秒，观察是否自动停止...")
    logger.info("（您可以对着麦克风说话，观察识别结果）")
    
    try:
        # 每5秒显示一次已运行时长
        start_time = time.time()
        while True:
            time.sleep(5)
            elapsed = time.time() - start_time
            duration = voice_service.get_asr_connection_duration()
            
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            seconds = int(elapsed % 60)
            
            logger.info(f"⏱️  已运行: {hours:02d}:{minutes:02d}:{seconds:02d} | ASR连接时长: {duration}秒")
            
            # 检查是否超时
            if timeout_triggered['value']:
                logger.info("✓ 超时功能正常工作！")
                break
            
            # 检查状态
            state = voice_service.get_state()
            if state.value == 'idle':
                logger.info("✓ 录音已停止")
                break
                
    except KeyboardInterrupt:
        logger.info("\n⚠️  用户中断测试")
    finally:
        # 停止录音
        if voice_service.get_state().value == 'recording':
            logger.info("▶️  停止录音...")
            voice_service.stop_recording()
        
        # 清理资源
        voice_service.cleanup()
        
        logger.info("=" * 60)
        logger.info("测试完成")
        logger.info(f"超时回调是否触发: {'✓ 是' if timeout_triggered['value'] else '✗ 否'}")
        logger.info("=" * 60)


if __name__ == '__main__':
    test_asr_timeout()

