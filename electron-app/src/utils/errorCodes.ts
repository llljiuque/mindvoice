/**
 * 系统错误码定义（前端）
 * 与后端 error_codes.py 保持一致
 */

export enum ErrorCategory {
  NETWORK = 'NETWORK',
  AUDIO_DEVICE = 'AUDIO_DEVICE',
  ASR_SERVICE = 'ASR_SERVICE',
  LLM_SERVICE = 'LLM_SERVICE',
  STORAGE = 'STORAGE',
  AUTH = 'AUTH',
  CONFIG = 'CONFIG',
  SYSTEM = 'SYSTEM',
}

export interface SystemErrorInfo {
  code: number;
  category: ErrorCategory;
  message: string;
  user_message: string;
  suggestion: string;
  details?: string;
  technical_info?: string;
}

// 错误码常量
export const ErrorCodes = {
  // 网络错误 (1000-1099)
  NETWORK_UNREACHABLE: 1000,
  NETWORK_TIMEOUT: 1001,
  WEBSOCKET_CONNECTION_FAILED: 1002,
  WEBSOCKET_DISCONNECTED: 1003,
  API_SERVER_UNAVAILABLE: 1004,

  // 音频设备错误 (2000-2099)
  AUDIO_DEVICE_NOT_FOUND: 2000,
  AUDIO_DEVICE_BUSY: 2001,
  AUDIO_DEVICE_PERMISSION_DENIED: 2002,
  AUDIO_DEVICE_FORMAT_NOT_SUPPORTED: 2003,
  AUDIO_DEVICE_OPEN_FAILED: 2004,
  AUDIO_STREAM_ERROR: 2005,

  // ASR服务错误 (3000-3099)
  ASR_AUTH_FAILED: 3000,
  ASR_QUOTA_EXCEEDED: 3001,
  ASR_SERVICE_UNAVAILABLE: 3002,
  ASR_REQUEST_TIMEOUT: 3003,
  ASR_AUDIO_FORMAT_ERROR: 3004,
  ASR_RATE_LIMIT: 3005,
  ASR_CONNECTION_BROKEN: 3006,
  ASR_NOT_CONFIGURED: 3007,

  // LLM服务错误 (4000-4099)
  LLM_AUTH_FAILED: 4000,
  LLM_QUOTA_EXCEEDED: 4001,
  LLM_SERVICE_UNAVAILABLE: 4002,
  LLM_REQUEST_TIMEOUT: 4003,
  LLM_RATE_LIMIT: 4004,
  LLM_MODEL_NOT_FOUND: 4005,
  LLM_RESPONSE_FORMAT_ERROR: 4006,
  LLM_NOT_CONFIGURED: 4007,

  // 存储错误 (5000-5099)
  STORAGE_CONNECTION_FAILED: 5000,
  STORAGE_WRITE_FAILED: 5001,
  STORAGE_READ_FAILED: 5002,
  STORAGE_DISK_FULL: 5003,

  // 配置错误 (6000-6099)
  CONFIG_FILE_NOT_FOUND: 6000,
  CONFIG_PARSE_ERROR: 6001,
  CONFIG_VALIDATION_ERROR: 6002,

  // 系统错误 (9000-9099)
  SYSTEM_INTERNAL_ERROR: 9000,
  SYSTEM_NOT_INITIALIZED: 9001,
  SYSTEM_RESOURCE_EXHAUSTED: 9002,
} as const;

// 错误码到类别的映射
export function getErrorCategory(code: number): ErrorCategory {
  if (code >= 1000 && code < 2000) return ErrorCategory.NETWORK;
  if (code >= 2000 && code < 3000) return ErrorCategory.AUDIO_DEVICE;
  if (code >= 3000 && code < 4000) return ErrorCategory.ASR_SERVICE;
  if (code >= 4000 && code < 5000) return ErrorCategory.LLM_SERVICE;
  if (code >= 5000 && code < 6000) return ErrorCategory.STORAGE;
  if (code >= 6000 && code < 7000) return ErrorCategory.CONFIG;
  if (code >= 9000 && code < 10000) return ErrorCategory.SYSTEM;
  return ErrorCategory.SYSTEM;
}

// 错误类别的显示名称
export const ErrorCategoryNames: Record<ErrorCategory, string> = {
  [ErrorCategory.NETWORK]: '网络错误',
  [ErrorCategory.AUDIO_DEVICE]: '音频设备错误',
  [ErrorCategory.ASR_SERVICE]: '语音识别错误',
  [ErrorCategory.LLM_SERVICE]: 'AI服务错误',
  [ErrorCategory.STORAGE]: '存储错误',
  [ErrorCategory.AUTH]: '认证错误',
  [ErrorCategory.CONFIG]: '配置错误',
  [ErrorCategory.SYSTEM]: '系统错误',
};

// 错误类别的图标
export const ErrorCategoryIcons: Record<ErrorCategory, string> = {
  [ErrorCategory.NETWORK]: '🌐',
  [ErrorCategory.AUDIO_DEVICE]: '🎤',
  [ErrorCategory.ASR_SERVICE]: '🗣️',
  [ErrorCategory.LLM_SERVICE]: '🤖',
  [ErrorCategory.STORAGE]: '💾',
  [ErrorCategory.AUTH]: '🔐',
  [ErrorCategory.CONFIG]: '⚙️',
  [ErrorCategory.SYSTEM]: '⚠️',
};

