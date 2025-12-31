import React from 'react';
import './ZenWelcome.css';

interface ZenWelcomeProps {
  onStart: () => void;
}

/**
 * 禅应用欢迎页面
 * 显示木鱼图标，点击开始对话
 */
const ZenWelcome: React.FC<ZenWelcomeProps> = ({ onStart }) => {
  return (
    <div className="zen-welcome">
      <div className="zen-welcome-content">
        <div className="muyu-container" onClick={onStart}>
          <div className="muyu-icon">
            <div className="muyu-body">
              <div className="muyu-pattern"></div>
              <div className="muyu-pattern"></div>
              <div className="muyu-pattern"></div>
            </div>
            <div className="muyu-shadow"></div>
          </div>
          <div className="muyu-text">木鱼</div>
          <div className="muyu-hint">点击开始与一禅对话</div>
        </div>
      </div>
    </div>
  );
};

export default ZenWelcome;

