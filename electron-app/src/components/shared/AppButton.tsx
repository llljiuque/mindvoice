import React, { ReactNode } from 'react';
import './AppButton.css';

export type ButtonVariant = 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'info' | 'ghost';
export type ButtonSize = 'small' | 'medium' | 'large';

interface AppButtonProps {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: string;
  className?: string;
  title?: string;
  ariaLabel?: string;
}

export const AppButton: React.FC<AppButtonProps> = ({
  children,
  onClick,
  disabled = false,
  variant = 'primary',
  size = 'medium',
  icon,
  className = '',
  title,
  ariaLabel,
}) => {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`app-button app-button-${variant} app-button-${size} ${className}`}
      title={title}
      aria-label={ariaLabel}
    >
      {icon && <span className="app-button-icon">{icon}</span>}
      <span className="app-button-text">{children}</span>
    </button>
  );
};

interface ButtonGroupProps {
  children: ReactNode;
  className?: string;
}

export const ButtonGroup: React.FC<ButtonGroupProps> = ({ children, className = '' }) => {
  return <div className={`app-button-group ${className}`}>{children}</div>;
};

