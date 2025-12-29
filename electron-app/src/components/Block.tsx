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
      // 检查是否是用户正在编辑的块（有焦点且光标在块内）
      const selection = window.getSelection();
      const range = selection?.rangeCount > 0 ? selection.getRangeAt(0) : null;
      const isUserEditing = isFocused && 
                           contentRef.current === document.activeElement &&
                           range &&
                           contentRef.current.contains(range.commonAncestorContainer);
      
      if (isUserEditing) {
        // 用户正在编辑：保存光标位置（在内容更新前）
        saveCursorPosition();
      }
      
      // 计算内容变化类型
      const isAppend = block.content.startsWith(content);
      const oldLength = content.length;
      
      setContent(block.content);
      
      if (isUserEditing) {
        // 恢复光标位置（在内容更新后）
        // 如果是追加内容，且用户光标在末尾，保持光标在末尾
        // 否则恢复保存的光标位置
        if (isAppend && cursorPositionRef.current !== null && cursorPositionRef.current >= oldLength) {
          // 用户光标在末尾，追加后也保持在末尾
          setTimeout(() => {
            const selection = window.getSelection();
            if (selection && contentRef.current) {
              const range = document.createRange();
              range.selectNodeContents(contentRef.current);
              range.collapse(false);
              selection.removeAllRanges();
              selection.addRange(range);
              cursorPositionRef.current = contentRef.current.textContent?.length || 0;
            }
          }, 0);
        } else {
          // 恢复保存的光标位置
          restoreCursorPosition();
        }
      } else {
        // 不是用户编辑的块，清除保存的光标位置
        cursorPositionRef.current = null;
      }
    }
  }, [block.content, isFocused]);

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
      // 用户输入时，保存光标位置（用于后续外部更新时恢复）
      // 但不立即恢复，让浏览器自然处理光标位置
      saveCursorPosition();
      
      setContent(newContent);
      onUpdate(block.id, newContent);
      
      // 注意：用户输入时不需要恢复光标位置
      // 浏览器会自动维护光标位置，我们只需要保存即可
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
        contentEditable
        suppressContentEditableWarning
        onInput={handleInput}
        onFocus={() => onFocus(block.id)}
        onBlur={onBlur}
        onKeyDown={handleKeyDown}
        data-placeholder={getPlaceholder(block.type)}
      >
        {content}
      </Tag>
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

