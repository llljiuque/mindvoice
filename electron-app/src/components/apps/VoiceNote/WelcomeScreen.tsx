import React from 'react';
import { AppButton } from '../../shared/AppButton';
import './WelcomeScreen.css';

interface WelcomeScreenProps {
  onStartWork: () => void;
}

export const WelcomeScreen: React.FC<WelcomeScreenProps> = ({ onStartWork }) => {
  return (
    <div className="welcome-screen">
      <div className="welcome-content">
        <div className="welcome-icon">📝</div>
        <h3 className="welcome-title">开始笔记</h3>
        <p className="welcome-description">
          点击下方按钮开始新的笔记会话
        </p>
        
        <div className="welcome-features">
          <div className="feature-item">
            <span className="feature-icon">🎤</span>
            <span className="feature-text">语音输入</span>
          </div>
          
          <div className="feature-item">
            <span className="feature-icon">📊</span>
            <span className="feature-text">会议记录</span>
          </div>
          
          <div className="feature-item">
            <span className="feature-icon">💾</span>
            <span className="feature-text">自动保存</span>
          </div>
        </div>
      </div>
      
      <div className="welcome-footer">
        <AppButton
          onClick={onStartWork}
          variant="primary"
          size="large"
          icon="✨"
          className="start-btn"
        >
          开始新笔记
        </AppButton>
        <div className="footer-hint">
          点击开始，填写会议信息并记录内容
        </div>
      </div>
    </div>
  );
};

