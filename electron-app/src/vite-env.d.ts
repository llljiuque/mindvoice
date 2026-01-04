/// <reference types="vite/client" />

declare module '*.svg' {
  const content: string;
  export default content;
}

declare module '*.png' {
  const content: string;
  export default content;
}

declare module '*.jpg' {
  const content: string;
  export default content;
}

declare module '*.jpeg' {
  const content: string;
  export default content;
}

declare module '*.gif' {
  const content: string;
  export default content;
}

declare module '*.webp' {
  const content: string;
  export default content;
}

// Electron API 类型定义
interface ElectronAPI {
  getApiUrl: () => Promise<string>;
  checkApiServer: () => Promise<boolean>;
  setPortraitMode: () => Promise<void>;
  setLandscapeMode: () => Promise<void>;
  maximizeWindow: () => Promise<void>;
  closeWindow: () => Promise<void>;
  quitApp: () => Promise<void>;
  // IPC 消息监听（修复版）
  onAsrMessage: (callback: (message: any) => void) => void;
  removeAllAsrMessageListeners: () => void;
}

declare global {
  interface Window {
    electronAPI?: ElectronAPI;
  }
}

export {};

