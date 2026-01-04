import React from 'react';
import './StatusIndicator.css';

export type StatusType = 'idle' | 'recording' | 'paused' | 'stopping' | 'processing' | 'connected' | 'disconnected';
export type AppStatusType = 'idle' | 'working' | 'waiting' | 'error';

interface StatusIndicatorProps {
  status: StatusType;
  text?: string;
  showDot?: boolean;
  // 新增：App状态和ASR状态
  appStatus?: AppStatusType;
  appStatusText?: string;
  asrStatus?: StatusType;
  asrStatusText?: string;
}

const statusConfig: Record<StatusType, { text: string; color: string }> = {
  idle: { text: 'ASR未启动', color: 'tertiary' },        // 灰色
  recording: { text: 'ASR输入中...', color: 'success' }, // 绿色 - 正在工作
  paused: { text: 'ASR已暂停', color: 'tertiary' },      // 灰色 - 暂停状态
  stopping: { text: 'ASR正在停止...', color: 'warning' }, // 黄色 - 过渡状态
  processing: { text: '处理中...', color: 'warning' },    // 黄色 - 过渡状态
  connected: { text: '已连接', color: 'success' },       // 绿色
  disconnected: { text: '未连接', color: 'danger' },     // 红色
};

const appStatusConfig: Record<AppStatusType, { text: string; color: string }> = {
  idle: { text: '空闲', color: 'tertiary' },
  working: { text: '工作中', color: 'success' },
  waiting: { text: '等待中', color: 'warning' },
  error: { text: '错误', color: 'danger' },
};

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  status,
  text,
  showDot = true,
  appStatus,
  appStatusText,
  asrStatus,
  asrStatusText,
}) => {
  // 如果提供了 asrStatus，优先显示 ASR 状态（简化版，不显示 appStatus）
  if (asrStatus !== undefined) {
    const asrConfig = statusConfig[asrStatus];
    const displayAsrText = asrStatusText || asrConfig.text;
    
    return (
      <div
        className="status-indicator"
        data-status={asrStatus}
        role="status"
        aria-live="polite"
      >
        {showDot && <span className="status-dot" aria-hidden="true"></span>}
        <span className="status-text">{displayAsrText}</span>
      </div>
    );
  }

  // 原有的单状态显示逻辑
  const config = statusConfig[status];
  const displayText = text || config.text;

  return (
    <div
      className="status-indicator"
      data-status={status}
      role="status"
      aria-live="polite"
    >
      {showDot && <span className="status-dot" aria-hidden="true"></span>}
      <span className="status-text">{displayText}</span>
    </div>
  );
};

