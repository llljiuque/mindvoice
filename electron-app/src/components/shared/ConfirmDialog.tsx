import React from 'react';
import { AppButton } from './AppButton';
import './ConfirmDialog.css';

export type DialogType = 'info' | 'warning' | 'danger';

interface DialogAction {
  label: string;
  variant: 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'info' | 'ghost';
  onClick: () => void;
}

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  type?: DialogType;
  actions: DialogAction[];
  onClose?: () => void;
}

const DIALOG_ICONS: Record<DialogType, string> = {
  info: 'ℹ️',
  warning: '⚠️',
  danger: '❌',
};

const DIALOG_COLORS: Record<DialogType, string> = {
  info: '#3b82f6',
  warning: '#f59e0b',
  danger: '#ef4444',
};

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  open,
  title,
  message,
  type = 'warning',
  actions,
  onClose,
}) => {
  if (!open) return null;

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget && onClose) {
      onClose();
    }
  };

  return (
    <div className="dialog-overlay" onClick={handleBackdropClick}>
      <div className="dialog-container">
        <div className="dialog-header" style={{ borderTopColor: DIALOG_COLORS[type] }}>
          <div className="dialog-icon" style={{ color: DIALOG_COLORS[type] }}>
            {DIALOG_ICONS[type]}
          </div>
          <h3 className="dialog-title">{title}</h3>
        </div>

        <div className="dialog-body">
          <p className="dialog-message">{message}</p>
        </div>

        <div className="dialog-footer">
          {actions.map((action, index) => (
            <AppButton
              key={index}
              variant={action.variant}
              onClick={action.onClick}
              className="dialog-action-btn"
            >
              {action.label}
            </AppButton>
          ))}
        </div>
      </div>
    </div>
  );
};

