import { createRouter, createWebHashHistory } from 'vue-router'
import Overview from './pages/Overview.vue'
import Models from './pages/Models.vue'
import Skills from './pages/Skills.vue'
import Mcp from './pages/Mcp.vue'
import Agents from './pages/Agents.vue'

export const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', component: Overview, meta: { title: '总览', hint: '今日花费与最近 30 天趋势' } },
    { path: '/models', component: Models, meta: { title: '模型开销', hint: '按模型看 token 与费用，单价可修改' } },
    { path: '/skills', component: Skills, meta: { title: 'Skills', hint: 'Claude 与 Trae 已安装的技能' } },
    { path: '/mcp', component: Mcp, meta: { title: 'MCP', hint: '本地缓存的 MCP 服务与工具' } },
    { path: '/agents', component: Agents, meta: { title: 'Agents', hint: '本机可发现的子代理' } }
  ]
})
