import React, { useState, useRef, useEffect, useCallback, forwardRef, useImperativeHandle } from 'react';
import { Block, BlockType } from './Block';
import './BlockEditor.css';

interface BlockEditorProps {
  initialContent?: string;
  onContentChange?: (content: string) => void;
  isRecording?: boolean;
  isPaused?: boolean;
  onAsrTextUpdate?: (text: string) => void;
}

export interface BlockEditorHandle {
  appendAsrText: (text: string) => void;
}

export const BlockEditor = forwardRef<BlockEditorHandle, BlockEditorProps>(({
  initialContent = '',
  onContentChange,
  isRecording = false,
  isPaused = false,
  onAsrTextUpdate,
}, ref) => {
  const [blocks, setBlocks] = useState<Block[]>(() => {
    if (initialContent) {
      return initialContent.split('\n').map((line, index) => ({
        id: `block-${Date.now()}-${index}`,
        type: 'paragraph' as BlockType,
        content: line,
      }));
    }
    return [createEmptyBlock()];
  });

  const [focusedBlockId, setFocusedBlockId] = useState<string | null>(null);
  const editorRef = useRef<HTMLDivElement>(null);

  // 同步外部内容变化到块编辑器
  useEffect(() => {
    if (initialContent !== undefined) {
      const currentContent = blocks.map(b => b.content).join('\n');
      // 只在内容真正变化时更新，避免循环更新
      if (currentContent !== initialContent) {
        const lines = initialContent.split('\n');
        const newBlocks = lines.length > 0 
          ? lines.map((line, index) => ({
              id: `block-${Date.now()}-${index}`,
              type: 'paragraph' as BlockType,
              content: line,
            }))
          : [createEmptyBlock()];
        setBlocks(newBlocks);
      }
    }
  }, [initialContent]);

  // ASR 文本更新处理 - 追加 ASR 文本到最后一个块
  const appendAsrText = useCallback((newText: string) => {
    // 只有在录音且未暂停时才追加
    if (!isRecording || isPaused || !newText) return;
    
    setBlocks((prev) => {
      const updated = [...prev];
      const lastBlock = updated[updated.length - 1];
      if (lastBlock) {
        // 追加到最后一个块
        // 注意：这会触发Block组件的useEffect，但只有最后一个块有焦点时才会保护光标
        // 如果用户正在编辑其他块，光标位置不会受影响
        updated[updated.length - 1] = {
          ...lastBlock,
          content: lastBlock.content + newText,
        };
      } else {
        // 如果没有块，创建一个新块
        updated.push({
          id: `block-${Date.now()}`,
          type: 'paragraph',
          content: newText,
        });
      }
      const contentString = updated.map((b) => b.content).join('\n');
      // 通知父组件内容变化（但不触发用户编辑标记）
      onContentChange?.(contentString);
      return updated;
    });
  }, [isRecording, isPaused, onContentChange]);

  // 暴露方法给父组件
  useImperativeHandle(ref, () => ({
    appendAsrText,
  }));

  function createEmptyBlock(): Block {
    return {
      id: `block-${Date.now()}-${Math.random()}`,
      type: 'paragraph',
      content: '',
    };
  }

  const handleBlockUpdate = useCallback((id: string, content: string) => {
    setBlocks((prev) => {
      const updated = prev.map((block) =>
        block.id === id ? { ...block, content } : block
      );
      const contentString = updated.map((b) => b.content).join('\n');
      onContentChange?.(contentString);
      return updated;
    });
  }, [onContentChange]);

  const handleBlockTypeChange = useCallback((id: string, type: BlockType) => {
    setBlocks((prev) =>
      prev.map((block) => (block.id === id ? { ...block, type } : block))
    );
  }, []);

  const handleBlockFocus = useCallback((id: string) => {
    setFocusedBlockId(id);
  }, []);

  const handleBlockBlur = useCallback(() => {
    // 延迟清除焦点，以便点击其他块时能正确切换
    setTimeout(() => {
      setFocusedBlockId(null);
    }, 100);
  }, []);

  const handleBlockKeyDown = useCallback(
    (e: React.KeyboardEvent, id: string) => {
      const currentIndex = blocks.findIndex((b) => b.id === id);

      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        const newBlock = createEmptyBlock();
        setBlocks((prev) => {
          const newBlocks = [...prev];
          newBlocks.splice(currentIndex + 1, 0, newBlock);
          return newBlocks;
        });
        setTimeout(() => {
          setFocusedBlockId(newBlock.id);
        }, 0);
      } else if (e.key === 'Backspace' && blocks[currentIndex].content === '') {
        if (blocks.length > 1) {
          e.preventDefault();
          setBlocks((prev) => prev.filter((b) => b.id !== id));
          if (currentIndex > 0) {
            setTimeout(() => {
              setFocusedBlockId(blocks[currentIndex - 1].id);
            }, 0);
          }
        }
      } else if (e.key === 'ArrowUp' && currentIndex > 0) {
        e.preventDefault();
        setFocusedBlockId(blocks[currentIndex - 1].id);
      } else if (e.key === 'ArrowDown' && currentIndex < blocks.length - 1) {
        e.preventDefault();
        setFocusedBlockId(blocks[currentIndex + 1].id);
      }
    },
    [blocks]
  );

  const handleBlockDelete = useCallback((id: string) => {
    if (blocks.length > 1) {
      setBlocks((prev) => prev.filter((b) => b.id !== id));
    }
  }, [blocks.length]);

  return (
    <div className="block-editor" ref={editorRef}>
      <div className="block-editor-content">
        {blocks.map((block) => (
          <Block
            key={block.id}
            block={block}
            isFocused={focusedBlockId === block.id}
            onUpdate={handleBlockUpdate}
            onTypeChange={handleBlockTypeChange}
            onFocus={handleBlockFocus}
            onBlur={handleBlockBlur}
            onKeyDown={handleBlockKeyDown}
            onDelete={handleBlockDelete}
          />
        ))}
      </div>
    </div>
  );
});

