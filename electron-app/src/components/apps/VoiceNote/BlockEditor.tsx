import { useState, useRef, useEffect, useCallback, forwardRef, useImperativeHandle } from 'react';
import { TimelineIndicator } from './TimelineIndicator';
import './BlockEditor.css';
import './Block.css';

export type BlockType = 'note-info' | 'paragraph' | 'h1' | 'h2' | 'h3' | 'bulleted-list' | 'numbered-list' | 'code';

export interface NoteInfo {
  title: string;
  type: string;
  relatedPeople: string;
  location: string;
  startTime: string;
  endTime?: string;
}

export interface Block {
  id: string;
  type: BlockType;
  content: string;
  isAsrWriting?: boolean;
  noteInfo?: NoteInfo;
  startTime?: number;
  endTime?: number;
  isSummary?: boolean;
  isBufferBlock?: boolean; // 标识底部缓冲块
}

interface BlockEditorProps {
  initialContent?: string;
  initialBlocks?: Block[];
  onContentChange?: (content: string, isDefiniteUtterance?: boolean) => void;
  onNoteInfoChange?: (noteInfo: NoteInfo) => void;
  isRecording?: boolean;
}

export interface BlockEditorHandle {
  appendAsrText: (text: string, isDefiniteUtterance?: boolean, timeInfo?: { startTime?: number; endTime?: number }) => void;
  setNoteInfoEndTime: () => void;
  getNoteInfo: () => NoteInfo | undefined;
  getBlocks: () => Block[];
  setBlocks: (newBlocks: Block[]) => void;
  appendSummaryBlock: (summary: string) => void;
  updateSummaryBlock: (summary: string) => void;
  finalizeSummaryBlock: () => void;
  removeSummaryBlock: () => void;
}


function createEmptyBlock(isAsrWriting: boolean = false): Block {
  return {
    id: `block-${Date.now()}-${Math.random()}`,
    type: 'paragraph',
    content: '',
    isAsrWriting,
  };
}

function createNoteInfoBlock(): Block {
  return {
    id: `block-noteinfo-${Date.now()}`,
    type: 'note-info',
    content: '',
    isAsrWriting: false,
    noteInfo: {
      title: '',
      type: '',
      relatedPeople: '',
      location: '',
      startTime: new Date().toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      }),
    },
  };
}

function createBlocksFromContent(content: string): Block[] {
  const noteInfoBlock = createNoteInfoBlock();
  if (!content) return [noteInfoBlock, createEmptyBlock()];
  
  const timestamp = Date.now();
  const contentBlocks: Block[] = [];
  
  // 处理小结块的特殊标记
  const summaryRegex = /\[SUMMARY_BLOCK_START\]([\s\S]*?)\[SUMMARY_BLOCK_END\]/g;
  let lastIndex = 0;
  let match;
  let blockIndex = 0;
  
  while ((match = summaryRegex.exec(content)) !== null) {
    // 处理小结块之前的普通内容
    if (match.index > lastIndex) {
      const beforeContent = content.substring(lastIndex, match.index);
      const lines = beforeContent.split('\n').filter(line => line.trim() || line === '');
      lines.forEach(line => {
        contentBlocks.push({
          id: `block-${timestamp}-${blockIndex++}-${Math.random()}`,
          type: 'paragraph' as BlockType,
          content: line,
          isAsrWriting: false,
        });
      });
    }
    
    // 创建小结块（保持完整，不拆分）
    const summaryContent = match[1];
    contentBlocks.push({
      id: `block-${timestamp}-${blockIndex++}-${Math.random()}`,
      type: 'paragraph' as BlockType,
      content: summaryContent,
      isAsrWriting: false,
      isSummary: true,
    });
    
    lastIndex = summaryRegex.lastIndex;
  }
  
  // 处理剩余的普通内容
  if (lastIndex < content.length) {
    const remainingContent = content.substring(lastIndex);
    const lines = remainingContent.split('\n').filter(line => line.trim() || line === '');
    lines.forEach(line => {
      contentBlocks.push({
        id: `block-${timestamp}-${blockIndex++}-${Math.random()}`,
        type: 'paragraph' as BlockType,
        content: line,
        isAsrWriting: false,
      });
    });
  }
  
  // 如果没有小结块，使用原来的简单拆分逻辑
  if (contentBlocks.length === 0) {
    content.split('\n').forEach((line, i) => {
      contentBlocks.push({
        id: `block-${timestamp}-${i}-${Math.random()}`,
        type: 'paragraph' as BlockType,
        content: line,
        isAsrWriting: false,
      });
    });
  }
  
  return [noteInfoBlock, ...contentBlocks];
}

function blocksToContent(blocks: Block[]): string {
  // 排除 note-info 和 buffer block
  // 小结block使用特殊分隔符，防止被拆分
  return blocks
    .filter(b => b.type !== 'note-info' && !b.isBufferBlock)
    .map((b) => {
      if (b.isSummary) {
        // 小结块使用特殊标记包裹，保持完整性
        return `[SUMMARY_BLOCK_START]${b.content}[SUMMARY_BLOCK_END]`;
      }
      return b.content;
    })
    .join('\n');
}

export const BlockEditor = forwardRef<BlockEditorHandle, BlockEditorProps>(({
  initialContent = '',
  initialBlocks,
  onContentChange,
  onNoteInfoChange,
  isRecording = false,
}, ref) => {
  const [blocks, setBlocks] = useState<Block[]>(() => createBlocksFromContent(initialContent));
  const asrWritingBlockIdRef = useRef<string | null>(null);
  const isAsrActive = isRecording;
  const [editingBlockId, setEditingBlockId] = useState<string | null>(null);
  const lastBlockCountRef = useRef<number>(blocks.length);
  const blockRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const isComposingRef = useRef<boolean>(false); // 标记是否正在进行中文输入

  // 确保底部始终有一个空的缓冲块（用于视觉空间）
  const ensureBottomBufferBlock = useCallback((blocks: Block[]): Block[] => {
    const updated = [...blocks];
    
    // 检查最后一个block是否是缓冲块
    const lastBlock = updated[updated.length - 1];
    const isLastBlockBuffer = lastBlock && lastBlock.isBufferBlock;
    
    // 如果最后一个block不是缓冲块，添加一个
    if (!isLastBlockBuffer) {
      const bufferBlock = createEmptyBlock(false);
      bufferBlock.isBufferBlock = true;
      updated.push(bufferBlock);
    }
    
    return updated;
  }, []);

  useEffect(() => {
    if (!isAsrActive) {
      if (initialBlocks && initialBlocks.length > 0) {
        const blocksWithBuffer = ensureBottomBufferBlock(initialBlocks);
        setBlocks(blocksWithBuffer);
      } else {
        const newBlocks = ensureBottomBufferBlock(createBlocksFromContent(initialContent));
        setBlocks(newBlocks);
      }
      asrWritingBlockIdRef.current = null;
    }
  }, [initialContent, initialBlocks, isAsrActive, ensureBottomBufferBlock]);

  const ensureAsrWritingBlock = useCallback((blocks: Block[]): { blocks: Block[]; blockId: string; index: number } => {
    const updated = [...blocks];
    updated.forEach((b) => b.isAsrWriting = false);
    
    // 找到最后一个空block（不包括缓冲块）
    let emptyBlockIdx = -1;
    for (let i = updated.length - 1; i >= 0; i--) {
      if (!updated[i].content || updated[i].content.trim() === '') {
        emptyBlockIdx = i;
        break;
      }
    }
    
    // 如果找到空block且不是最后一个（最后一个是缓冲块），使用它
    if (emptyBlockIdx >= 0 && emptyBlockIdx < updated.length - 1) {
      updated[emptyBlockIdx] = {
        ...updated[emptyBlockIdx],
        isAsrWriting: true,
        content: '',
      };
      return { blocks: updated, blockId: updated[emptyBlockIdx].id, index: emptyBlockIdx };
    }
    
    // 否则，在倒数第二个位置插入新的ASR写入块（保持缓冲块在最后）
    const newBlock = createEmptyBlock(true);
    updated.splice(updated.length - 1, 0, newBlock);
    const asrIdx = updated.length - 2;
    return { blocks: updated, blockId: updated[asrIdx].id, index: asrIdx };
  }, []);

  useEffect(() => {
    if (isAsrActive) {
      if (!asrWritingBlockIdRef.current) {
        setBlocks((prev) => {
          const { blocks: updated, blockId } = ensureAsrWritingBlock(prev);
          asrWritingBlockIdRef.current = blockId;
          return ensureBottomBufferBlock(updated);
        });
      }
    } else {
      setBlocks((prev) => {
        const updated = prev.map((b) => ({ ...b, isAsrWriting: false }));
        return ensureBottomBufferBlock(updated);
      });
      asrWritingBlockIdRef.current = null;
    }
  }, [isAsrActive, ensureAsrWritingBlock, ensureBottomBufferBlock]);

  const appendAsrText = useCallback(
    (newText: string, isDefiniteUtterance: boolean = false, timeInfo?: { startTime?: number; endTime?: number }) => {
      if (!isAsrActive) return;

      setBlocks((prev) => {
        const updated = [...prev];
        
        let currentIdx = asrWritingBlockIdRef.current
          ? updated.findIndex((b) => b.id === asrWritingBlockIdRef.current)
          : -1;
        
        if (currentIdx < 0) {
          const { blocks: newBlocks, blockId, index } = ensureAsrWritingBlock(updated);
          updated.splice(0, updated.length, ...newBlocks);
          asrWritingBlockIdRef.current = blockId;
          currentIdx = index;
        }

        if (isDefiniteUtterance) {
          updated[currentIdx] = {
            ...updated[currentIdx],
            content: newText,
            isAsrWriting: false,
            startTime: timeInfo?.startTime,
            endTime: timeInfo?.endTime,
          };
          
          // 在倒数第二个位置插入新的ASR写入块（保持缓冲块在最后）
          const nextBlock = createEmptyBlock(true);
          updated.splice(updated.length - 1, 0, nextBlock);
          asrWritingBlockIdRef.current = nextBlock.id;
        } else {
          updated[currentIdx] = {
            ...updated[currentIdx],
            content: newText,
          };
        }
        
        const content = blocksToContent(updated);
        onContentChange?.(content, isDefiniteUtterance);
        
        return ensureBottomBufferBlock(updated);
      });
    },
    [isAsrActive, ensureAsrWritingBlock, onContentChange, ensureBottomBufferBlock]
  );

  const setNoteInfoEndTime = useCallback(() => {
    const endTime = new Date().toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
    
    setBlocks((prev) => {
      const updated = prev.map((b) => {
        if (b.type === 'note-info' && b.noteInfo) {
          const newNoteInfo = { ...b.noteInfo, endTime };
          onNoteInfoChange?.(newNoteInfo);
          return { ...b, noteInfo: newNoteInfo };
        }
        return b;
      });
      return updated;
    });
  }, [onNoteInfoChange]);

  const getNoteInfo = useCallback((): NoteInfo | undefined => {
    const noteInfoBlock = blocks.find(b => b.type === 'note-info');
    return noteInfoBlock?.noteInfo;
  }, [blocks]);

  const getBlocks = useCallback((): Block[] => {
    return blocks;
  }, [blocks]);

  const setBlocksFromExternal = useCallback((newBlocks: Block[]) => {
    setBlocks(newBlocks);
  }, []);

  const appendSummaryBlock = useCallback((summary: string) => {
    setBlocks((prev) => {
      const updated = [...prev];
      
      // 移除所有空的 ASR 写入块
      const filtered = updated.filter(b => !(b.isAsrWriting && !b.content.trim()));
      
      // 移除末尾的缓冲块（稍后会重新添加）
      if (filtered.length > 0 && filtered[filtered.length - 1].isBufferBlock) {
        filtered.pop();
      }
      
      // 创建一个包含标题和内容的小结块（使用换行符分隔标题和内容）
      const summaryBlock: Block = {
        id: `block-summary-${Date.now()}`,
        type: 'paragraph',
        content: summary ? `📊 会议小结\n\n${summary}` : '📊 会议小结\n\n生成中...',
        isAsrWriting: false,
        isSummary: true,
      };
      
      // 添加小结块
      filtered.push(summaryBlock);
      
      // 更新内容
      const content = blocksToContent(filtered);
      onContentChange?.(content, false);
      
      // 确保底部有缓冲块
      return ensureBottomBufferBlock(filtered);
    });
  }, [onContentChange, ensureBottomBufferBlock]);

  const updateSummaryBlock = useCallback((summary: string) => {
    setBlocks((prev) => {
      const updated = [...prev];
      
      // 找到小结块并更新内容
      const summaryBlockIndex = updated.findIndex(b => b.isSummary);
      if (summaryBlockIndex >= 0) {
        updated[summaryBlockIndex] = {
          ...updated[summaryBlockIndex],
          content: `📊 会议小结\n\n${summary}`,
        };
        
        // 注意：流式更新时不调用 onContentChange，避免触发外部更新导致block重建
        // 只在生成完成时（finalizeSummaryBlock）才更新外部内容
      }
      
      return updated;
    });
  }, []); // 移除 onContentChange 依赖

  const finalizeSummaryBlock = useCallback(() => {
    setBlocks((prev) => {
      // 生成完成，更新外部内容
      const content = blocksToContent(prev);
      onContentChange?.(content, false);
      return prev;
    });
  }, [onContentChange]);

  const removeSummaryBlock = useCallback(() => {
    setBlocks((prev) => {
      const updated = prev.filter(b => !b.isSummary);
      
      // 更新内容
      const content = blocksToContent(updated);
      onContentChange?.(content, false);
      
      return ensureBottomBufferBlock(updated);
    });
  }, [onContentChange, ensureBottomBufferBlock]);

  useImperativeHandle(ref, () => ({ 
    appendAsrText,
    setNoteInfoEndTime,
    getNoteInfo,
    getBlocks,
    setBlocks: setBlocksFromExternal,
    appendSummaryBlock,
    updateSummaryBlock,
    finalizeSummaryBlock,
    removeSummaryBlock,
  }));

  const getTagName = (type: BlockType) => {
    switch (type) {
      case 'h1': return 'h1';
      case 'h2': return 'h2';
      case 'h3': return 'h3';
      case 'code': return 'pre';
      default: return 'p';
    }
  };

  const getClassName = (block: Block) => {
    const base = 'block-content';
    const typeClass = `block-${block.type}`;
    const asrWritingClass = block.isAsrWriting ? 'block-asr-writing' : '';
    return `${base} ${typeClass} ${asrWritingClass}`.trim();
  };

  const getPlaceholder = (type: BlockType) => {
    switch (type) {
      case 'note-info': return '点击编辑笔记信息...';
      case 'h1': return '标题 1';
      case 'h2': return '标题 2';
      case 'h3': return '标题 3';
      case 'bulleted-list': return '列表项';
      case 'numbered-list': return '列表项';
      case 'code': return '代码';
      default: return '';
    }
  };

  // 处理block内容变化
  const handleBlockChange = (blockId: string, newContent: string) => {
    setBlocks((prev) => {
      const updated = prev.map((b) =>
        b.id === blockId ? { ...b, content: newContent } : b
      );
      const content = blocksToContent(updated);
      onContentChange?.(content, false);
      return ensureBottomBufferBlock(updated);
    });
  };

  // 保存光标位置
  const saveCursorPosition = (element: HTMLElement) => {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) return null;
    
    const range = selection.getRangeAt(0);
    const preCaretRange = range.cloneRange();
    preCaretRange.selectNodeContents(element);
    preCaretRange.setEnd(range.endContainer, range.endOffset);
    const caretOffset = preCaretRange.toString().length;
    
    return caretOffset;
  };

  // 恢复光标位置
  const restoreCursorPosition = (element: HTMLElement, offset: number) => {
    const selection = window.getSelection();
    if (!selection) return;
    
    const range = document.createRange();
    let currentOffset = 0;
    let found = false;

    const traverseNodes = (node: Node): boolean => {
      if (node.nodeType === Node.TEXT_NODE) {
        const textLength = node.textContent?.length || 0;
        if (currentOffset + textLength >= offset) {
          range.setStart(node, offset - currentOffset);
          range.collapse(true);
          found = true;
          return true;
        }
        currentOffset += textLength;
      } else {
        for (let i = 0; i < node.childNodes.length; i++) {
          if (traverseNodes(node.childNodes[i])) return true;
        }
      }
      return false;
    };

    traverseNodes(element);
    
    if (found) {
      selection.removeAllRanges();
      selection.addRange(range);
    }
  };

  // 处理noteInfo变化
  const handleNoteInfoChange = (blockId: string, field: keyof NoteInfo, value: string) => {
    setBlocks((prev) => {
      const updated = prev.map((b) => {
        if (b.id === blockId && b.type === 'note-info' && b.noteInfo) {
          const newNoteInfo = { ...b.noteInfo, [field]: value };
          onNoteInfoChange?.(newNoteInfo);
          return { ...b, noteInfo: newNoteInfo };
        }
        return b;
      });
      return ensureBottomBufferBlock(updated);
    });
  };

  // 生成noteInfo的文本描述
  const generateNoteInfoDescription = (noteInfo?: NoteInfo) => {
    if (!noteInfo) return '';
    const parts: string[] = [];
    
    if (noteInfo.title) parts.push(`📌 ${noteInfo.title}`);
    if (noteInfo.type) parts.push(`🏷️ ${noteInfo.type}`);
    if (noteInfo.relatedPeople) parts.push(`👥 ${noteInfo.relatedPeople}`);
    if (noteInfo.location) parts.push(`📍 ${noteInfo.location}`);
    parts.push(`⏰ ${noteInfo.startTime}`);
    if (noteInfo.endTime) parts.push(`⏱️ ${noteInfo.endTime}`);
    
    return parts.join(' · ');
  };

  // 处理删除block
  const handleDeleteBlock = useCallback((blockId: string) => {
    setBlocks((prev) => {
      // 过滤掉要删除的block
      const updated = prev.filter(b => b.id !== blockId);
      
      // 确保至少有 note-info block
      if (updated.length === 0 || !updated.find(b => b.type === 'note-info')) {
        return prev; // 不允许删除所有block
      }
      
      // 更新内容
      const content = blocksToContent(updated);
      onContentChange?.(content, false);
      
      return ensureBottomBufferBlock(updated);
    });
  }, [onContentChange, ensureBottomBufferBlock]);

  // 处理note-info编辑区域外的点击
  // 检测是否有用户正在编辑的block
  const isUserEditing = useCallback(() => {
    // 检查是否有contentEditable元素获得焦点
    const activeElement = document.activeElement;
    if (activeElement && activeElement.getAttribute('contenteditable') === 'true') {
      return true;
    }
    
    // 检查是否在编辑note-info
    if (editingBlockId) {
      return true;
    }
    
    return false;
  }, [editingBlockId]);

  // 当新block出现或ASR正在写入block时，自动滚动以确保内容完整可见
  useEffect(() => {
    if (!isAsrActive || isUserEditing()) {
      lastBlockCountRef.current = blocks.length;
      return;
    }

    const currentBlockCount = blocks.length;
    const previousBlockCount = lastBlockCountRef.current;
    
    // 找到ASR正在写入的block
    const asrWritingBlock = blocks.find(b => b.isAsrWriting);
    
    if (asrWritingBlock) {
      const blockElement = blockRefs.current.get(asrWritingBlock.id);
      
      if (blockElement) {
        // 检测是否是新增block
        const isNewBlock = currentBlockCount > previousBlockCount;
        
        if (isNewBlock) {
          // 新增block时，将block定位到视口中心偏上的位置，而不是贴底
          blockElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
        } else {
          // 内容更新时，确保block完整可见但不过度滚动
          const rect = blockElement.getBoundingClientRect();
          const viewportHeight = window.innerHeight;
          
          // 如果block底部超出视口或顶部不可见，则滚动到中心位置
          if (rect.bottom > viewportHeight - 100 || rect.top < 100) {
            blockElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }
        }
      }
    }
    
    lastBlockCountRef.current = currentBlockCount;
  }, [blocks, isAsrActive, isUserEditing]);

  // 处理note-info编辑区域外的点击
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (editingBlockId) {
        const target = e.target as HTMLElement;
        // 检查点击是否在note-info-edit区域外
        if (!target.closest('.block-note-info-edit') && !target.closest('.block-note-info')) {
          setEditingBlockId(null);
        }
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [editingBlockId]);

  const renderBlock = (block: Block) => {
    // 缓冲块特殊处理：不显示，只用于占位
    // 使用更大的高度，确保当前输入的block有足够的视觉空间
    if (block.isBufferBlock) {
      return (
        <div 
          key={block.id} 
          className="block block-buffer"
          style={{ minHeight: '60vh', background: 'transparent' }}
        >
        </div>
      );
    }

    // note-info类型的特殊渲染
    if (block.type === 'note-info') {
      const isEditing = editingBlockId === block.id;
      const description = generateNoteInfoDescription(block.noteInfo);

      return (
        <div 
          key={block.id} 
          className="block block-note-info-container"
          ref={(el) => {
            if (el) blockRefs.current.set(block.id, el);
            else blockRefs.current.delete(block.id);
          }}
        >
          <div className="block-handle">
            <span className="handle-icon">📋</span>
          </div>
          {!isEditing ? (
            <div
              className="block-content block-note-info"
              onClick={() => setEditingBlockId(block.id)}
              data-placeholder={getPlaceholder(block.type)}
            >
              {description}
            </div>
          ) : (
            <div className="block-content block-note-info-edit">
              <input
                type="text"
                className="note-info-input"
                placeholder="📌 标题"
                value={block.noteInfo?.title || ''}
                onChange={(e) => handleNoteInfoChange(block.id, 'title', e.target.value)}
                autoFocus
              />
              <input
                type="text"
                className="note-info-input"
                placeholder="🏷️ 类型"
                value={block.noteInfo?.type || ''}
                onChange={(e) => handleNoteInfoChange(block.id, 'type', e.target.value)}
              />
              <input
                type="text"
                className="note-info-input"
                placeholder="👥 相关人员"
                value={block.noteInfo?.relatedPeople || ''}
                onChange={(e) => handleNoteInfoChange(block.id, 'relatedPeople', e.target.value)}
              />
              <input
                type="text"
                className="note-info-input"
                placeholder="📍 地点"
                value={block.noteInfo?.location || ''}
                onChange={(e) => handleNoteInfoChange(block.id, 'location', e.target.value)}
              />
              <div className="note-info-time">⏰ {block.noteInfo?.startTime}</div>
              {block.noteInfo?.endTime && (
                <div className="note-info-time">⏱️ {block.noteInfo.endTime}</div>
              )}
            </div>
          )}
          <button 
            className="block-delete-btn"
            onClick={(e) => {
              e.stopPropagation();
              handleDeleteBlock(block.id);
            }}
            title="删除此块"
          >
            🗑️
          </button>
        </div>
      );
    }

    // 普通block渲染
    const Tag = getTagName(block.type) as 'p' | 'h1' | 'h2' | 'h3' | 'pre';
    const canEdit = !block.isAsrWriting; // ASR正在写入的block不能编辑
    const hasTimeInfo = block.startTime !== undefined && block.endTime !== undefined;

    return (
      <div 
        key={block.id} 
        className={`block ${block.isAsrWriting ? 'block-asr-writing-container' : ''} ${block.isSummary ? 'block-summary-container' : ''}`}
        ref={(el) => {
          if (el) blockRefs.current.set(block.id, el);
          else blockRefs.current.delete(block.id);
        }}
      >
        <div className="block-handle">
          <span className="handle-icon">⋮⋮</span>
        </div>
        <div className="block-content-wrapper">
          <Tag
            className={getClassName(block)}
            contentEditable={canEdit}
            suppressContentEditableWarning
            onCompositionStart={() => {
              // 中文输入开始
              isComposingRef.current = true;
            }}
            onCompositionUpdate={() => {
              // 中文输入进行中
              isComposingRef.current = true;
            }}
            onCompositionEnd={(e) => {
              // 中文输入结束，现在可以安全更新状态
              isComposingRef.current = false;
              if (canEdit) {
                const element = e.currentTarget;
                const cursorPos = saveCursorPosition(element);
                const newContent = element.textContent || '';
                handleBlockChange(block.id, newContent);
                
                // 在下一个渲染周期恢复光标位置
                setTimeout(() => {
                  if (cursorPos !== null) {
                    restoreCursorPosition(element, cursorPos);
                  }
                }, 0);
              }
            }}
            onInput={(e) => {
              // 如果正在进行中文输入，不更新状态，等待 compositionEnd
              if (isComposingRef.current) {
                return;
              }
              
              if (canEdit) {
                const element = e.currentTarget;
                const cursorPos = saveCursorPosition(element);
                const newContent = element.textContent || '';
                handleBlockChange(block.id, newContent);
                
                // 在下一个渲染周期恢复光标位置
                setTimeout(() => {
                  if (cursorPos !== null) {
                    restoreCursorPosition(element, cursorPos);
                  }
                }, 0);
              }
            }}
            onPaste={(e) => {
              if (!canEdit) {
                e.preventDefault();
              } else {
                // 处理粘贴，保持纯文本
                e.preventDefault();
                const text = e.clipboardData.getData('text/plain');
                const selection = window.getSelection();
                if (selection && selection.rangeCount > 0) {
                  const range = selection.getRangeAt(0);
                  range.deleteContents();
                  range.insertNode(document.createTextNode(text));
                  range.collapse(false);
                  
                  // 触发 input 事件
                  const element = e.currentTarget;
                  const event = new Event('input', { bubbles: true });
                  element.dispatchEvent(event);
                }
              }
            }}
            data-placeholder={block.isAsrWriting ? '>' : getPlaceholder(block.type)}
            spellCheck={false}
            suppressHydrationWarning
            style={block.isAsrWriting ? { cursor: 'not-allowed', opacity: 0.7 } : undefined}
            dangerouslySetInnerHTML={{ __html: block.content }}
          />
          {hasTimeInfo && (
            <TimelineIndicator startTime={block.startTime} endTime={block.endTime} />
          )}
        </div>
        <button 
          className="block-delete-btn"
          onClick={(e) => {
            e.stopPropagation();
            handleDeleteBlock(block.id);
          }}
          title="删除此块"
        >
          🗑️
        </button>
      </div>
    );
  };

  return (
    <div className="block-editor">
      <div className="block-editor-content">
        {blocks.map(renderBlock)}
      </div>
    </div>
  );
});
