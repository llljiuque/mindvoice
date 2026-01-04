import React, { useState, useRef, useEffect } from 'react';
import './LanguageSelector.css';

export type LanguageType = 'original' | 'zh-en' | 'zh-ja' | 'zh-ko' | 'en-zh' | 'ja-zh' | 'ko-zh';

interface LanguageOption {
  value: LanguageType;
  label: string;
  icon: string;
}

const LANGUAGE_OPTIONS: LanguageOption[] = [
  { value: 'original', label: '原文', icon: '📄' },
  { value: 'zh-en', label: '中文→英文', icon: '🇨🇳→🇬🇧' },
  { value: 'zh-ja', label: '中文→日文', icon: '🇨🇳→🇯🇵' },
  { value: 'zh-ko', label: '中文→韩文', icon: '🇨🇳→🇰🇷' },
  { value: 'en-zh', label: '英文→中文', icon: '🇬🇧→🇨🇳' },
  { value: 'ja-zh', label: '日文→中文', icon: '🇯🇵→🇨🇳' },
  { value: 'ko-zh', label: '韩文→中文', icon: '🇰🇷→🇨🇳' },
];

interface LanguageSelectorProps {
  value: LanguageType;
  onChange: (language: LanguageType) => void;
  disabled?: boolean;
  loading?: boolean;
}

export const LanguageSelector: React.FC<LanguageSelectorProps> = ({
  value,
  onChange,
  disabled = false,
  loading = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const selectorRef = useRef<HTMLDivElement>(null);

  const selectedOption = LANGUAGE_OPTIONS.find(opt => opt.value === value) || LANGUAGE_OPTIONS[0];

  // 点击外部关闭下拉菜单
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (selectorRef.current && !selectorRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [isOpen]);

  const handleToggle = () => {
    if (!disabled && !loading) {
      setIsOpen(!isOpen);
    }
  };

  const handleSelect = (language: LanguageType) => {
    onChange(language);
    setIsOpen(false);
  };

  return (
    <div 
      className={`language-selector ${disabled ? 'disabled' : ''} ${isOpen ? 'open' : ''} ${loading ? 'loading' : ''}`}
      ref={selectorRef}
    >
      <button
        className="language-selector-trigger"
        onClick={handleToggle}
        disabled={disabled || loading}
        title="选择翻译语言"
        aria-label="翻译语言选择"
      >
        <span className="language-current">{selectedOption.icon} {selectedOption.label}</span>
        {loading ? (
          <span className="language-loading">
            <span className="loading-dot"></span>
          </span>
        ) : (
          <span className={`language-arrow ${isOpen ? 'rotate' : ''}`}>▼</span>
        )}
      </button>

      {isOpen && (
        <div className="language-dropdown">
          {LANGUAGE_OPTIONS.map(option => (
            <button
              key={option.value}
              className={`language-option ${option.value === value ? 'selected' : ''}`}
              onClick={() => handleSelect(option.value)}
            >
              <span className="option-icon">{option.icon}</span>
              <span className="option-label">{option.label}</span>
              {option.value === value && (
                <span className="option-check">✓</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

