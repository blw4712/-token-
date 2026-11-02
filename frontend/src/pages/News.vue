<template>
  <div>
    <div v-if="error" class="empty"><strong>读取失败</strong>{{ error }}</div>
    <div v-else-if="!data" class="loading">正在读取 AI 动态…</div>

    <template v-else>
      <div class="search-row">
        <div class="tabs">
          <button :class="{ active: source === 'all' }" @click="source = 'all'">
            全部 {{ data.items.length }}
          </button>
          <button
            v-for="name in sources"
            :key="name"
            :class="{ active: source === name }"
            @click="source = name"
          >
            {{ name }} {{ countOf(name) }}
          </button>
        </div>
        <input v-model="keyword" class="input" placeholder="搜索标题、摘要或标签…" />
        <span class="chip">{{ filtered.length }} 条</span>
      </div>

      <div v-if="!filtered.length" class="empty">
        <strong>没有匹配的内容</strong>换个关键词，或切换来源再试。
      </div>

      <div v-else class="news-list">
        <a
          v-for="item in filtered"
          :key="item.link"
          class="news-item"
          :href="item.link"
          target="_blank"
          rel="noreferrer"
        >
          <div class="news-meta">
            <span class="tag blue">{{ item.source }}</span>
            <span class="faint">{{ dateText(item.published) }}</span>
          </div>
          <h3>{{ item.title }}</h3>
          <p v-if="item.summary">{{ item.summary }}</p>
          <div class="news-foot">
            <span class="tags">
              <span v-for="tag in item.tags" :key="tag" class="tag">{{ tag }}</span>
            </span>
            <span class="open">阅读原文 ↗</span>
          </div>
        </a>
      </div>

      <div class="section footnote">
        内容来自公开 RSS 源（OpenAI、Hugging Face、Simon Willison、Google AI 等），由 GitHub Actions
        每天定时抓取并写入站点。只聚合标题与摘要，不转载全文。
        <template v-if="generatedAt"> 本次生成：{{ generatedAt }}。</template>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { getNews } from '../api'

const data = ref(null)
const source = ref('all')
const keyword = ref('')
const error = ref('')

const sources = computed(() => {
  const counts = new Map()
  for (const item of data.value?.items || []) {
    counts.set(item.source, (counts.get(item.source) || 0) + 1)
  }
  return [...counts.entries()].sort((a, b) => b[1] - a[1]).map(([name]) => name)
})

const generatedAt = computed(() => {
  const value = data.value?.generated_at
  if (!value) return ''
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
})

function countOf(name) {
  return (data.value?.items || []).filter((item) => item.source === name).length
}

function dateText(value) {
  if (!value) return ''
  return new Date(value).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })
}

const filtered = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  return (data.value?.items || []).filter((item) => {
    if (source.value !== 'all' && item.source !== source.value) return false
    if (!text) return true
    return [item.title, item.summary, item.source, (item.tags || []).join(' ')]
      .join(' ')
      .toLowerCase()
      .includes(text)
  })
})

onMounted(async () => {
  try {
    data.value = await getNews()
  } catch (err) {
    error.value = err.message
  }
})
</script>

<style scoped>
.news-list {
  display: grid;
  gap: 10px;
}

.news-item {
  display: block;
  padding: 16px 18px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--panel);
  transition: border-color 0.2s, background 0.2s, transform 0.2s;
}

.news-item:hover {
  border-color: var(--border-strong);
  background: var(--panel-soft);
  transform: translateX(3px);
}

.news-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 11px;
}

.news-item h3 {
  margin: 8px 0 6px;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.5;
}

.news-item p {
  margin: 0;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.7;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.news-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 10px;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.open {
  flex-shrink: 0;
  color: var(--faint);
  font-size: 11px;
  transition: color 0.2s;
}

.news-item:hover .open {
  color: var(--brand);
}

.footnote {
  color: var(--faint);
  font-size: 11.5px;
  line-height: 1.7;
}
</style>
