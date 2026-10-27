<template>
  <div>
    <div v-if="error" class="empty"><strong>读取失败</strong>{{ error }}</div>
    <div v-else-if="!data" class="loading">正在读取已安装技能…</div>

    <template v-else>
      <div class="search-row">
        <div class="tabs">
          <button :class="{ active: platform === 'all' }" @click="platform = 'all'">
            全部 {{ data.total }}
          </button>
          <button :class="{ active: platform === 'claude' }" @click="platform = 'claude'">
            Claude {{ countOf('claude') }}
          </button>
          <button :class="{ active: platform === 'trae' }" @click="platform = 'trae'">
            Trae {{ countOf('trae') }}
          </button>
        </div>
        <input v-model="keyword" class="input" placeholder="搜索名称、简介或来源…" />
        <span class="chip">{{ filtered.length }} 个结果</span>
      </div>

      <div v-if="!filtered.length" class="empty">
        <strong>没有匹配的技能</strong>换个关键词，或切换平台再试。
      </div>

      <div v-else class="section">
        <table class="table">
          <thead>
            <tr>
              <th>技能</th>
              <th>简介</th>
              <th>平台</th>
              <th>作用域</th>
              <th>来源 / 路径</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in filtered" :key="item.path">
              <td class="name-cell">
                <div class="mono name">{{ item.name }}</div>
                <div class="faint path" :title="item.path">{{ item.path }}</div>
              </td>
              <td class="desc">{{ item.description || '—' }}</td>
              <td>
                <span :class="['tag', item.platform === 'claude' ? 'green' : 'blue']">
                  {{ item.platform === 'claude' ? 'Claude' : 'Trae' }}
                </span>
              </td>
              <td><span class="tag">{{ item.scope_label }}</span></td>
              <td class="origin">{{ item.origin || '—' }}</td>
              <td>
                <span :class="['tag', item.enabled ? 'green' : 'red']">
                  {{ item.enabled ? '启用' : '停用' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="section footnote">
        技能目录只读扫描，不执行脚本，也不读取密钥。Claude 用户级目录、Claude 项目目录、
        Trae 内置技能和插件技能都会计入。
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { getSkills } from '../api'
import { revision } from '../store'

const data = ref(null)
const platform = ref('all')
const keyword = ref('')
const error = ref('')

function countOf(name) {
  return (data.value?.skills || []).filter((item) => item.platform === name).length
}

const filtered = computed(() => {
  const items = data.value?.skills || []
  const text = keyword.value.trim().toLowerCase()
  return items.filter((item) => {
    if (platform.value !== 'all' && item.platform !== platform.value) return false
    if (!text) return true
    return [item.name, item.description, item.origin, item.path]
      .join(' ')
      .toLowerCase()
      .includes(text)
  })
})

async function load() {
  try {
    data.value = await getSkills()
    error.value = ''
  } catch (err) {
    error.value = err.message
  }
}

onMounted(load)
watch(revision, load)
</script>

<style scoped>
.name-cell {
  max-width: 230px;
}

.name {
  color: var(--text);
  font-size: 12.5px;
}

.path {
  font-size: 10.5px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 230px;
}

.desc {
  max-width: 420px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.55;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.origin {
  color: var(--faint);
  font-size: 11px;
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.footnote {
  color: var(--faint);
  font-size: 11.5px;
  line-height: 1.7;
}
</style>
