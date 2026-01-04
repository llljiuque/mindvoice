#!/bin/bash
# 尝试安装 WebRTC Audio Processing

echo "========================================"
echo "安装 WebRTC Audio Processing"
echo "========================================"
echo ""

# 激活虚拟环境
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✓ 虚拟环境已激活"
else
    echo "✗ 未找到虚拟环境，请先运行 ./quick_start.sh"
    exit 1
fi

echo ""
echo "尝试安装 webrtc-audio-processing..."
echo "注意：这需要编译工具，可能需要几分钟"
echo ""

# 尝试安装
if pip install webrtc-audio-processing; then
    echo ""
    echo "✓ WebRTC APM 安装成功！"
    echo ""
    echo "验证安装..."
    if python -c "import webrtc_audio_processing; print('✓ 导入成功')"; then
        echo ""
        echo "========================================"
        echo "安装完成！"
        echo "========================================"
        echo ""
        echo "WebRTC 音频处理模块已成功安装"
        echo "将使用原生 WebRTC APM 实现（性能最优）"
        echo ""
        echo "下一步："
        echo "1. 检查 config.yml 中 audio_processing.enabled = true"
        echo "2. 重启应用：./stop.sh && ./quick_start.sh"
        echo "3. 测试语音输入效果"
        echo ""
    else
        echo ""
        echo "✗ 导入失败，请检查错误信息"
        exit 1
    fi
else
    echo ""
    echo "✗ 安装失败"
    echo ""
    echo "这通常是因为："
    echo "1. 缺少编译工具"
    echo "2. 系统不兼容"
    echo ""
    echo "解决方案："
    echo "--------------------------------------"
    echo "不用担心！系统会自动使用简化版实现"
    echo ""
    echo "简化版功能："
    echo "- ✓ 提供基本的 AGC 和 NS 功能"
    echo "- ✓ 无需编译，纯 Python 实现"
    echo "- ✓ 性能略逊于原生实现，但足够使用"
    echo ""
    echo "如需安装原生版本，请先安装编译工具："
    echo "  macOS: xcode-select --install"
    echo "  然后重新运行此脚本"
    echo ""
    exit 0
fi

