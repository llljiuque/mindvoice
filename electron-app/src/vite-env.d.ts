/// <reference types="vite/client" />
/// <reference types="vite-plugin-svgr/client" />

// SVG 作为 URL 字符串导入
declare module '*.svg' {
  const content: string;
  export default content;
}

// SVG 作为 React 组件导入（使用 ?react 后缀）
declare module '*.svg?react' {
  import * as React from 'react';
  const SVGComponent: React.FC<React.SVGProps<SVGSVGElement>>;
  export default SVGComponent;
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

