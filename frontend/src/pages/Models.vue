<template>
  <div>
    <div v-if="error" class="empty"><strong>读取失败</strong>{{ error }}</div>
    <div v-else-if="!data" class="loading">正在读取模型用量…</div>

    <template v-else>
      <div class="section">
        <div class="section-title">
          <h2>各模型 token 用量</h2>
          <span class="hint">按总量排序</span>
        </div>
        <Chart :option="chartOption" height="300px" />
      </div>

      <div class="section">
        <div class="section-title">
          <h2>明细</h2>
          <span class="hint">待定价的模型不会按 0 元计算</span>
        </div>
        <table class="table">
          <thead>
            <tr>
              <th>平台</th>
              <th>模型</th>
              <th class="num">调用</th>
              <th class="num">Token</th>
              <th class="num">花费</th>
              <th class="num">占比</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in data.models" :key="`${row.source}-${row.model}`">
              <td>
                <span :class="['tag', row.source === 'claude' ? 'green' : 'blue']">
                  {{ row.source === 'claude' ? 'Claude' : 'Trae' }}
                </span>
              </td>
              <td class="mono">{{ row.model }}</td>
              <td class="num muted">{{ row.events }}</td>
              <td class="num">{{ tokens(row.tokens) }}</td>
              <td class="num" :class="row.unpriced ? 'faint' : 'cost'">
                {{ row.unpriced ? '待定价' : money(row.cost) }}
              </td>
              <td class="num muted">{{ percent(row.tokens, totalTokens) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="section">
        <div class="section-title">
          <h2>单价表</h2>
          <span class="hint">单位：{{ priceData?.currency || 'CNY' }} / 每百万 token</span>
        </div>

        <div class="price-note">
          <span class="tag" :class="priceData?.verified ? 'green' : 'amber'">
            {{ priceData?.verified ? '已核对' : '示例价 · 未核对' }}
          </span>
          <span>{{ priceData?.note || '单价可以直接修改，保存后立即生效。' }}</span>
        </div>

        <table class="table price-table">
          <thead>
            <tr>
              <th>模型</th>
              <th class="num">输入</th>
              <th class="num">输出</th>
              <th class="num">缓存读</th>
              <th class="num">缓存写</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="name in priceNames" :key="name">
              <td class="mono">{{ name }}</td>
              <td v-for="field in fields" :key="field" class="num">
                <input
                  v-model="editing[name][field]"
                  class="price-input"
                  type="number"
                  min="0"
                  step="0.01"
                  placeholder="未填"
                />
              </td>
              <td>
                <span v-if="rowComplete(name)" class="tag green">可计价</span>
                <span v-else class="tag amber">待定价</span>
              </td>
            </tr>
          </tbody>
        </table>

        <div class="price-actions">
          <label class="check">
            <input v-model="verified" type="checkbox" />
            这些单价已和账单核对
          </label>
          <button class="btn primary" :disabled="saving" @click="save">
            {{ saving ? '保存中…' : '保存单价' }}
          </button>
        </div>
      </div>

      <div v-if="toast" class="toast">{{ toast }}</div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import Chart from '../components/Chart.vue'
import { getModels, getPrices, savePrices } from '../api'
import { revision } from '../store'
import { money, percent, tokens } from '../utils'
import { COLORS, categoryAxis, tooltip, valueAxis } from '../charts'

const fields = ['input', 'output', 'cache_read', 'cache_write']
const data = ref(null)
const priceData = ref(null)
const editing = reactive({})
const verified = ref(false)
const saving = ref(false)
const error = ref('')
const toast = ref('')

const totalTokens = computed(() =>
  (data.value?.models || []).reduce((sum, row) => sum + row.tokens, 0)
)

const priceNames = computed(() => Object.keys(editing))

const chartRows = computed(() => {
  const rows = [...(data.value?.models || [])].slice(0, 12)
  return rows.reverse()
})

const chartOption = computed(() => ({
  tooltip: {
    ...tooltip,
    trigger: 'item',
    formatter: (item) => {
      const row = chartRows.value.find((entry) => entry.model === item.name)
      if (!row) return item.name
      return `${row.model}<br/>${tokens(row.tokens)} token<br/>${row.unpriced ? '待定价' : money(row.cost)}`
    }
  },
  grid: { left: 170, right: 60, top: 12, bottom: 24 },
  xAxis: valueAxis({
    axisLabel: {
      color: COLORS.text,
      fontSize: 10,
      formatter: (value) => `${(value / 1_000_000).toFixed(0)}M`
    }
  }),
  yAxis: categoryAxis(chartRows.value.map((row) => row.model), {
    axisLabel: { color: COLORS.text, fontSize: 11, width: 150, overflow: 'truncate' }
  }),
  series: [
    {
      type: 'bar',
      barMaxWidth: 16,
      data: chartRows.value.map((row) => ({
        value: row.tokens,
        itemStyle: {
          color: row.source === 'claude' ? COLORS.claude : COLORS.trae,
          borderRadius: [0, 5, 5, 0]
        }
      })),
      label: {
        show: true,
        position: 'right',
        color: COLORS.text,
        fontSize: 10,
        formatter: (item) => tokens(item.value)
      }
    }
  ]
}))

function emptyRates() {
  return { input: '', output: '', cache_read: '', cache_write: '' }
}

function fillEditing(prices) {
  for (const key of Object.keys(editing)) delete editing[key]
  for (const [name, rates] of Object.entries(prices.models || {})) {
    editing[name] = emptyRates()
    if (rates) {
      for (const field of fields) {
        editing[name][field] = rates[field] === null ? '' : String(rates[field])
      }
    }
  }
}

function rowComplete(name) {
  return fields.every((field) => {
    const value = editing[name][field]
    return value !== '' && Number(value) >= 0
  })
}

function ratesPayload() {
  const models = {}
  for (const [name, rates] of Object.entries(editing)) {
    if (rates === null) continue
    const empty = fields.every((field) => rates[field] === '' || rates[field] === null)
    if (empty) {
      models[name] = null
      continue
    }
    models[name] = {}
    for (const field of fields) {
      models[name][field] = rates[field] === '' ? null : Number(rates[field])
    }
  }
  return models
}

async function save() {
  saving.value = true
  try {
    const result = await savePrices({ models: ratesPayload(), verified: verified.value })
    priceData.value = result
    toast.value = '单价已保存'
    window.setTimeout(() => (toast.value = ''), 2400)
    await loadModels()
  } catch (err) {
    toast.value = `保存失败：${err.message}`
    window.setTimeout(() => (toast.value = ''), 3200)
  } finally {
    saving.value = false
  }
}

async function loadModels() {
  const result = await getModels()
  data.value = result
}

async function load() {
  try {
    const [models, prices] = await Promise.all([getModels(), getPrices()])
    data.value = models
    priceData.value = prices
    verified.value = prices.verified
    fillEditing(prices)
    error.value = ''
  } catch (err) {
    error.value = err.message
  }
}

watch(revision, load)
onMounted(load)
</script>

<style scoped>
.cost {
  color: var(--cost);
}

.price-note {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 11px 13px;
  border: 1px solid var(--border);
  background: var(--panel-soft);
  border-radius: 10px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.6;
  margin-bottom: 14px;
}

.price-table td {
  padding: 8px 10px;
}

.price-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-top: 16px;
}

.check {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--muted);
  font-size: 12px;
  cursor: pointer;
}

.check input {
  accent-color: var(--brand);
}
</style>
