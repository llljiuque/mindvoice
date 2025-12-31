import React from 'react';
import './Sidebar.css';

export type AppView = 'voice-note' | 'voice-chat' | 'voice-zen' | 'history' | 'settings' | 'about';

interface SidebarProps {
  activeView: AppView;
  onViewChange: (view: AppView) => void;
  activeWorkingApp?: AppView | null;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeView, onViewChange, activeWorkingApp }) => {
  const isLocked = (view: AppView): boolean => {
    if (!activeWorkingApp) return false;
    // 应用分类：工作应用和非工作应用
    const workingApps: AppView[] = ['voice-note', 'voice-chat', 'voice-zen'];
    const utilityViews: AppView[] = ['history', 'settings', 'about'];
    
    if (workingApps.includes(view) && workingApps.includes(activeWorkingApp)) {
      // 工作应用之间互锁
      return view !== activeWorkingApp;
    }
    
    if (utilityViews.includes(view) && workingApps.includes(activeWorkingApp)) {
      // 有工作应用在运行时，工具视图被锁定
      return true;
    }
    
    return false;
  };

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <span className="logo-icon">🎤</span>
        </div>
      </div>
      
      <div className="sidebar-content">
        <nav className="sidebar-nav">
          <button
            className={`nav-item ${activeView === 'voice-note' ? 'active' : ''} ${isLocked('voice-note') ? 'locked' : ''}`}
            onClick={() => onViewChange('voice-note')}
            aria-label="语音笔记"
            aria-current={activeView === 'voice-note' ? 'page' : undefined}
            disabled={isLocked('voice-note')}
            title="语音笔记"
          >
            <span className="nav-icon" aria-hidden="true">📝</span>
            {isLocked('voice-note') && <span className="nav-lock-badge" aria-hidden="true">🔒</span>}
          </button>
          
          <button
            className={`nav-item ${activeView === 'voice-chat' ? 'active' : ''} ${isLocked('voice-chat') ? 'locked' : ''}`}
            onClick={() => onViewChange('voice-chat')}
            aria-label="语音助手"
            aria-current={activeView === 'voice-chat' ? 'page' : undefined}
            disabled={isLocked('voice-chat')}
            title="语音助手"
          >
            <span className="nav-icon" aria-hidden="true">💬</span>
            {isLocked('voice-chat') && <span className="nav-lock-badge" aria-hidden="true">🔒</span>}
          </button>
          
          <button
            className={`nav-item ${activeView === 'voice-zen' ? 'active' : ''} ${isLocked('voice-zen') ? 'locked' : ''}`}
            onClick={() => onViewChange('voice-zen')}
            aria-label="禅"
            aria-current={activeView === 'voice-zen' ? 'page' : undefined}
            disabled={isLocked('voice-zen')}
            title="禅 - 与一禅小和尚对话"
          >
            <span className="nav-icon" aria-hidden="true">🧘</span>
            {isLocked('voice-zen') && <span className="nav-lock-badge" aria-hidden="true">🔒</span>}
          </button>
          
          <div className="nav-divider"></div>
          
          <button
            className={`nav-item ${activeView === 'history' ? 'active' : ''} ${isLocked('history') ? 'locked' : ''}`}
            onClick={() => onViewChange('history')}
            aria-label="历史记录"
            aria-current={activeView === 'history' ? 'page' : undefined}
            disabled={isLocked('history')}
            title="历史记录"
          >
            <span className="nav-icon" aria-hidden="true">📚</span>
            {isLocked('history') && <span className="nav-lock-badge" aria-hidden="true">🔒</span>}
          </button>
          
          <button
            className={`nav-item ${activeView === 'settings' ? 'active' : ''} ${isLocked('settings') ? 'locked' : ''}`}
            onClick={() => onViewChange('settings')}
            aria-label="设置"
            aria-current={activeView === 'settings' ? 'page' : undefined}
            disabled={isLocked('settings')}
            title="设置"
          >
            <span className="nav-icon" aria-hidden="true">⚙️</span>
            {isLocked('settings') && <span className="nav-lock-badge" aria-hidden="true">🔒</span>}
          </button>
          
          <button
            className={`nav-item ${activeView === 'about' ? 'active' : ''} ${isLocked('about') ? 'locked' : ''}`}
            onClick={() => onViewChange('about')}
            aria-label="关于"
            aria-current={activeView === 'about' ? 'page' : undefined}
            disabled={isLocked('about')}
            title="关于"
          >
            <span className="nav-icon" aria-hidden="true">ℹ️</span>
            {isLocked('about') && <span className="nav-lock-badge" aria-hidden="true">🔒</span>}
          </button>
        </nav>
      </div>
    </div>
  );
};

