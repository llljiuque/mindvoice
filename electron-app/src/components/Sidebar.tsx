import React from 'react';
import './Sidebar.css';

interface SidebarProps {
  activeView: 'workspace' | 'history' | 'settings';
  onViewChange: (view: 'workspace' | 'history' | 'settings') => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeView, onViewChange }) => {
  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <span className="logo-icon">🎤</span>
          <span className="logo-text">MindVoice</span>
        </div>
      </div>
      
      <div className="sidebar-content">
        <nav className="sidebar-nav">
          <button
            className={`nav-item ${activeView === 'workspace' ? 'active' : ''}`}
            onClick={() => onViewChange('workspace')}
          >
            <span className="nav-icon">📝</span>
            <span className="nav-text">工作区</span>
          </button>
          
          <button
            className={`nav-item ${activeView === 'history' ? 'active' : ''}`}
            onClick={() => onViewChange('history')}
          >
            <span className="nav-icon">📚</span>
            <span className="nav-text">历史记录</span>
          </button>
          
          <button
            className={`nav-item ${activeView === 'settings' ? 'active' : ''}`}
            onClick={() => onViewChange('settings')}
          >
            <span className="nav-icon">⚙️</span>
            <span className="nav-text">设置</span>
          </button>
        </nav>
      </div>
    </div>
  );
};

