/**
 * 应用版本信息配置
 * 
 * 设计说明：
 * - 这是全局版本号的唯一来源
 * - GitHub 版本快照信息保存在 Git 仓库中，拉取代码时即可使用
 * - 维护者可以在发布新版本前通过 sync-github-snapshot.js 手动更新快照信息
 * - 构建时直接使用 Git 仓库中的快照信息，不进行网络请求
 * - 运行时直接使用编译后的版本快照信息，无需网络请求
 */

// ==================== 类型定义 ====================

export interface GitHubOwner {
  login: string;
  avatar_url: string;
  html_url: string;
  type: string;
}

export interface GitHubContributor {
  login: string;
  avatar_url: string;
  html_url: string;
  contributions: number;
}

// ==================== GitHub 版本快照信息 ====================
// 
// 设计说明：
// - 这些信息保存在 Git 仓库中，是快照信息的唯一来源
// - 维护者可以在发布新版本前运行 npm run sync:github 更新快照信息
// - 更新后的快照信息需要提交到 Git 仓库
// - 构建时直接使用 Git 仓库中的快照信息，不进行网络请求
// - 这是该版本的"快照"，代表版本发布时的贡献者状态
// - 运行时直接使用，无需网络请求，保证离线可用性

const VERSION_GITHUB_OWNER: GitHubOwner = {
  login: 'manwjh',
  avatar_url: 'https://avatars.githubusercontent.com/u/7723271?v=4',
  html_url: 'https://github.com/manwjh',
  type: 'User'
};

const VERSION_GITHUB_CONTRIBUTORS: GitHubContributor[] = [
  {
    login: 'manwjh',
    avatar_url: 'https://avatars.githubusercontent.com/u/7723271?v=4',
    html_url: 'https://github.com/manwjh',
    contributions: 34
  }
];

// ==================== 应用版本配置 ====================

export const APP_VERSION = {
  version: '1.9.5',
  releaseDate: '2026-01-06',
  name: 'MindVoice',
  description: 'AI驱动的语音桌面助手',
  github: {
    // GitHub 仓库地址，格式：owner/repo
    repository: 'manwjh/mindvoice',
    // 完整的 GitHub URL
    url: 'https://github.com/manwjh/mindvoice',
    // 版本快照信息：Git 仓库中保存的该版本发布时刻的贡献者信息（运行时直接使用，无需网络请求）
    snapshot: {
      owner: VERSION_GITHUB_OWNER,
      contributors: VERSION_GITHUB_CONTRIBUTORS
    }
  }
} as const;

