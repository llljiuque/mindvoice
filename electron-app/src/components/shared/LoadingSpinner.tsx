import React from 'react';
import './LoadingSpinner.css';

interface LoadingSpinnerProps {
  size?: 'small' | 'medium' | 'large';
  text?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'medium',
  text,
}) => {
  return (
    <div className={`loading-spinner loading-spinner-${size}`}>
      <div className="spinner">
        <div className="spinner-circle"></div>
      </div>
      {text && <span className="loading-text">{text}</span>}
    </div>
  );
};

