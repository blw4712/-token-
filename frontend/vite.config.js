import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// base 用相对路径：Electron 走 / 静态挂载、GitHub Pages 走子路径，两种都能用。
// 页面用的是 hash 路由，所以路径不会随页面切换而改变。
export default defineConfig({
  base: './',
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8765'
    }
  }
})
