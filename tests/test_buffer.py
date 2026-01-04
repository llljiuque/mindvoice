#!/usr/bin/env python3
"""
音频缓冲区测试脚本
用于验证长时间录音时的缓冲区管理功能
"""

import sys
import time
import logging
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.audio_recorder import SoundDeviceRecorder
from src.core.logger import get_logger

logger = get_logger("BufferTest")

def test_buffer_management():
    """测试缓冲区管理功能"""
    print("=" * 60)
    print("音频缓冲区管理测试")
    print("=" * 60)
    print()
    
    # 创建录音器（设置较小的缓冲区用于快速测试）
    # 正常情况下是60秒，测试时使用5秒
    test_buffer_seconds = 5
    recorder = SoundDeviceRecorder(
        rate=16000,
        channels=1,
        chunk=3200,
        device=None,  # 使用默认设备
        vad_config=None,  # 不启用VAD
        max_buffer_seconds=test_buffer_seconds
    )
    
    print(f"✓ 录音器已创建")
    print(f"  - 采样率: 16000 Hz")
    print(f"  - 通道数: 1")
    print(f"  - 缓冲区限制: {test_buffer_seconds}秒")
    print(f"  - 最大缓冲大小: {recorder.max_buffer_size / 1024 / 1024:.2f}MB")
    print()
    
    # 设置音频数据回调（模拟ASR）
    chunk_count = [0]
    def on_audio_chunk(data: bytes):
        chunk_count[0] += 1
        if chunk_count[0] % 50 == 0:
            print(f"  → 已处理 {chunk_count[0]} 个音频块")
    
    recorder.set_on_audio_chunk_callback(on_audio_chunk)
    
    # 开始录音
    print("开始录音测试...")
    print(f"将录音 {test_buffer_seconds * 3} 秒，观察缓冲区清理行为")
    print("（说话或保持安静都可以，测试的是缓冲区管理）")
    print()
    
    recorder.start_recording()
    
    # 录音一段时间（比缓冲区限制更长）
    test_duration = test_buffer_seconds * 3  # 15秒
    start_time = time.time()
    
    try:
        while time.time() - start_time < test_duration:
            elapsed = int(time.time() - start_time)
            remaining = test_duration - elapsed
            print(f"\r录音中... {elapsed}秒 / {test_duration}秒 (剩余 {remaining}秒)", end="", flush=True)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n中断录音测试")
    
    print("\n")
    
    # 停止录音
    print("停止录音...")
    audio_data = recorder.stop_recording()
    
    print()
    print("=" * 60)
    print("测试结果统计")
    print("=" * 60)
    print(f"✓ 录音时长: {test_duration}秒")
    print(f"✓ 音频块数: {recorder._chunk_count}")
    print(f"✓ 总字节数: {recorder._total_bytes / 1024 / 1024:.2f}MB")
    print(f"✓ 最终缓冲: {len(audio_data) / 1024 / 1024:.2f}MB")
    print(f"✓ 清理次数: {recorder._buffer_cleanups}")
    print()
    
    # 验证结果
    expected_final_size = recorder.max_buffer_size
    actual_final_size = len(audio_data)
    
    print("验证结果:")
    if recorder._buffer_cleanups > 0:
        print(f"✅ 缓冲区已清理 {recorder._buffer_cleanups} 次（正常）")
    else:
        print(f"⚠️  缓冲区未清理（可能录音时间不够长）")
    
    if actual_final_size <= expected_final_size * 1.1:  # 允许10%误差
        print(f"✅ 缓冲区大小控制正常（{actual_final_size / 1024 / 1024:.2f}MB <= {expected_final_size / 1024 / 1024:.2f}MB）")
    else:
        print(f"❌ 缓冲区大小超标（{actual_final_size / 1024 / 1024:.2f}MB > {expected_final_size / 1024 / 1024:.2f}MB）")
    
    if chunk_count[0] > 0:
        print(f"✅ 音频流处理正常（共 {chunk_count[0]} 个块）")
    else:
        print(f"❌ 音频流处理失败")
    
    print()
    print("测试完成！")
    
    # 清理
    recorder.cleanup()

if __name__ == "__main__":
    try:
        test_buffer_management()
    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
        sys.exit(1)

