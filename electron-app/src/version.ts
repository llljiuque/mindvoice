/**
 * 应用版本信息配置
 * 这是全局版本号的唯一来源
 */
export const APP_VERSION = {
  version: '1.9.2',
  releaseDate: '2026-01-06',
  name: 'MindVoice',
  description: 'AI驱动的语音桌面助手',
  github: {
    // GitHub 仓库地址，格式：owner/repo
    // 例如：'username/mindvoice' 或 'organization/mindvoice'
    repository: '', // 需要配置实际的仓库地址，例如：'manwjh/mindvoice'
    // 完整的 GitHub URL（可选，如果不提供会自动从 repository 生成）
    url: '' // 例如：'https://github.com/manwjh/mindvoice'
  }
} as const;

