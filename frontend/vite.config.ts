import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 端口固定，避免 PyCharm 或浏览器仍访问 5173 时静默切换到其他端口。
export default defineConfig({
  plugins: [vue()],
  server: { host: '127.0.0.1', port: 5173, strictPort: true },
})
