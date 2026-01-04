#!/bin/bash
# VAD 调试脚本 - 实时监控语音活动检测

echo "========================================"
echo "VAD 调试监控 - 实时查看语音检测状态"
echo "========================================"
echo ""
echo "当前 VAD 配置:"
echo "  mode: 3 (最严格)"
echo "  speech_start_threshold: 5 (需要连续5帧)"
echo "  speech_end_threshold: 15"
echo ""
echo "监控以下关键事件:"
echo "  ✓ 检测到语音开始 (on_speech_start)"
echo "  ✓ 检测到语音结束 (on_speech_end)"
echo "  ✓ 语音帧统计"
echo "  ✓ ASR 启动/停止"
echo ""
echo "按 Ctrl+C 停止监控"
echo "========================================"
echo ""

# 获取最新的日志文件
LOG_FILE=$(ls -t logs/api_server_*.log | head -1)

if [ -z "$LOG_FILE" ]; then
    echo "错误: 未找到日志文件"
    exit 1
fi

echo "监控日志文件: $LOG_FILE"
echo ""

# 实时监控日志，高亮显示关键信息
tail -f "$LOG_FILE" | grep --line-buffered -E "(AudioASRGateway|语音服务|检测到语音|on_speech|speech_start|speech_end|ASR.*启动|ASR.*停止|语音帧=|过滤率)" | while read line; do
    # 高亮显示重要事件
    if echo "$line" | grep -q "检测到语音开始"; then
        echo -e "\033[1;32m[语音开始] $line\033[0m"
    elif echo "$line" | grep -q "检测到语音结束"; then
        echo -e "\033[1;31m[语音结束] $line\033[0m"
    elif echo "$line" | grep -q "on_speech_start"; then
        echo -e "\033[1;32m[回调] $line\033[0m"
    elif echo "$line" | grep -q "on_speech_end"; then
        echo -e "\033[1;31m[回调] $line\033[0m"
    elif echo "$line" | grep -q "过滤率"; then
        echo -e "\033[1;33m[统计] $line\033[0m"
    else
        echo "$line"
    fi
done

