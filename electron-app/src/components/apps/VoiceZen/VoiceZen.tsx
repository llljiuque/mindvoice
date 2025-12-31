import React, { useState } from 'react';
import { AppLayout } from '../../shared/AppLayout';
import ZenWelcome from './ZenWelcome';
import ZenChat from './ZenChat';
import './VoiceZen.css';

/**
 * 禅 - 角色扮演对话应用
 * 
 * 与一禅小和尚进行对话，获得心灵的平静
 * 
 * 核心功能（待实现）：
 * 1. 长记忆库（多层记忆系统）
 * 2. 知识库（禅宗故事、公案）
 * 3. 图片库（禅意图片和gif）
 * 4. 音频库（背景音乐、自然音效）
 * 5. 用户画像（多维度分析）
 * 6. 情绪分析（自动选择合适的图片和音乐）
 * 
 * 当前状态：脚手架阶段
 */
const VoiceZen: React.FC = () => {
  const [isStarted, setIsStarted] = useState(false);

  const handleStart = () => {
    setIsStarted(true);
  };

  const handleExit = () => {
    setIsStarted(false);
  };

  return (
    <AppLayout
      title="禅 Zen"
      subtitle="与一禅小和尚对话"
      icon="🧘"
    >
      <div className="voice-zen">
        {!isStarted ? (
          <ZenWelcome onStart={handleStart} />
        ) : (
          <ZenChat onExit={handleExit} />
        )}
      </div>
    </AppLayout>
  );
};

export default VoiceZen;

