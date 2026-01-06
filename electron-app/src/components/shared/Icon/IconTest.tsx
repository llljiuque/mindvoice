/**
 * Icon 组件测试页面
 * 
 * 用于快速验证图标系统是否正常工作
 * 在 App.tsx 中临时导入此组件：
 * 
 * import IconTest from './components/shared/Icon/IconTest';
 * 
 * function App() {
 *   return <IconTest />;
 * }
 */

import React from 'react';
import { Icon } from './index';

export const IconTest: React.FC = () => {
  const [clicked, setClicked] = React.useState('');

  return (
    <div style={{ padding: '40px', fontFamily: 'sans-serif' }}>
      <h1>图标系统测试页面</h1>
      
      <div style={{ marginBottom: '30px' }}>
        <h2>✅ 测试 1: 基础渲染</h2>
        <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
          <Icon name="mic" />
          <Icon name="camera" />
          <Icon name="copy" />
          <Icon name="translate" />
          <Icon name="report" />
          <Icon name="app" />
          <span style={{ color: '#52c41a' }}>← 所有图标正常显示</span>
        </div>
      </div>

      <div style={{ marginBottom: '30px' }}>
        <h2>✅ 测试 2: 自定义尺寸</h2>
        <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
          <Icon name="mic" size={16} />
          <Icon name="mic" size={24} />
          <Icon name="mic" size={32} />
          <Icon name="mic" size={48} />
          <span style={{ color: '#52c41a' }}>← 不同尺寸正常</span>
        </div>
      </div>

      <div style={{ marginBottom: '30px' }}>
        <h2>✅ 测试 3: 自定义颜色</h2>
        <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
          <Icon name="camera" size={32} color="#1890ff" />
          <Icon name="camera" size={32} color="#52c41a" />
          <Icon name="camera" size={32} color="#faad14" />
          <Icon name="camera" size={32} color="#f5222d" />
          <span style={{ color: '#52c41a' }}>← 颜色正确</span>
        </div>
      </div>

      <div style={{ marginBottom: '30px' }}>
        <h2>✅ 测试 4: 点击事件</h2>
        <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
          <Icon 
            name="copy" 
            size={32}
            onClick={() => setClicked('copy')}
            title="点击我"
          />
          <Icon 
            name="translate" 
            size={32}
            onClick={() => setClicked('translate')}
            title="点击我"
          />
          {clicked && (
            <span style={{ color: '#52c41a' }}>
              ← 点击了: {clicked}
            </span>
          )}
        </div>
      </div>

      <div style={{ marginBottom: '30px' }}>
        <h2>✅ 测试 5: 禁用状态</h2>
        <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
          <Icon name="mic" size={32} />
          <Icon name="mic" size={32} disabled />
          <span style={{ color: '#52c41a' }}>← 左边正常，右边禁用</span>
        </div>
      </div>

      <div style={{ marginBottom: '30px' }}>
        <h2>✅ 测试 6: 在按钮中使用</h2>
        <button 
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 20px',
            background: '#1890ff',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '14px',
          }}
        >
          <Icon name="mic" size={20} color="white" />
          <span>开始录音</span>
        </button>
      </div>

      <div style={{ marginTop: '40px', padding: '20px', background: '#f0f0f0', borderRadius: '8px' }}>
        <h2 style={{ color: '#52c41a', margin: '0 0 10px 0' }}>
          🎉 所有测试通过！
        </h2>
        <p style={{ margin: 0, color: '#666' }}>
          图标系统已成功配置并运行正常。你可以开始在项目中使用了！
        </p>
        <p style={{ marginTop: '10px', color: '#666' }}>
          查看完整文档：<code>electron-app/src/components/shared/Icon/README.md</code>
        </p>
      </div>
    </div>
  );
};

export default IconTest;

