import React from 'react';
import { SystemErrorInfo, ErrorCategory, ErrorCategoryNames, ErrorCategoryIcons } from '../../utils/errorCodes';
import './SystemErrorDisplay.css';

interface SystemErrorDisplayProps {
  error: SystemErrorInfo | null;
  onClose?: () => void;
  onRetry?: () => void;
  showTechnicalInfo?: boolean;
}

/**
 * 系统错误展示组件
 * 用于统一展示系统级错误信息，包含错误码、用户友好提示和解决建议
 */
export const SystemErrorDisplay: React.FC<SystemErrorDisplayProps> = ({
  error,
  onClose,
  onRetry,
  showTechnicalInfo = false,
}) => {
  if (!error) return null;

  const categoryName = ErrorCategoryNames[error.category as ErrorCategory] || '未知错误';
  const categoryIcon = ErrorCategoryIcons[error.category as ErrorCategory] || '⚠️';

  return (
    <div className="system-error-display">
      <div className="system-error-header">
        <div className="system-error-title">
          <span className="error-icon">{categoryIcon}</span>
          <span className="error-category">{categoryName}</span>
          <span className="error-code">#{error.code}</span>
        </div>
        {onClose && (
          <button className="error-close-btn" onClick={onClose} aria-label="关闭">
            ×
          </button>
        )}
      </div>

      <div className="system-error-content">
        <div className="error-user-message">{error.user_message}</div>

        {error.details && (
          <div className="error-details">
            <strong>详情：</strong>
            {error.details}
          </div>
        )}

        {error.suggestion && (
          <div className="error-suggestion">
            <strong>解决建议：</strong>
            <div className="suggestion-content">
              {error.suggestion.split('\n').map((line, index) => (
                <div key={index} className="suggestion-line">
                  {line}
                </div>
              ))}
            </div>
          </div>
        )}

        {showTechnicalInfo && error.technical_info && (
          <details className="error-technical-info">
            <summary>技术信息</summary>
            <pre>{error.technical_info}</pre>
          </details>
        )}
      </div>

      <div className="system-error-actions">
        {onRetry && (
          <button className="error-action-btn retry-btn" onClick={onRetry}>
            重试
          </button>
        )}
        {onClose && (
          <button className="error-action-btn close-btn" onClick={onClose}>
            关闭
          </button>
        )}
      </div>
    </div>
  );
};

interface ErrorBannerProps {
  error: SystemErrorInfo | null;
  onClose?: () => void;
}

/**
 * 错误横幅组件
 * 用于在页面顶部显示简洁的错误提示
 */
export const ErrorBanner: React.FC<ErrorBannerProps> = ({ error, onClose }) => {
  if (!error) return null;

  const categoryIcon = ErrorCategoryIcons[error.category as ErrorCategory] || '⚠️';

  return (
    <div className="error-banner">
      <span className="banner-icon">{categoryIcon}</span>
      <span className="banner-message">{error.user_message}</span>
      <span className="banner-code">#{error.code}</span>
      {onClose && (
        <button className="banner-close-btn" onClick={onClose} aria-label="关闭">
          ×
        </button>
      )}
    </div>
  );
};

interface ErrorToastProps {
  error: SystemErrorInfo | null;
  duration?: number;
  onClose?: () => void;
}

/**
 * 错误Toast组件
 * 用于显示临时的错误提示，自动消失
 */
export const ErrorToast: React.FC<ErrorToastProps> = ({
  error,
  duration = 5000,
  onClose,
}) => {
  React.useEffect(() => {
    if (error && duration > 0) {
      const timer = setTimeout(() => {
        onClose?.();
      }, duration);
      return () => clearTimeout(timer);
    }
  }, [error, duration, onClose]);

  if (!error) return null;

  const categoryIcon = ErrorCategoryIcons[error.category as ErrorCategory] || '⚠️';

  return (
    <div className="error-toast">
      <span className="toast-icon">{categoryIcon}</span>
      <div className="toast-content">
        <div className="toast-message">{error.user_message}</div>
        {error.code && <div className="toast-code">错误码: {error.code}</div>}
      </div>
      {onClose && (
        <button className="toast-close-btn" onClick={onClose} aria-label="关闭">
          ×
        </button>
      )}
    </div>
  );
};

