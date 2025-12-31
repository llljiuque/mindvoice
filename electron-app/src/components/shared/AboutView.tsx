import React from 'react';
import { APP_VERSION } from '../../version';
import './AboutView.css';

export const AboutView: React.FC = () => {
  const { version, releaseDate } = APP_VERSION;
  
  return (
    <div className="about-view">
      <div className="about-container">
        <div className="about-header">
          <div className="about-logo">
            <span className="about-logo-icon">🎤</span>
          </div>
          <h1 className="about-title">MindVoice</h1>
          <p className="about-subtitle">AI驱动的语音桌面助手</p>
        </div>

        <div className="about-content">
          <div className="about-section">
            <h2 className="section-title">版本信息</h2>
            <div className="info-grid">
              <div className="info-item">
                <span className="info-label">版本号</span>
                <span className="info-value">{version}</span>
              </div>
              <div className="info-item">
                <span className="info-label">发布日期</span>
                <span className="info-value">{releaseDate}</span>
              </div>
            </div>
          </div>

          <div className="about-section">
            <h2 className="section-title">开发者</h2>
            <div className="developer-info">
              <p className="developer-name">深圳王哥 & AI</p>
              <div className="contact-info">
                <span className="contact-label">联系方式：</span>
                <a href="mailto:manwjh@126.com" className="contact-link">
                  manwjh@126.com
                </a>
              </div>
            </div>
          </div>

          <div className="about-section">
            <h2 className="section-title">关于项目</h2>
            <p className="about-description">
              MindVoice 是一款结合了语音识别(ASR)和大语言模型(LLM)的智能桌面助手。
              通过先进的AI技术，为您提供流畅的语音笔记、智能对话等功能，
              让语音交互变得更加自然和高效。
            </p>
          </div>

          <div className="about-section">
            <h2 className="section-title">技术栈</h2>
            <div className="tech-stack">
              <span className="tech-badge">Electron</span>
              <span className="tech-badge">React</span>
              <span className="tech-badge">TypeScript</span>
              <span className="tech-badge">Python</span>
              <span className="tech-badge">FastAPI</span>
              <span className="tech-badge">WebSocket</span>
            </div>
          </div>

          <div className="about-footer">
            <p className="copyright">© 2025 深圳王哥 & AI. All rights reserved.</p>
          </div>
        </div>
      </div>
    </div>
  );
};

