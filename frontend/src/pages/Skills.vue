<template>
  <div>
    <div v-if="error" class="empty"><strong>读取失败</strong>{{ error }}</div>
    <div v-else-if="!data" class="loading">正在读取已安装技能…</div>

    <template v-else>
      <div class="uploader">
        <div class="uploader-head">
          <div>
            <h3>上传常用技能</h3>
            <p>
              把 SKILL.md 拖进来，解析 frontmatter 后保存在当前浏览器，不会写入本机技能目录，也不会执行其中的脚本。
            </p>
          </div>
          <div class="uploader-actions">
            <span class="chip">{{ mine.length }} 个已保存</span>
            <button class="btn" :disabled="!mine.length" @click="exportMine">导出 JSON</button>
          </div>
        </div>

        <label
          class="drop"
          :class="{ over: dragging }"
          @dragover.prevent="dragging = true"
          @dragleave.prevent="dragging = false"
          @drop.prevent="onDrop"
        >
          <input type="file" accept=".md,.markdown,.txt" multiple hidden @change="onPick" />
          <strong>拖拽 SKILL.md 到这里</strong>
          <span>或点击选择文件，支持一次多个</span>
        </label>

        <p v-if="notice" class="notice">{{ notice }}</p>

        <div v-if="pending.length" class="pending">
          <article v-for="item in pending" :key="item.id" class="pending-item">
            <div class="pending-title">
              <b>{{ item.name }}</b>
              <span class="faint">{{ (item.size / 1024).toFixed(1) }}k</span>
            </div>
            <p>{{ item.description || '没有简介' }}</p>
            <div v-if="item.tags.length" class="tags">
              <span v-for="tag in item.tags" :key="tag" class="tag">{{ tag }}</span>
            </div>
          </article>
          <div class="pending-actions">
            <button class="btn primary" @click="confirmPending">保存 {{ pending.length }} 个技能</button>
            <button class="btn" @click="clearPending">取消</button>
          </div>
        </div>

        <div v-if="mine.length" class="mine">
          <article v-for="item in mine" :key="item.id" class="mine-item">
            <div class="pending-title">
              <b>{{ item.name }}</b>
              <span class="tags">
                <span v-for="tag in item.tags" :key="tag" class="tag">{{ tag }}</span>
              </span>
            </div>
            <p>{{ item.description || '没有简介' }}</p>
            <div class="mine-foot">
              <span class="faint">{{ item.file_name }} · {{ item.added_at.slice(0, 10) }}</span>
              <button class="link" @click="removeMine(item.id)">删除</button>
            </div>
          </article>
        </div>
      </div>

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
import { downloadJson, loadUploaded, parseSkillFile, persistUploaded } from '../skillUpload'
import { revision } from '../store'

const data = ref(null)
const platform = ref('all')
const keyword = ref('')
const error = ref('')
const mine = ref(loadUploaded())
const pending = ref([])
const dragging = ref(false)
const notice = ref('')

function setNotice(message) {
  notice.value = message
  window.setTimeout(() => {
    if (notice.value === message) notice.value = ''
  }, 3200)
}

async function handleFiles(files) {
  const list = Array.from(files || []).slice(0, 8)
  if (!list.length) return
  const parsed = []
  for (const file of list) {
    try {
      parsed.push(parseSkillFile(await file.text(), file.name))
    } catch (err) {
      setNotice(`${file.name}：${err.message}`)
    }
  }
  if (parsed.length) pending.value = [...pending.value, ...parsed]
  dragging.value = false
}

function onDrop(event) {
  handleFiles(event.dataTransfer?.files)
}

function onPick(event) {
  handleFiles(event.target.files)
  event.target.value = ''
}

function clearPending() {
  pending.value = []
}

function confirmPending() {
  mine.value = [...pending.value, ...mine.value]
  persistUploaded(mine.value)
  pending.value = []
  setNotice('已保存到当前浏览器')
}

function removeMine(id) {
  mine.value = mine.value.filter((item) => item.id !== id)
  persistUploaded(mine.value)
}

function exportMine() {
  downloadJson(mine.value)
}

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

.uploader {
  margin-bottom: 20px;
  padding: 18px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--panel);
}

.uploader-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.uploader-head h3 {
  margin: 0 0 6px;
  font-size: 14px;
}

.uploader-head p {
  margin: 0;
  max-width: 520px;
  color: var(--faint);
  font-size: 11.5px;
  line-height: 1.7;
}

.uploader-actions {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 8px;
}

.drop {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  margin-top: 16px;
  padding: 24px;
  border: 1px dashed var(--border-strong);
  border-radius: 12px;
  color: var(--faint);
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s, color 0.2s;
}

.drop strong {
  color: var(--text);
  font-size: 13px;
}

.drop span {
  font-size: 11.5px;
}

.drop:hover,
.drop.over {
  border-color: var(--brand);
  background: var(--brand-dim);
  color: var(--brand);
}

.notice {
  margin: 12px 0 0;
  color: var(--brand);
  font-size: 11.5px;
}

.pending,
.mine {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 10px;
  margin-top: 14px;
}

.mine {
  margin-top: 16px;
}

.pending-item,
.mine-item {
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--panel-soft);
}

.pending-title {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  font-size: 12.5px;
}

.pending-item p,
.mine-item p {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 11.5px;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 8px;
}

.pending-actions {
  grid-column: 1 / -1;
  display: flex;
  gap: 8px;
}

.mine-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
  font-size: 10.5px;
}

.link {
  padding: 0;
  border: 0;
  background: none;
  color: var(--danger);
  font-size: 11px;
  cursor: pointer;
}

.link:hover {
  text-decoration: underline;
}
</style>
