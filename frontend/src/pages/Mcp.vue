<template>
  <div>
    <div v-if="error" class="empty"><strong>读取失败</strong>{{ error }}</div>
    <div v-else-if="!data" class="loading">正在读取 MCP 缓存…</div>

    <template v-else>
      <div class="search-row">
        <span class="chip">{{ data.total }} 个服务</span>
        <input v-model="keyword" class="input" placeholder="搜索服务名或工具名…" />
      </div>

      <div class="notice">
        只展示服务名、工具名和所在范围，不读取命令、地址或密钥。缓存里有记录说明安装过，
        不代表当前正在运行。
      </div>

      <div v-if="!filtered.length" class="empty">
        <strong>没有匹配的 MCP 服务</strong>换个关键词，或先在 Trae 里使用一次 MCP 工具。
      </div>

      <div v-for="server in filtered" :key="`${server.platform}-${server.name}`" class="server">
        <div class="server-head">
          <div class="server-name">
            <span class="avatar mcp-mark">M</span>
            <span class="mono">{{ server.name }}</span>
            <span :class="['tag', server.platform === 'claude' ? 'green' : 'blue']">
              {{ server.platform === 'claude' ? 'Claude' : 'Trae' }}
            </span>
            <span v-if="server.transport" class="tag">{{ server.transport }}</span>
          </div>
          <div class="pill-row">
            <span class="tag">{{ server.tool_count }} 个工具</span>
            <span :class="['tag', server.enabled ? 'green' : 'red']">
              {{ server.enabled ? '启用' : '停用' }}
            </span>
          </div>
        </div>

        <div class="instances">
          <span v-for="(item, index) in server.instances" :key="index" class="pill">
            {{ item.scope_label }}
            <template v-if="item.workspace"> · {{ shortWorkspace(item.workspace) }}</template>
            <template v-if="item.category"> · {{ item.category }}</template>
            <template v-if="!item.workspace && item.origin"> · {{ item.origin }}</template>
          </span>
        </div>

        <details v-if="server.tools.length">
          <summary>展开工具列表</summary>
          <div class="tool-list">
            <div class="tool-grid">
              <span v-for="tool in server.tools" :key="tool" class="tool mono">{{ tool }}</span>
            </div>
          </div>
        </details>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { getMcp } from '../api'
import { revision } from '../store'

const data = ref(null)
const keyword = ref('')
const error = ref('')

function shortWorkspace(value) {
  const text = String(value || '')
  const parts = text.split('-')
  return parts.length > 1 ? parts.slice(1).join('-') : text
}

const filtered = computed(() => {
  const items = data.value?.servers || []
  const text = keyword.value.trim().toLowerCase()
  if (!text) return items
  return items.filter((item) => {
    const haystack = [item.name, item.origin, item.category, ...(item.tools || [])]
      .join(' ')
      .toLowerCase()
    return haystack.includes(text)
  })
})

async function load() {
  try {
    data.value = await getMcp()
    error.value = ''
  } catch (err) {
    error.value = err.message
  }
}

onMounted(load)
watch(revision, load)
</script>

<style scoped>
.notice {
  border: 1px solid rgba(245, 181, 69, 0.22);
  background: rgba(245, 181, 69, 0.05);
  color: var(--muted);
  border-radius: 10px;
  padding: 11px 14px;
  font-size: 11.5px;
  line-height: 1.7;
  margin-bottom: 16px;
}

.mcp-mark {
  width: 28px;
  height: 28px;
  font-size: 11px;
}

.instances {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 11px;
}

.tool-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tool {
  background: #0d1520;
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--muted);
  padding: 3px 7px;
  font-size: 10.5px;
}
</style>
