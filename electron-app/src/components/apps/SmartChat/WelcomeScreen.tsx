import React from 'react';
import { AppButton } from '../../shared/AppButton';
import './WelcomeScreen.css';

interface WelcomeScreenProps {
  onStartWork: () => void;
}

export const WelcomeScreen: React.FC<WelcomeScreenProps> = ({ onStartWork }) => {
  return (
    <div className="smartchat-welcome-screen">
      <div className="welcome-content">
        <div className="welcome-icon">💬</div>
        <h3 className="welcome-title">开始对话</h3>
        <p className="welcome-description">
          智能对话，支持知识库检索，随时为您服务
        </p>
        
        <div className="welcome-features">
          <div className="feature-item">
            <span className="feature-icon">💬</span>
            <span className="feature-text">多轮对话</span>
          </div>
          
          <div className="feature-item">
            <span className="feature-icon">📚</span>
            <span className="feature-text">知识库增强</span>
          </div>
          
          <div className="feature-item">
            <span className="feature-icon">⚡</span>
            <span className="feature-text">实时响应</span>
          </div>
          
          <div className="feature-item">
            <span className="feature-icon">🎯</span>
            <span className="feature-text">智能理解</span>
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
          开始对话
        </AppButton>
        <div className="footer-hint">
          点击开始，使用文字与AI交互
        </div>
      </div>
    </div>
  );
};

