<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark">A</div>
        <div class="brand-text">
          <strong>Agent Console</strong>
          <span>本地用量与资产</span>
        </div>
      </div>

      <nav class="nav">
        <RouterLink
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: $route.path === item.path }"
        >
          <span class="nav-dot" />
          {{ item.label }}
        </RouterLink>
      </nav>

      <div class="sidebar-foot">
        <b>只读扫描</b><br />
        数据来自本机 Claude Code 与 Trae Code 日志，不上传、不改配置。<br /><br />
        最近扫描<br />
        {{ lastScanText }}
      </div>
    </aside>

    <main class="main">
      <div class="topbar">
        <div>
          <h1>{{ $route.meta.title }}</h1>
          <p>{{ $route.meta.hint }}</p>
        </div>
        <div class="topbar-actions">
          <span v-if="prices" class="chip" :class="prices.verified ? 'brand' : 'warn'">
            <span class="dot" />
            {{ prices.verified ? '单价已核对' : '示例价 · 未核对' }}
          </span>
          <button class="btn" :disabled="scanning" @click="rescan">
            {{ scanning ? '扫描中…' : '重新扫描' }}
          </button>
        </div>
      </div>

      <RouterView />

      <div v-if="toast" class="toast">{{ toast }}</div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import { getOverview, scan } from './api'
import { bump, revision, scanning } from './store'
import { timeText } from './utils'

const navItems = [
  { path: '/', label: '总览' },
  { path: '/models', label: '模型开销' },
  { path: '/skills', label: 'Skills' },
  { path: '/mcp', label: 'MCP' },
  { path: '/agents', label: 'Agents' }
]

const prices = ref(null)
const lastScan = ref(null)
const toast = ref('')

const lastScanText = computed(() => {
  if (lastScan.value) return timeText(lastScan.value)
  return '尚未扫描'
})

function flash(message) {
  toast.value = message
  window.setTimeout(() => {
    toast.value = ''
  }, 2600)
}

async function loadHeader() {
  try {
    const data = await getOverview()
    prices.value = data.prices
    lastScan.value = data.last_scan
  } catch {
    prices.value = null
  }
}

async function rescan() {
  scanning.value = true
  try {
    const result = await scan(false)
    lastScan.value = result.last_scan
    const parsed = result.stats.reduce((sum, item) => sum + item.parsed, 0)
    const skipped = result.stats.reduce((sum, item) => sum + item.skipped, 0)
    flash(parsed ? `扫描完成，解析 ${parsed} 个文件` : `没有新记录（跳过 ${skipped} 个文件）`)
    bump()
    loadHeader()
  } catch (error) {
    flash(`扫描失败：${error.message}`)
  } finally {
    scanning.value = false
  }
}

onMounted(() => {
  loadHeader()
  if (window.desktop?.onScanDone) {
    window.desktop.onScanDone(async () => {
      await loadHeader()
      bump()
      flash('已重新扫描')
    })
  }
})

watch(revision, loadHeader)
</script>
