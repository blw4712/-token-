<template>
  <div>
    <div v-if="error" class="empty"><strong>读取失败</strong>{{ error }}</div>
    <div v-else-if="!overview" class="loading">正在读取本地日志…</div>

    <template v-else>
      <div class="cards">
        <div class="card">
          <div class="metric-label">
            累计花费
            <span class="tag" :class="overview.prices.verified ? 'green' : 'amber'">
              {{ overview.prices.verified ? '已核对' : '示例价' }}
            </span>
          </div>
          <div class="metric-value">{{ money(overview.totals.cost) }}</div>
          <div class="metric-foot">
            累计 {{ tokens(overview.totals.tokens) }} token ·
            {{ overview.totals.unpriced_tokens ? `${tokens(overview.totals.unpriced_tokens)} 待定价` : '全部已计价' }}
          </div>
        </div>

        <div class="card">
          <div class="metric-label">今日花费</div>
          <div class="metric-value">{{ money(overview.today.cost) }}</div>
          <div class="metric-foot">今天用了 {{ tokens(overview.today.tokens) }} token</div>
        </div>

        <div class="card">
          <div class="metric-label">累计 Token</div>
          <div class="metric-value">{{ tokens(overview.totals.tokens) }}</div>
          <div class="metric-foot">
            {{ overview.totals.events }} 条回复 · {{ overview.totals.sessions }} 个会话
          </div>
        </div>

        <div class="card">
          <div class="metric-label">活跃模型</div>
          <div class="metric-value">{{ overview.active_models.length }}<small>个</small></div>
          <div class="metric-foot">最近 7 天调用过的模型</div>
        </div>
      </div>

      <div class="grid-2">
        <div class="section">
          <div class="section-title">
            <h2>最近 30 天</h2>
            <span class="hint">堆叠为 token，折线为花费</span>
          </div>
          <Chart :option="dailyOption" height="268px" />
        </div>

        <div class="section">
          <div class="section-title">
            <h2>平台占比</h2>
            <span class="hint">按 token</span>
          </div>
          <Chart :option="sourceOption" height="268px" />
        </div>
      </div>

      <div class="section">
        <div class="section-title">
          <h2>花费最高的模型</h2>
          <RouterLink to="/models" class="hint">查看全部 →</RouterLink>
        </div>

        <div v-if="!overview.top_models.length" class="empty">
          <strong>还没有调用记录</strong>点右上角重新扫描，或先在本机使用一次 Claude / Trae。
        </div>
        <div v-else>
          <div v-for="item in overview.top_models" :key="`${item.source}-${item.model}`" class="model-row">
            <div class="model-main">
              <div class="model-title">
                <span :class="['tag', item.source === 'claude' ? 'green' : 'blue']">
                  {{ item.source === 'claude' ? 'Claude' : 'Trae' }}
                </span>
                <span class="mono">{{ item.model }}</span>
              </div>
              <div class="bar-line">
                <i :style="{ width: percent(item.tokens, topMax), background: item.source === 'claude' ? COLORS.claude : COLORS.trae }" />
              </div>
            </div>
            <div class="model-tokens">{{ tokens(item.tokens) }}</div>
            <div class="model-cost">{{ money(item.cost) }}</div>
          </div>
        </div>
      </div>

      <div class="asset-strip">
        <RouterLink to="/skills" class="asset">
          <div class="asset-label">Skills</div>
          <div class="asset-value">{{ overview.counts.skills }}</div>
          <div class="asset-foot">{{ overview.counts.enabled_skills }} 个已启用</div>
        </RouterLink>
        <RouterLink to="/mcp" class="asset">
          <div class="asset-label">MCP</div>
          <div class="asset-value">{{ overview.counts.mcps }}</div>
          <div class="asset-foot">本地缓存的服务</div>
        </RouterLink>
        <RouterLink to="/agents" class="asset">
          <div class="asset-label">Agents</div>
          <div class="asset-value">{{ overview.counts.agents }}</div>
          <div class="asset-foot">可发现的子代理</div>
        </RouterLink>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import Chart from '../components/Chart.vue'
import { getDaily, getOverview } from '../api'
import { revision } from '../store'
import { money, percent, shortDate, tokens } from '../utils'
import { COLORS, categoryAxis, legend, tooltip, valueAxis } from '../charts'

const overview = ref(null)
const days = ref([])
const error = ref('')

const topMax = computed(() =>
  Math.max(1, ...(overview.value?.top_models || []).map((item) => item.tokens))
)

const dailyOption = computed(() => {
  const labels = days.value.map((item) => shortDate(item.date))
  const full = new Map(days.value.map((item) => [shortDate(item.date), item]))
  return {
    tooltip: {
      ...tooltip,
      formatter(params) {
        const item = full.get(params[0].axisValue)
        if (!item) return ''
        const costItem = params.find((entry) => entry.seriesName === '花费')
        return [
          `<b>${item.date}</b>`,
          `Claude ${tokens(item.claude_tokens)} token`,
          `Trae ${tokens(item.trae_tokens)} token`,
          `合计 ${tokens(item.tokens)} token`,
          `花费 ${costItem ? money(costItem.value) : '—'}`
        ].join('<br/>')
      }
    },
    legend: { ...legend, data: ['Claude', 'Trae', '花费'] },
    grid: { left: 46, right: 48, top: 30, bottom: 24 },
    xAxis: categoryAxis(labels, { axisLabel: { color: COLORS.text, fontSize: 10, interval: 4, rotate: 0 } }),
    yAxis: [
      valueAxis({
        axisLabel: {
          color: COLORS.text,
          fontSize: 10,
          formatter: (value) => `${(value / 1_000_000).toFixed(0)}M`
        }
      }),
      valueAxis({
        position: 'right',
        splitLine: { show: false },
        axisLabel: { color: COLORS.text, fontSize: 10, formatter: (value) => `¥${value}` }
      })
    ],
    series: [
      {
        name: 'Claude',
        type: 'bar',
        stack: 'tokens',
        barMaxWidth: 13,
        itemStyle: { color: COLORS.claude },
        data: days.value.map((item) => item.claude_tokens)
      },
      {
        name: 'Trae',
        type: 'bar',
        stack: 'tokens',
        barMaxWidth: 13,
        itemStyle: { color: COLORS.trae },
        data: days.value.map((item) => item.trae_tokens)
      },
      {
        name: '花费',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        symbol: 'none',
        lineStyle: { color: COLORS.cost, width: 2 },
        data: days.value.map((item) => Number(item.cost.toFixed(2)))
      }
    ]
  }
})

const sourceOption = computed(() => {
  const sources = overview.value?.by_source || []
  const total = overview.value?.totals.tokens || 0
  return {
    tooltip: {
      trigger: 'item',
      backgroundColor: tooltip.backgroundColor,
      borderColor: tooltip.borderColor,
      textStyle: tooltip.textStyle,
      formatter: (item) => `${item.name}<br/>${tokens(item.value)} token（${item.percent}%）`
    },
    title: {
      text: tokens(total),
      subtext: '累计 token',
      left: 'center',
      top: '36%',
      textStyle: { color: '#e8eef6', fontSize: 19, fontWeight: 600 },
      subtextStyle: { color: COLORS.text, fontSize: 10 }
    },
    legend: { ...legend, top: 'auto', bottom: 0, left: 'center' },
    series: [
      {
        type: 'pie',
        radius: ['60%', '78%'],
        center: ['50%', '46%'],
        avoidLabelOverlap: true,
        label: { show: false },
        itemStyle: { borderColor: '#0f1620', borderWidth: 2 },
        data: sources.map((item) => ({
          name: item.source === 'claude' ? 'Claude' : 'Trae',
          value: item.tokens,
          itemStyle: { color: item.source === 'claude' ? COLORS.claude : COLORS.trae }
        }))
      }
    ]
  }
})

async function load() {
  try {
    const [data, trend] = await Promise.all([getOverview(), getDaily(30)])
    overview.value = data
    days.value = trend.days
    error.value = ''
  } catch (err) {
    error.value = err.message
  }
}

onMounted(load)
watch(revision, load)
</script>

<style scoped>
.model-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 70px 90px;
  gap: 14px;
  align-items: center;
  padding: 9px 0;
}

.model-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.model-title {
  display: flex;
  align-items: center;
  gap: 8px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.model-tokens,
.model-cost {
  text-align: right;
  font-variant-numeric: tabular-nums;
  font-size: 12px;
}

.model-cost {
  color: var(--cost);
}

.asset-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.asset {
  display: block;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 15px 18px;
  transition: border-color 0.15s;
}

.asset:hover {
  border-color: var(--border-strong);
}

.asset-label {
  color: var(--muted);
  font-size: 12px;
}

.asset-value {
  font-size: 22px;
  font-weight: 650;
  margin: 7px 0 5px;
}

.asset-foot {
  color: var(--faint);
  font-size: 11px;
}
</style>
