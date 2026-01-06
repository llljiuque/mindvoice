import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import svgr from 'vite-plugin-svgr';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  base: './', // 使用相对路径，适配 Electron 的 file:// 协议
  plugins: [
    react(),
    svgr({
      // svgr 配置选项
      svgrOptions: {
        // SVG 作为 React 组件导入时的配置
        icon: true, // 默认移除 width 和 height，使用父容器尺寸
        exportType: 'default', // 导出为默认导出
      },
      // 只对带 ?react 后缀的 SVG 文件使用 svgr
      include: '**/*.svg?react',
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
});

