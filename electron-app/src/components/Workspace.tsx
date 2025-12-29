import React, { useRef, useState, useEffect, useCallback } from 'react';
import { BlockEditor } from './BlockEditor';
import { FormatToolbar } from './FormatToolbar';
import './Workspace.css';

interface WorkspaceProps {
  text: string;
  onTextChange: (text: string) => void;
  // ASR状态（后台输入员）
  asrState: 'idle' | 'recording' | 'paused' | 'processing';
  // ASR控制（后台输入员）
  onStartAsr?: () => void;
  onPauseAsr?: () => void;
  onResumeAsr?: () => void;
  onStopAsr?: () => void;
  // 保存（只有前端输入员可以操作）
  onSaveText: () => void;
  // 其他
  onCopyText: () => void;
  onClearText?: () => void;
  apiConnected: boolean;
  blockEditorRef?: React.RefObject<{ appendAsrText: (text: string) => void }>;
  hasPendingAsr?: boolean;
}

export const Workspace: React.FC<WorkspaceProps> = ({
  text,
  onTextChange,
  asrState,
  onStartAsr,
  onPauseAsr,
  onResumeAsr,
  onStopAsr,
  onSaveText,
  onCopyText,
  onClearText,
  apiConnected,
  blockEditorRef,
  hasPendingAsr = false,
}) => {
  const [showToolbar, setShowToolbar] = useState(false);
  const [toolbarPosition, setToolbarPosition] = useState({ top: 0, left: 0 });
  const workspaceContentRef = useRef<HTMLDivElement>(null);

  // 监听文本选择，显示格式化工具栏
  useEffect(() => {
    const handleSelectionChange = () => {
      const selection = window.getSelection();
      if (!selection || selection.rangeCount === 0 || selection.isCollapsed) {
        setShowToolbar(false);
        return;
      }

      const range = selection.getRangeAt(0);
      const rect = range.getBoundingClientRect();
      
      if (workspaceContentRef.current) {
        const contentRect = workspaceContentRef.current.getBoundingClientRect();
        setToolbarPosition({
          top: rect.top - contentRect.top - 40,
          left: rect.left - contentRect.left + rect.width / 2,
        });
        setShowToolbar(true);
      }
    };

    document.addEventListener('selectionchange', handleSelectionChange);
    return () => {
      document.removeEventListener('selectionchange', handleSelectionChange);
    };
  }, []);

  // 点击其他地方时隐藏工具栏
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      const selection = window.getSelection();
      if (!selection || selection.isCollapsed) {
        setShowToolbar(false);
      }
    };

    document.addEventListener('click', handleClick);
    return () => {
      document.removeEventListener('click', handleClick);
    };
  }, []);

  const handleFormat = useCallback((format: string) => {
    // TODO: 实现格式化功能
    console.log('格式化:', format);
    setShowToolbar(false);
  }, []);

  return (
    <div className="workspace">
      <div className="workspace-header">
        <div className="header-left">
          <div className="status-group">
            {/* ASR状态（后台输入员） */}
            {apiConnected && (
              <div
                className="status-indicator status-indicator-asr"
                data-status={asrState}
                role="status"
                aria-live="polite"
              >
                <span className="status-dot" aria-hidden="true"></span>
                <span className="status-text">
                  {asrState === 'recording'
                    ? hasPendingAsr
                      ? 'ASR输入中...（有新的语音输入待应用）'
                      : 'ASR输入中...'
                    : asrState === 'paused'
                    ? hasPendingAsr
                      ? 'ASR已暂停（有新的语音输入待应用）'
                      : 'ASR已暂停'
                    : asrState === 'processing'
                    ? 'ASR处理中...'
                    : 'ASR未启动'}
                </span>
                {hasPendingAsr && (
                  <span className="pending-asr-indicator" title="停止输入后，新的语音输入将自动应用">
                    ⏳
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
        <div className="header-right">
          <div className="recording-controls">
            {/* ASR控制（后台输入员） */}
            {apiConnected && onStartAsr && (
              <div className="primary-actions">
                {asrState === 'idle' ? (
                  <button
                    onClick={onStartAsr}
                    className="control-btn control-btn-primary control-btn-start"
                    title="启动ASR（后台输入员开始工作）"
                    aria-label="启动ASR"
                  >
                    <span className="btn-icon" aria-hidden="true">🎤</span>
                    <span className="btn-text">启动ASR</span>
                  </button>
                ) : asrState === 'recording' ? (
                  <>
                    <button
                      onClick={onPauseAsr}
                      className="control-btn control-btn-secondary control-btn-pause"
                      title="暂停ASR"
                      aria-label="暂停ASR"
                    >
                      <span className="btn-icon" aria-hidden="true">⏸</span>
                      <span className="btn-text">暂停</span>
                    </button>
                    {onStopAsr && (
                      <button
                        onClick={onStopAsr}
                        className="control-btn control-btn-secondary control-btn-stop"
                        title="停止ASR"
                        aria-label="停止ASR"
                      >
                        <span className="btn-icon" aria-hidden="true">■</span>
                        <span className="btn-text">停止</span>
                      </button>
                    )}
                  </>
                ) : asrState === 'paused' ? (
                  <>
                    <button
                      onClick={onResumeAsr}
                      className="control-btn control-btn-secondary control-btn-resume"
                      title="恢复ASR"
                      aria-label="恢复ASR"
                    >
                      <span className="btn-icon" aria-hidden="true">▶</span>
                      <span className="btn-text">继续</span>
                    </button>
                    {onStopAsr && (
                      <button
                        onClick={onStopAsr}
                        className="control-btn control-btn-secondary control-btn-stop"
                        title="停止ASR"
                        aria-label="停止ASR"
                      >
                        <span className="btn-icon" aria-hidden="true">■</span>
                        <span className="btn-text">停止</span>
                      </button>
                    )}
                  </>
                ) : null}
              </div>
            )}

            {/* 保存按钮（只有前端输入员可以操作） */}
            <div className="secondary-actions">
              <button
                onClick={onSaveText}
                disabled={!text || !text.trim()}
                className="control-btn control-btn-primary control-btn-save"
                title="保存到历史记录（只有前端输入员可以操作）"
                aria-label="保存文本"
              >
                <span className="btn-icon" aria-hidden="true">💾</span>
                <span className="btn-text">保存</span>
              </button>
            </div>

            {/* 工具按钮组 */}
            <div className="tool-actions">
              {onClearText && text && (
                <button
                  onClick={onClearText}
                  className="control-btn control-btn-tool"
                  title="清空当前内容"
                  aria-label="清空内容"
                >
                  <span className="btn-icon" aria-hidden="true">🗑</span>
                  <span className="btn-text">清空</span>
                </button>
              )}
              <button
                onClick={onCopyText}
                disabled={!text}
                className="control-btn control-btn-tool"
                title="复制文本到剪贴板"
                aria-label="复制文本"
              >
                <span className="btn-icon" aria-hidden="true">📋</span>
                <span className="btn-text">复制</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="workspace-content" ref={workspaceContentRef}>
        <FormatToolbar
          visible={showToolbar}
          position={toolbarPosition}
          onFormat={handleFormat}
        />
        <BlockEditor
          initialContent={text}
          onContentChange={onTextChange}
          isRecording={asrState === 'recording'}
          isPaused={asrState === 'paused'}
          ref={blockEditorRef}
        />
      </div>
    </div>
  );
};

