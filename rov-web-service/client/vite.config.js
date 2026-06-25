import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
    plugins: [vue()],
    server: {
        proxy: {
            // 将 WebSocket 视频流代理到后端服务
            '/ws': {
                target: 'ws://localhost:3000',
                ws: true,
                changeOrigin: true
            },
            // 健康检查等 HTTP 接口代理
            '/health': {
                target: 'http://localhost:3000',
                changeOrigin: true
            }
        }
    }
})
