import React from 'react';
import './Icon.css';
import { iconMap, IconName } from './iconRegistry';

export interface IconProps {
  /** 图标名称 */
  name: IconName;
  /** 图标大小（像素），默认 24 */
  size?: number;
  /** 图标颜色，支持 CSS 颜色值或 'currentColor'，默认继承文本颜色 */
  color?: string;
  /** 自定义类名 */
  className?: string;
  /** 点击事件 */
  onClick?: (e: React.MouseEvent) => void;
  /** 鼠标悬停提示 */
  title?: string;
  /** 是否禁用 */
  disabled?: boolean;
}

/**
 * 统一的图标组件
 * 
 * @example
 * ```tsx
 * // 基础使用
 * <Icon name="mic" />
 * 
 * // 自定义大小和颜色
 * <Icon name="mic" size={32} color="#1890ff" />
 * 
 * // 可点击图标
 * <Icon name="copy" onClick={handleCopy} title="复制" />
 * 
 * // 禁用状态
 * <Icon name="translate" disabled />
 * ```
 */
export const Icon: React.FC<IconProps> = ({
  name,
  size = 24,
  color = 'currentColor',
  className = '',
  onClick,
  title,
  disabled = false,
}) => {
  const IconComponent = iconMap[name];

  if (!IconComponent) {
    console.warn(`[Icon] 图标 "${name}" 不存在`);
    return null;
  }

  const handleClick = (e: React.MouseEvent) => {
    if (disabled) {
      e.preventDefault();
      return;
    }
    onClick?.(e);
  };

  return (
    <span
      className={`icon ${disabled ? 'icon--disabled' : ''} ${onClick ? 'icon--clickable' : ''} ${className}`}
      style={{
        width: size,
        height: size,
        color: disabled ? 'var(--color-disabled, #ccc)' : color,
      }}
      onClick={handleClick}
      title={title}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick && !disabled ? 0 : undefined}
    >
      <IconComponent />
    </span>
  );
};

export default Icon;

