/**
 * Preload脚本
 * 在渲染进程中运行，提供安全的API访问
 */
import { contextBridge, ipcRenderer } from 'electron';

// 暴露安全的API给渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
  getApiUrl: () => ipcRenderer.invoke('get-api-url'),
  checkApiServer: () => ipcRenderer.invoke('check-api-server'),
});

