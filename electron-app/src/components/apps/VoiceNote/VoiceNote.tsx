import React, { useRef, useState, useEffect, useCallback } from 'react';
import { BlockEditor, NoteInfo } from './BlockEditor';
import { FormatToolbar } from './FormatToolbar';
import { WelcomeScreen } from './WelcomeScreen';
import { AppLayout } from '../../shared/AppLayout';
import { StatusIndicator, AppStatusType } from '../../shared/StatusIndicator';
import { AppButton, ButtonGroup } from '../../shared/AppButton';
import './VoiceNote.css';

interface BlockEditorHandle {
  appendAsrText: (text: string, isDefiniteUtterance?: boolean, timeInfo?: { startTime?: number; endTime?: number }) => void;
  setNoteInfoEndTime: () => void;
  getNoteInfo: () => NoteInfo | undefined;
  getBlocks: () => any[];
  setBlocks: (blocks: any[]) => void;
  appendSummaryBlock: (summary: string) => void;
  updateSummaryBlock: (summary: string) => void;
  finalizeSummaryBlock: () => void;
  removeSummaryBlock: () => void;
}

interface VoiceNoteProps {
  text: string;
  onTextChange: (text: string) => void;
  // ASR状态
  asrState: 'idle' | 'recording' | 'stopping';
  // ASR控制
  onAsrStart?: () => void; // 启动ASR
  onAsrStop?: () => void; // 停止ASR
  // 保存当前内容到历史记录（仅在idle状态时可用）
  onSaveText: (noteInfo?: NoteInfo) => void;
  // 其他
  onCopyText: () => void;
  onCreateNewNote?: () => void; // 保存当前笔记并创建新笔记
  apiConnected: boolean;
  blockEditorRef?: React.RefObject<BlockEditorHandle>;
  // 工作会话
  isWorkSessionActive: boolean;
  onStartWork: () => void;
  onEndWork: () => void;
  initialBlocks?: any[];
}

export const VoiceNote: React.FC<VoiceNoteProps> = ({
  text,
  onTextChange,
  asrState,
  onAsrStart,
  onAsrStop,
  onSaveText,
  onCopyText,
  onCreateNewNote,
  apiConnected,
  blockEditorRef,
  isWorkSessionActive,
  onStartWork,
  onEndWork,
  initialBlocks,
}) => {
  const [showToolbar, setShowToolbar] = useState(false);
  const [toolbarPosition, setToolbarPosition] = useState({ top: 0, left: 0 });
  const [isSummarizing, setIsSummarizing] = useState(false);
  const voiceNoteContentRef = useRef<HTMLDivElement>(null);
  
  // 判断是否显示欢迎界面：只要工作会话未激活，就显示欢迎界面
  const showWelcome = !isWorkSessionActive;

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
      
      if (voiceNoteContentRef.current) {
        const contentRect = voiceNoteContentRef.current.getBoundingClientRect();
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
    const handleClick = () => {
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
    console.log('格式化:', format);
    setShowToolbar(false);
  }, []);

  // 处理开始工作按钮
  const handleStartWork = () => {
    onStartWork();
  };

  // 当用户开始输入时，自动开始工作会话
  const handleTextChange = (newText: string) => {
    if (!isWorkSessionActive && newText.trim().length > 0) {
      onStartWork();
    }
    onTextChange(newText);
  };
  
  // 处理笔记信息变化
  const handleNoteInfoChange = useCallback((_info: NoteInfo) => {
    // 笔记信息变化时的处理（如果需要可以在这里添加逻辑）
  }, []);
  
  // 处理保存（添加结束时间）
  const handleSave = () => {
    if (blockEditorRef?.current) {
      // 设置结束时间
      blockEditorRef.current.setNoteInfoEndTime();
      // 获取更新后的笔记信息
      const currentNoteInfo = blockEditorRef.current.getNoteInfo();
      onSaveText(currentNoteInfo);
    } else {
      onSaveText();
    }
  };

  // 处理生成小结
  const handleSummary = async () => {
    if (!blockEditorRef?.current || isSummarizing) return;
    
    setIsSummarizing(true);
    
    try {
      // 获取所有blocks内容（排除note-info和已有的小结块）
      const blocks = blockEditorRef.current.getBlocks();
      const contentBlocks = blocks.filter((b: any) => 
        b.type !== 'note-info' && 
        !b.isSummary &&  // 忽略已有的小结块
        b.content.trim()
      );
      
      if (contentBlocks.length === 0) {
        alert('没有内容可以生成小结');
        setIsSummarizing(false);
        return;
      }
      
      // 提取所有文本内容
      const allText = contentBlocks.map((b: any) => b.content).join('\n\n');
      
      // 先创建一个空的小结block，用于流式更新
      blockEditorRef.current.appendSummaryBlock(''); // 先创建空block
      
      // 调用 SummaryAgent API 进行流式生成
      const response = await fetch('http://127.0.0.1:8765/api/summary/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: allText,
          temperature: 0.5,
          max_tokens: 2000,
          stream: true,  // 启用流式输出
        }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      // 处理流式响应
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('无法获取响应流');
      }
      
      const decoder = new TextDecoder();
      let summaryContent = '';
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') continue;
            
            try {
              const parsed = JSON.parse(data);
              if (parsed.chunk) {
                summaryContent += parsed.chunk;
                // 实时更新小结block
                blockEditorRef.current.updateSummaryBlock(summaryContent);
              }
            } catch (e) {
              console.warn('解析流式数据失败:', e);
            }
          }
        }
      }
      
      if (!summaryContent) {
        alert('生成小结失败：未收到有效内容');
        // 移除空的小结block
        blockEditorRef.current.removeSummaryBlock();
      } else {
        // 生成完成，更新外部内容（保存到历史记录）
        blockEditorRef.current.finalizeSummaryBlock();
      }
      
    } catch (error) {
      console.error('生成小结失败:', error);
      alert(`生成小结失败: ${error}`);
      // 移除失败的小结block
      if (blockEditorRef?.current) {
        blockEditorRef.current.removeSummaryBlock();
      }
    } finally {
      setIsSummarizing(false);
    }
  };

  // 计算 App 状态
  const getAppStatus = (): AppStatusType => {
    if (!apiConnected) return 'error';
    if (asrState === 'stopping') return 'waiting';
    if (isWorkSessionActive) return 'working';
    return 'idle';
  };

  return (
    <AppLayout
      title="语音笔记"
      subtitle="语音转文字，实时记录"
      icon="📝"
      statusIndicator={
        <StatusIndicator 
          status={asrState}
          appStatus={getAppStatus()}
          appStatusText={
            !apiConnected ? 'API未连接' :
            isWorkSessionActive ? '记录中' :
            '空闲'
          }
          asrStatus={asrState}
        />
      }
      actions={
        <>
          {/* ASR控制按钮：根据状态切换 */}
          {apiConnected && isWorkSessionActive && (
            <>
              {asrState === 'idle' && onAsrStart && (
                <AppButton
                  onClick={onAsrStart}
                  variant="success"
                  size="large"
                  icon="🎤"
                  title="启动语音识别"
                  ariaLabel="启动ASR"
                >
                  启动ASR
                </AppButton>
              )}

              {asrState === 'recording' && onAsrStop && (
                <AppButton
                  onClick={onAsrStop}
                  variant="danger"
                  size="medium"
                  icon="⏹"
                  title="停止语音识别"
                  ariaLabel="停止ASR"
                >
                  停止
                </AppButton>
              )}

              {asrState === 'stopping' && (
                <AppButton
                  disabled
                  variant="warning"
                  size="medium"
                  icon="⏳"
                  title="正在停止语音识别..."
                  ariaLabel="正在停止"
                >
                  停止中
                </AppButton>
              )}
            </>
          )}

          {/* 保存和工具按钮 */}
          {isWorkSessionActive && (
            <>
              <AppButton
                onClick={handleSave}
                disabled={asrState !== 'idle' || !text || !text.trim()}
                variant="info"
                size="medium"
                icon="💾"
                title="保存到历史记录"
                ariaLabel="保存文本"
              >
                保存
              </AppButton>

              <AppButton
                onClick={handleSummary}
                disabled={asrState !== 'idle' || !text || !text.trim() || isSummarizing}
                variant="success"
                size="medium"
                icon={isSummarizing ? "⏳" : "📊"}
                title="使用AI生成内容小结"
                ariaLabel="生成小结"
              >
                {isSummarizing ? '生成中' : '小结'}
              </AppButton>

              <ButtonGroup>
                {onCreateNewNote && (
                  <AppButton
                    onClick={onCreateNewNote}
                    disabled={asrState !== 'idle'}
                    variant="ghost"
                    size="medium"
                    icon="📝"
                    title={text && text.trim() ? "保存当前笔记并创建新笔记" : "创建新笔记"}
                    ariaLabel="新笔记"
                  >
                    新笔记
                  </AppButton>
                )}
                <AppButton
                  onClick={onCopyText}
                  disabled={!text}
                  variant="ghost"
                  size="medium"
                  icon="📋"
                  title="复制文本到剪贴板"
                  ariaLabel="复制文本"
                >
                  复制
                </AppButton>
                <AppButton
                  onClick={onEndWork}
                  disabled={asrState !== 'idle'}
                  variant="ghost"
                  size="medium"
                  icon="🚪"
                  title="退出当前笔记会话"
                  ariaLabel="退出"
                >
                  退出
                </AppButton>
              </ButtonGroup>
            </>
          )}
        </>
      }
    >
      {showWelcome ? (
        <WelcomeScreen onStartWork={handleStartWork} />
      ) : (
        <div className="voice-note-content" ref={voiceNoteContentRef}>
          <FormatToolbar
            visible={showToolbar}
            position={toolbarPosition}
            onFormat={handleFormat}
          />
          
          <BlockEditor
            initialContent={text}
            initialBlocks={initialBlocks}
            onContentChange={handleTextChange}
            onNoteInfoChange={handleNoteInfoChange}
            isRecording={asrState === 'recording'}
            ref={blockEditorRef}
          />
        </div>
      )}
    </AppLayout>
  );
};

