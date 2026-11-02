// 前端应用唯一入口：装载根组件和全局样式。
import { createApp } from 'vue'
import App from './App.vue'
import './styles.css'

// index.html 中的 #app 是 Vue 应用挂载点。
createApp(App).mount('#app')
