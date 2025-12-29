import React from 'react';
import './FormatToolbar.css';

interface FormatToolbarProps {
  onFormat?: (format: string) => void;
  visible?: boolean;
}

export const FormatToolbar: React.FC<FormatToolbarProps> = ({
  onFormat,
  visible = false,
}) => {
  if (!visible) return null;

  return (
    <div className="format-toolbar">
      <button
        className="toolbar-btn"
        onClick={() => onFormat?.('bold')}
        title="粗体 (Ctrl+B)"
      >
        <strong>B</strong>
      </button>
      <button
        className="toolbar-btn"
        onClick={() => onFormat?.('italic')}
        title="斜体 (Ctrl+I)"
      >
        <em>I</em>
      </button>
      <button
        className="toolbar-btn"
        onClick={() => onFormat?.('code')}
        title="代码"
      >
        {'</>'}
      </button>
      <div className="toolbar-divider" />
      <button
        className="toolbar-btn"
        onClick={() => onFormat?.('h1')}
        title="标题 1"
      >
        H1
      </button>
      <button
        className="toolbar-btn"
        onClick={() => onFormat?.('h2')}
        title="标题 2"
      >
        H2
      </button>
      <button
        className="toolbar-btn"
        onClick={() => onFormat?.('h3')}
        title="标题 3"
      >
        H3
      </button>
    </div>
  );
};

