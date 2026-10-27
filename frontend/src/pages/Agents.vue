<template>
  <div>
    <div v-if="error" class="empty"><strong>读取失败</strong>{{ error }}</div>
    <div v-else-if="!data" class="loading">正在查找子代理…</div>

    <template v-else>
      <div v-if="!data.agents.length" class="section">
        <div class="empty">
          <strong>本机还没有自定义子代理</strong>
          子代理是可被主 Agent 调用的独立角色。安装后会在这里显示名称、简介和可用工具。
        </div>

        <div class="checked">
          <div class="checked-title">已经检查过的位置</div>
          <div v-for="place in places" :key="place.path" class="place">
            <span class="mono">{{ place.path }}</span>
            <span class="tag">{{ place.status }}</span>
          </div>
        </div>
      </div>

      <div v-else class="section">
        <div v-for="agent in data.agents" :key="agent.path" class="agent-row">
          <div class="avatar">{{ initial(agent.name) }}</div>
          <div class="agent-main">
            <div class="agent-title">
              <span class="mono">{{ agent.name }}</span>
              <span :class="['tag', agent.platform === 'claude' ? 'green' : 'blue']">
                {{ agent.platform === 'claude' ? 'Claude' : 'Trae' }}
              </span>
              <span v-if="agent.model" class="tag">{{ agent.model }}</span>
              <span v-if="agent.scope" class="tag">{{ agent.scope }}</span>
            </div>
            <div class="agent-desc">{{ agent.description || '没有简介' }}</div>
            <div v-if="agent.tools.length" class="tool-list">
              <div class="tool-grid">
                <span v-for="tool in agent.tools" :key="tool" class="tool mono">{{ tool }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { getAgents } from '../api'
import { revision } from '../store'

const data = ref(null)
const error = ref('')

const places = [
  { path: '~/.claude/agents', status: '未发现' },
  { path: '~/.trae-cn/assistant', status: '未发现' },
  { path: '~/.trae-cn/plugins/*/agents', status: '未发现' }
]

function initial(name) {
  return String(name || '?').slice(0, 1).toUpperCase()
}

async function load() {
  try {
    data.value = await getAgents()
    error.value = ''
  } catch (err) {
    error.value = err.message
  }
}

onMounted(load)
watch(revision, load)
</script>

<style scoped>
.checked {
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px solid var(--border);
}

.checked-title {
  color: var(--faint);
  font-size: 11px;
  margin-bottom: 9px;
}

.place {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 6px 0;
  color: var(--muted);
  font-size: 11.5px;
}

.agent-main {
  min-width: 0;
  flex: 1;
}

.agent-title {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.agent-desc {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.6;
  margin-top: 6px;
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
