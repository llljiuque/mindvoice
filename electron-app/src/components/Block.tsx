import React, { useState, useRef, useEffect } from 'react';
import './Block.css';

export type BlockType = 'paragraph' | 'h1' | 'h2' | 'h3' | 'bulleted-list' | 'numbered-list' | 'code';

export interface Block {
  id: string;
  type: BlockType;
  content: string;
}

interface BlockProps {
  block: Block;
  isFocused: boolean;
  onUpdate: (id: string, content: string) => void;
  onTypeChange: (id: string, type: BlockType) => void;
  onFocus: (id: string) => void;
  onBlur: () => void;
  onKeyDown: (e: React.KeyboardEvent, id: string) => void;
  onDelete: (id: string) => void;
}

export const Block: React.FC<BlockProps> = ({
  block,
  isFocused,
  onUpdate,
  onTypeChange,
  onFocus,
  onBlur,
  onKeyDown,
  onDelete,
}) => {
  const [content, setContent] = useState(block.content);
  const contentRef = useRef<HTMLDivElement>(null);
  const cursorPositionRef = useRef<number | null>(null); // 保存光标在文本中的位置（字符偏移）
  const isUserEditingRef = useRef(false); // 跟踪用户是否正在编辑
  const lastSyncedContentRef = useRef<string>(block.content); // 记录上次同步到DOM的内容

  // 保存光标位置（相对于文本内容的字符位置）
  const saveCursorPosition = () => {
    if (!contentRef.current) return;
    
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) return;
    
    const range = selection.getRangeAt(0);
    if (!range) return;
    
    // 检查光标是否在当前块内
    if (!contentRef.current.contains(range.commonAncestorContainer)) {
      return;
    }
    
    // 计算光标在文本内容中的字符位置
    const preCaretRange = range.cloneRange();
    preCaretRange.selectNodeContents(contentRef.current);
    preCaretRange.setEnd(range.startContainer, range.startOffset);
    cursorPositionRef.current = preCaretRange.toString().length;
  };

  // 恢复光标位置
  const restoreCursorPosition = () => {
    if (!contentRef.current || cursorPositionRef.current === null) return;
    
    const targetPosition = cursorPositionRef.current;
    const textContent = contentRef.current.textContent || '';
    const maxPosition = textContent.length;
    const actualPosition = Math.min(targetPosition, maxPosition);
    
    // 设置光标位置
    setTimeout(() => {
      if (!contentRef.current) return;
      
      const selection = window.getSelection();
      if (!selection) return;
      
      try {
        // 使用更简单可靠的方法：直接设置文本节点的偏移
        const range = document.createRange();
        
        // 如果内容为空，设置到元素开始
        if (textContent.length === 0) {
          range.setStart(contentRef.current, 0);
          range.setEnd(contentRef.current, 0);
        } else {
          // 找到包含目标位置的文本节点
          const walker = document.createTreeWalker(
            contentRef.current,
            NodeFilter.SHOW_TEXT,
            null
          );
          
          let currentPosition = 0;
          let textNode: Node | null = null;
          let offset = 0;
          
          while (walker.nextNode()) {
            const node = walker.currentNode;
            const nodeLength = node.textContent?.length || 0;
            
            if (currentPosition + nodeLength >= actualPosition) {
              textNode = node;
              offset = actualPosition - currentPosition;
              break;
            }
            
            currentPosition += nodeLength;
          }
          
          // 如果没有找到文本节点，使用最后一个文本节点
          if (!textNode) {
            // 找到最后一个文本节点
            let lastTextNode: Node | null = null;
            const walker2 = document.createTreeWalker(
              contentRef.current,
              NodeFilter.SHOW_TEXT,
              null
            );
            while (walker2.nextNode()) {
              lastTextNode = walker2.currentNode;
            }
            
            if (lastTextNode && lastTextNode.nodeType === Node.TEXT_NODE) {
              textNode = lastTextNode;
              offset = lastTextNode.textContent?.length || 0;
            } else {
              // 如果没有文本节点，设置到元素末尾
              range.setStart(contentRef.current, contentRef.current.childNodes.length);
              range.setEnd(contentRef.current, contentRef.current.childNodes.length);
              selection.removeAllRanges();
              selection.addRange(range);
              return;
            }
          }
          
          // 设置到找到的文本节点
          if (textNode && textNode.nodeType === Node.TEXT_NODE) {
            const maxOffset = textNode.textContent?.length || 0;
            const safeOffset = Math.min(Math.max(0, offset), maxOffset);
            range.setStart(textNode, safeOffset);
            range.setEnd(textNode, safeOffset);
          } else {
            // 回退方案：设置到元素开始
            range.setStart(contentRef.current, 0);
            range.setEnd(contentRef.current, 0);
          }
        }
        
        selection.removeAllRanges();
        selection.addRange(range);
      } catch (e) {
        console.error('恢复光标位置失败:', e);
        // 回退：设置到元素开始
        try {
          const range = document.createRange();
          range.setStart(contentRef.current, 0);
          range.setEnd(contentRef.current, 0);
          const selection = window.getSelection();
          selection?.removeAllRanges();
          selection?.addRange(range);
        } catch (e2) {
          console.error('回退光标位置也失败:', e2);
        }
      }
    }, 0);
  };

  useEffect(() => {
    // 只有当外部内容改变且与当前内容不同时才更新
    if (block.content !== content && contentRef.current) {
      // 如果用户正在编辑，完全跳过更新，让浏览器自己管理
      if (isUserEditingRef.current) {
        // 只同步state，不更新DOM（避免干扰用户输入）
        setContent(block.content);
        return;
      }
      
      // 检查是否是用户正在编辑的块（有焦点且光标在块内）
      const selection = window.getSelection();
      const range = selection?.rangeCount > 0 ? selection.getRangeAt(0) : null;
      const isUserEditing = isFocused && 
                           contentRef.current === document.activeElement &&
                           range &&
                           contentRef.current.contains(range.commonAncestorContainer);
      
      // 如果用户正在编辑，完全跳过DOM更新，避免打断用户输入
      // ASR更新会在用户停止输入后通过applyPendingAsrOperations应用
      if (isUserEditing) {
        // 只同步state，不更新DOM（避免干扰用户输入）
        setContent(block.content);
        return;
      }
      
      // 非用户编辑时，更新DOM内容
      const currentText = contentRef.current.textContent || '';
      if (currentText !== block.content) {
        // 保存光标位置（如果有）
        saveCursorPosition();
        
        // 直接更新DOM，避免React重新渲染导致的问题
        contentRef.current.textContent = block.content;
        lastSyncedContentRef.current = block.content;
        setContent(block.content);
        
        // 恢复光标位置（如果之前有保存）
        if (cursorPositionRef.current !== null) {
          restoreCursorPosition();
        }
      }
    }
  }, [block.content, isFocused, content]);
  
  // 初始化时设置内容
  useEffect(() => {
    if (contentRef.current) {
      const currentText = contentRef.current.textContent || '';
      if (currentText !== block.content && !isUserEditingRef.current) {
        contentRef.current.textContent = block.content;
        lastSyncedContentRef.current = block.content;
      }
    }
  }, [block.content]);

  useEffect(() => {
    if (isFocused && contentRef.current) {
      contentRef.current.focus();
      // 只有在没有保存的光标位置时，才将光标移到末尾
      // 这样可以避免覆盖用户的光标位置
      if (cursorPositionRef.current === null) {
        const range = document.createRange();
        const sel = window.getSelection();
        if (contentRef.current.childNodes.length > 0) {
          range.selectNodeContents(contentRef.current);
          range.collapse(false);
        } else {
          range.setStart(contentRef.current, 0);
          range.setEnd(contentRef.current, 0);
        }
        sel?.removeAllRanges();
        sel?.addRange(range);
        // 更新保存的光标位置
        cursorPositionRef.current = contentRef.current.textContent?.length || 0;
      } else {
        // 恢复保存的光标位置
        restoreCursorPosition();
      }
    }
  }, [isFocused]);

  const handleInput = (e: React.FormEvent<HTMLDivElement>) => {
    const newContent = e.currentTarget.textContent || '';
    // 只有当内容真正改变时才更新，避免循环更新
    if (newContent !== content) {
      // 标记用户正在编辑
      isUserEditingRef.current = true;
      
      // 保存光标位置（用户输入时）
      saveCursorPosition();
      
      // 更新同步内容ref
      lastSyncedContentRef.current = newContent;
      
      setContent(newContent);
      onUpdate(block.id, newContent);
      
      // 延迟重置编辑状态，避免在快速输入时频繁更新
      // 延长到500ms，给ASR延迟应用留出时间
      setTimeout(() => {
        isUserEditingRef.current = false;
      }, 500);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    // 处理删除空块
    if (e.key === 'Backspace' && content === '' && block.type === 'paragraph') {
      e.preventDefault();
      onDelete(block.id);
      return;
    }

    onKeyDown(e, block.id);
  };

  const getTagName = () => {
    switch (block.type) {
      case 'h1':
        return 'h1';
      case 'h2':
        return 'h2';
      case 'h3':
        return 'h3';
      case 'code':
        return 'pre';
      default:
        return 'p';
    }
  };

  const getClassName = () => {
    const base = 'block-content';
    const typeClass = `block-${block.type}`;
    const focusClass = isFocused ? 'block-focused' : '';
    return `${base} ${typeClass} ${focusClass}`.trim();
  };

  const Tag = getTagName() as keyof JSX.IntrinsicElements;

  return (
    <div className={`block ${isFocused ? 'block-focused' : ''}`}>
      <div className="block-handle">
        <span className="handle-icon">⋮⋮</span>
      </div>
      <Tag
        ref={contentRef}
        className={getClassName()}
        contentEditable={true}
        suppressContentEditableWarning
        onInput={handleInput}
        onFocus={() => {
          isUserEditingRef.current = false; // 重置编辑状态
          onFocus(block.id);
        }}
        onBlur={() => {
          isUserEditingRef.current = false; // 重置编辑状态
          onBlur();
        }}
        onKeyDown={handleKeyDown}
        onPaste={(e) => {
          e.preventDefault();
          const text = e.clipboardData.getData('text/plain');
          document.execCommand('insertText', false, text);
        }}
        data-placeholder={getPlaceholder(block.type)}
        spellCheck={false}
        suppressHydrationWarning
      />
    </div>
  );
};

function getPlaceholder(type: BlockType): string {
  switch (type) {
    case 'h1':
      return '标题 1';
    case 'h2':
      return '标题 2';
    case 'h3':
      return '标题 3';
    case 'bulleted-list':
      return '列表项';
    case 'numbered-list':
      return '列表项';
    case 'code':
      return '代码';
    default:
      return '';
  }
}

