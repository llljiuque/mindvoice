/**
 * Icon 组件展示页面
 * 
 * 这是一个开发时使用的展示页面，用于：
 * 1. 查看所有可用的图标
 * 2. 测试图标的不同状态和属性
 * 3. 作为使用示例参考
 * 
 * 使用方式：在 App.tsx 中临时导入此组件查看效果
 */

import React, { useState } from 'react';
import { Icon, getAvailableIcons } from './index';
import './IconShowcase.css';

export const IconShowcase: React.FC = () => {
  const [size, setSize] = useState(24);
  const [color, setColor] = useState('#333333');
  const icons = getAvailableIcons();

  return (
    <div className="icon-showcase">
      <h1>Icon 组件展示</h1>
      
      {/* 控制面板 */}
      <div className="showcase-controls">
        <div className="control-group">
          <label>
            大小: {size}px
            <input 
              type="range" 
              min="16" 
              max="64" 
              value={size}
              onChange={(e) => setSize(Number(e.target.value))}
            />
          </label>
        </div>
        
        <div className="control-group">
          <label>
            颜色:
            <input 
              type="color" 
              value={color}
              onChange={(e) => setColor(e.target.value)}
            />
            <input 
              type="text" 
              value={color}
              onChange={(e) => setColor(e.target.value)}
              placeholder="#333333"
            />
          </label>
        </div>
      </div>

      {/* 图标网格 */}
      <section className="showcase-section">
        <h2>所有图标 ({icons.length})</h2>
        <div className="icon-grid">
          {icons.map(name => (
            <div key={name} className="icon-card">
              <Icon name={name} size={size} color={color} />
              <span className="icon-name">{name}</span>
            </div>
          ))}
        </div>
      </section>

      {/* 尺寸示例 */}
      <section className="showcase-section">
        <h2>不同尺寸</h2>
        <div className="icon-row">
          <div className="icon-example">
            <Icon name="mic" size={16} />
            <span>16px (小)</span>
          </div>
          <div className="icon-example">
            <Icon name="mic" size={24} />
            <span>24px (默认)</span>
          </div>
          <div className="icon-example">
            <Icon name="mic" size={32} />
            <span>32px (中)</span>
          </div>
          <div className="icon-example">
            <Icon name="mic" size={48} />
            <span>48px (大)</span>
          </div>
        </div>
      </section>

      {/* 颜色示例 */}
      <section className="showcase-section">
        <h2>不同颜色</h2>
        <div className="icon-row">
          <div className="icon-example">
            <Icon name="camera" size={32} color="#1890ff" />
            <span>Primary</span>
          </div>
          <div className="icon-example">
            <Icon name="camera" size={32} color="#52c41a" />
            <span>Success</span>
          </div>
          <div className="icon-example">
            <Icon name="camera" size={32} color="#faad14" />
            <span>Warning</span>
          </div>
          <div className="icon-example">
            <Icon name="camera" size={32} color="#f5222d" />
            <span>Error</span>
          </div>
          <div className="icon-example" style={{ color: '#722ed1' }}>
            <Icon name="camera" size={32} />
            <span>currentColor</span>
          </div>
        </div>
      </section>

      {/* 可点击示例 */}
      <section className="showcase-section">
        <h2>可点击图标</h2>
        <div className="icon-row">
          <Icon 
            name="copy" 
            size={32}
            onClick={() => alert('复制已点击')}
            title="点击复制"
          />
          <Icon 
            name="translate" 
            size={32}
            onClick={() => alert('翻译已点击')}
            title="点击翻译"
          />
          <Icon 
            name="report" 
            size={32}
            onClick={() => alert('报告已点击')}
            title="点击查看报告"
          />
        </div>
      </section>

      {/* 禁用状态 */}
      <section className="showcase-section">
        <h2>禁用状态</h2>
        <div className="icon-row">
          <div className="icon-example">
            <Icon name="mic" size={32} />
            <span>正常</span>
          </div>
          <div className="icon-example">
            <Icon name="mic" size={32} disabled />
            <span>禁用</span>
          </div>
          <div className="icon-example">
            <Icon 
              name="mic" 
              size={32} 
              disabled 
              onClick={() => alert('不会触发')}
            />
            <span>禁用+点击</span>
          </div>
        </div>
      </section>

      {/* 实际应用示例 */}
      <section className="showcase-section">
        <h2>实际应用示例</h2>
        
        <div className="example-group">
          <h3>工具栏</h3>
          <div className="toolbar-example">
            <button className="toolbar-button">
              <Icon name="mic" size={20} />
            </button>
            <button className="toolbar-button">
              <Icon name="camera" size={20} />
            </button>
            <button className="toolbar-button">
              <Icon name="copy" size={20} />
            </button>
            <button className="toolbar-button">
              <Icon name="translate" size={20} />
            </button>
            <button className="toolbar-button">
              <Icon name="report" size={20} />
            </button>
          </div>
        </div>

        <div className="example-group">
          <h3>按钮中使用</h3>
          <button className="primary-button">
            <Icon name="mic" size={18} color="white" />
            <span>开始录音</span>
          </button>
          <button className="secondary-button">
            <Icon name="report" size={18} />
            <span>查看报告</span>
          </button>
        </div>

        <div className="example-group">
          <h3>列表项</h3>
          <div className="list-item">
            <Icon name="mic" size={20} color="#1890ff" />
            <span>语音输入</span>
          </div>
          <div className="list-item">
            <Icon name="camera" size={20} color="#1890ff" />
            <span>图片识别</span>
          </div>
          <div className="list-item">
            <Icon name="translate" size={20} color="#1890ff" />
            <span>实时翻译</span>
          </div>
        </div>
      </section>

      {/* 代码示例 */}
      <section className="showcase-section">
        <h2>代码示例</h2>
        <pre className="code-block">
{`import { Icon } from '@/components/shared/Icon';

// 基础使用
<Icon name="mic" />

// 自定义大小和颜色
<Icon name="mic" size={32} color="#1890ff" />

// 可点击
<Icon 
  name="copy" 
  onClick={handleCopy}
  title="复制"
/>

// 禁用状态
<Icon name="mic" disabled />

// 在按钮中
<button>
  <Icon name="mic" size={20} />
  <span>开始录音</span>
</button>`}
        </pre>
      </section>
    </div>
  );
};

export default IconShowcase;

