<template>
  <div ref="root" class="home">
    <canvas ref="canvas" class="field" />
    <div class="aurora">
      <span class="blob a" />
      <span class="blob b" />
      <span class="blob c" />
    </div>
    <div class="mesh" />
    <div class="cursor-glow" />

    <header class="home-top">
      <RouterLink to="/" class="mark">
        <span class="mark-box">A</span>
        <span class="mark-text">
          <b>Agent Console</b>
          <i>本地用量与资产</i>
        </span>
      </RouterLink>
      <nav class="home-links">
        <RouterLink to="/overview">总览</RouterLink>
        <RouterLink to="/skills">Skills</RouterLink>
        <RouterLink to="/mcp">MCP</RouterLink>
        <a href="https://github.com/blw4712/-token-" target="_blank" rel="noreferrer">GitHub ↗</a>
      </nav>
    </header>

    <section class="hero">
      <p class="eyebrow">
        <span class="pulse" />
        {{ typed }}<span class="caret" />
      </p>
      <h1>
        把每一次调用<br />
        <span class="shine">看得明明白白</span>
      </h1>
      <p class="lede">
        Claude Code 与 Trae Code 的 token 消耗、模型花费、Skills、MCP，
        汇总到一个只读面板里。数据不出本机，也不改任何配置。
      </p>

      <div class="cta">
        <RouterLink to="/overview" class="btn-cta primary">
          进入总览
          <span>→</span>
        </RouterLink>
        <RouterLink to="/skills" class="btn-cta">浏览技能库</RouterLink>
      </div>

      <div class="stats">
        <div class="stat">
          <span class="stat-label">累计花费</span>
          <b>{{ money(shown.cost) }}</b>
          <i>示例价估算</i>
        </div>
        <div class="stat">
          <span class="stat-label">累计 Token</span>
          <b>{{ tokens(Math.round(shown.tokens)) }}</b>
          <i>{{ counts.events }} 条回复 · {{ counts.sessions }} 个会话</i>
        </div>
        <div class="stat">
          <span class="stat-label">Skills</span>
          <b>{{ counts.skills }}</b>
          <i>{{ counts.enabled_skills }} 个已启用</i>
        </div>
        <div class="stat">
          <span class="stat-label">MCP</span>
          <b>{{ counts.mcps }}</b>
          <i>本地缓存的服务</i>
        </div>
      </div>
    </section>

    <section class="entries">
      <RouterLink
        v-for="entry in entries"
        :key="entry.to"
        :to="entry.to"
        class="entry"
        :class="entry.accent"
        @pointermove="tilt"
        @pointerleave="resetTilt"
        @pointerdown="ripple"
      >
        <span class="entry-icon" v-html="entry.icon" />
        <h3>{{ entry.title }}</h3>
        <p>{{ entry.desc }}</p>
        <footer>
          <b>{{ entry.stat }}</b>
          <span class="arrow">→</span>
        </footer>
      </RouterLink>
    </section>

    <footer class="home-foot">
      <span v-if="snapshotAt">本地快照 · {{ snapshotAt.slice(0, 10) }}</span>
      <span v-else>本机实时数据</span>
      <span>单价为示例参考价，未与账单核对</span>
      <a href="https://github.com/blw4712/-token-" target="_blank" rel="noreferrer">源码</a>
    </footer>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { getModels, getOverview, getSnapshotInfo } from '../api'
import { money, tokens } from '../utils'

const root = ref(null)
const canvas = ref(null)
const typed = ref('')
const snapshotAt = ref('')

const shown = reactive({ cost: 0, tokens: 0 })
const counts = reactive({ skills: 0, enabled_skills: 0, mcps: 0, events: 0, sessions: 0 })

const icons = {
  chart: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"><path d="M4 19V9M10 19V5M16 19v-7M22 19H2"/></svg>`,
  layers: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l9 5-9 5-9-5 9-5Z"/><path d="M3 13l9 5 9-5"/></svg>`,
  spark: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l2.2 5.6L20 11l-5.8 2.4L12 19l-2.2-5.6L4 11l5.8-2.4L12 3Z"/></svg>`,
  plug: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M9 3v6M15 3v6"/><path d="M6 9h12v3a6 6 0 0 1-12 0V9Z"/><path d="M12 18v3"/></svg>`,
  bot: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="7" width="16" height="12" rx="3"/><path d="M12 3v4M9 12h.01M15 12h.01M9.5 16h5"/></svg>`
}

const entries = reactive([
  { to: '/overview', title: '总览', desc: '今日花费、最近 30 天趋势与平台占比', stat: '看趋势', accent: 'emerald', icon: icons.chart },
  { to: '/models', title: '模型开销', desc: '按模型拆 token 与费用，四档单价可核对', stat: '看账本', accent: 'blue', icon: icons.layers },
  { to: '/skills', title: 'Skills', desc: 'Claude 与 Trae 的技能库，来源与启用状态', stat: '待填', accent: 'amber', icon: icons.spark },
  { to: '/mcp', title: 'MCP', desc: '本地缓存的服务与工具清单，已脱敏', stat: '待填', accent: 'violet', icon: icons.plug },
  { to: '/agents', title: 'Agents', desc: '可发现的子代理及其来源目录', stat: '待填', accent: 'cyan', icon: icons.bot }
])

function animate(target, key, duration = 1100) {
  const start = performance.now()
  const from = shown[key] || 0
  function frame(now) {
    const t = Math.min(1, (now - start) / duration)
    const eased = 1 - Math.pow(1 - t, 3)
    shown[key] = from + (target - from) * eased
    if (t < 1) requestAnimationFrame(frame)
  }
  requestAnimationFrame(frame)
}

async function load() {
  try {
    const [overview, models] = await Promise.all([getOverview(), getModels()])
    animate(overview.totals.cost || 0, 'cost')
    animate(overview.totals.tokens || 0, 'tokens')
    Object.assign(counts, {
      skills: overview.counts.skills,
      enabled_skills: overview.counts.enabled_skills,
      mcps: overview.counts.mcps,
      events: overview.totals.events,
      sessions: overview.totals.sessions
    })
    entries[1].stat = `${models.models.length} 个模型`
    entries[2].stat = `${overview.counts.skills} 个已安装`
    entries[3].stat = `${overview.counts.mcps} 个服务`
    entries[4].stat = `${overview.counts.agents} 个可发现`
  } catch {
    entries[2].stat = '打开看看'
    entries[3].stat = '打开看看'
    entries[4].stat = '打开看看'
  }

  try {
    const info = await getSnapshotInfo()
    snapshotAt.value = info?.generated_at || ''
  } catch {
    snapshotAt.value = ''
  }
}

/* ---------- 打字机 ---------- */
const phrases = ['每一次 token 消耗', '每个模型的真实花费', '本机装好的 Skills', '缓存过的 MCP 服务']
let phraseIndex = 0
let charIndex = 0
let deleting = false
let typeTimer = 0

function typeLoop() {
  const phrase = phrases[phraseIndex]
  charIndex += deleting ? -1 : 1
  typed.value = phrase.slice(0, charIndex)
  let delay = deleting ? 40 : 90
  if (!deleting && charIndex === phrase.length) {
    deleting = true
    delay = 1500
  } else if (deleting && charIndex === 0) {
    deleting = false
    phraseIndex = (phraseIndex + 1) % phrases.length
    delay = 260
  }
  typeTimer = window.setTimeout(typeLoop, delay)
}

/* ---------- 鼠标光晕 ---------- */
let frame = 0
let pointer = { x: -9999, y: -9999 }

function onPointerMove(event) {
  if (frame) return
  frame = requestAnimationFrame(() => {
    frame = 0
    if (!root.value) return
    const rect = root.value.getBoundingClientRect()
    pointer = { x: event.clientX - rect.left, y: event.clientY - rect.top }
    root.value.style.setProperty('--mx', `${pointer.x}px`)
    root.value.style.setProperty('--my', `${pointer.y}px`)
  })
}

function tilt(event) {
  const el = event.currentTarget
  const rect = el.getBoundingClientRect()
  const px = (event.clientX - rect.left) / rect.width
  const py = (event.clientY - rect.top) / rect.height
  el.style.setProperty('--cx', `${px * 100}%`)
  el.style.setProperty('--cy', `${py * 100}%`)
  el.style.transform = `perspective(900px) rotateX(${(0.5 - py) * 7}deg) rotateY(${(px - 0.5) * 9}deg) translateY(-6px)`
}

function resetTilt(event) {
  event.currentTarget.style.transform = ''
}

function ripple(event) {
  const host = event.currentTarget
  const rect = host.getBoundingClientRect()
  const size = Math.max(rect.width, rect.height) * 1.8
  const dot = document.createElement('span')
  dot.className = 'ripple'
  dot.style.width = `${size}px`
  dot.style.height = `${size}px`
  dot.style.left = `${event.clientX - rect.left - size / 2}px`
  dot.style.top = `${event.clientY - rect.top - size / 2}px`
  host.appendChild(dot)
  window.setTimeout(() => dot.remove(), 650)
}

/* ---------- 粒子背景 ---------- */
let raf = 0
let nodes = []
let size = { w: 0, h: 0 }
let ctx = null
let dpr = 1
const motionOK = !window.matchMedia('(prefers-reduced-motion: reduce)').matches

function resizeCanvas() {
  if (!canvas.value) return
  const rect = canvas.value.getBoundingClientRect()
  dpr = Math.min(window.devicePixelRatio || 1, 2)
  size = { w: rect.width, h: rect.height }
  canvas.value.width = Math.floor(rect.width * dpr)
  canvas.value.height = Math.floor(rect.height * dpr)
  ctx = canvas.value.getContext('2d')
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  const total = Math.min(84, Math.max(28, Math.floor((rect.width * rect.height) / 16000)))
  nodes = Array.from({ length: total }, () => ({
    x: Math.random() * rect.width,
    y: Math.random() * rect.height,
    vx: (Math.random() - 0.5) * 0.35,
    vy: (Math.random() - 0.5) * 0.35,
    r: Math.random() * 1.6 + 0.6
  }))
}

function tick() {
  if (!ctx) return
  ctx.clearRect(0, 0, size.w, size.h)
  for (const node of nodes) {
    node.x += node.vx
    node.y += node.vy
    if (node.x < 0 || node.x > size.w) node.vx *= -1
    if (node.y < 0 || node.y > size.h) node.vy *= -1

    const dx = node.x - pointer.x
    const dy = node.y - pointer.y
    const dist = Math.hypot(dx, dy)
    if (dist < 150 && dist > 0.1) {
      node.x += (dx / dist) * 0.5
      node.y += (dy / dist) * 0.5
    }

    ctx.beginPath()
    ctx.arc(node.x, node.y, node.r, 0, Math.PI * 2)
    ctx.fillStyle = 'rgba(120, 220, 180, 0.55)'
    ctx.fill()
  }

  for (let i = 0; i < nodes.length; i += 1) {
    for (let j = i + 1; j < nodes.length; j += 1) {
      const a = nodes[i]
      const b = nodes[j]
      const d = Math.hypot(a.x - b.x, a.y - b.y)
      if (d < 130) {
        ctx.beginPath()
        ctx.moveTo(a.x, a.y)
        ctx.lineTo(b.x, b.y)
        ctx.strokeStyle = `rgba(52, 211, 153, ${0.16 * (1 - d / 130)})`
        ctx.lineWidth = 0.7
        ctx.stroke()
      }
    }
  }
  raf = requestAnimationFrame(tick)
}

function startCanvas() {
  if (!motionOK) return
  resizeCanvas()
  cancelAnimationFrame(raf)
  raf = requestAnimationFrame(tick)
}

function onResize() {
  resizeCanvas()
}

function onVisibility() {
  if (!motionOK) return
  if (document.hidden) {
    cancelAnimationFrame(raf)
  } else {
    cancelAnimationFrame(raf)
    raf = requestAnimationFrame(tick)
  }
}

onMounted(() => {
  load()
  if (motionOK) typeLoop()
  else typed.value = phrases[0]
  root.value?.addEventListener('pointermove', onPointerMove)
  window.addEventListener('resize', onResize)
  document.addEventListener('visibilitychange', onVisibility)
  startCanvas()
})

onUnmounted(() => {
  clearTimeout(typeTimer)
  cancelAnimationFrame(raf)
  window.clearTimeout(frame)
  root.value?.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('resize', onResize)
  document.removeEventListener('visibilitychange', onVisibility)
})
</script>

<style scoped>
.home {
  position: relative;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0 clamp(20px, 5vw, 72px) 40px;
  --mx: 50%;
  --my: 30%;
  background:
    radial-gradient(1200px 700px at 15% -10%, rgba(52, 211, 153, 0.16), transparent 60%),
    radial-gradient(900px 600px at 88% 8%, rgba(91, 157, 255, 0.14), transparent 62%),
    #070b10;
  isolation: isolate;
}

.field {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0.75;
  pointer-events: none;
  z-index: 0;
}

.aurora {
  position: absolute;
  inset: -20% -10% auto;
  height: 90%;
  pointer-events: none;
  filter: blur(90px);
  opacity: 0.55;
  z-index: 0;
}

.blob {
  position: absolute;
  border-radius: 50%;
  animation: float 16s ease-in-out infinite;
}

.blob.a {
  width: 460px;
  height: 360px;
  left: 6%;
  top: 5%;
  background: rgba(52, 211, 153, 0.5);
}

.blob.b {
  width: 520px;
  height: 400px;
  right: 8%;
  top: 0;
  background: rgba(91, 157, 255, 0.4);
  animation-delay: -5s;
}

.blob.c {
  width: 380px;
  height: 320px;
  left: 42%;
  top: 18%;
  background: rgba(245, 181, 69, 0.28);
  animation-delay: -9s;
}

@keyframes float {
  0%, 100% { transform: translate3d(0, 0, 0) scale(1); }
  50% { transform: translate3d(30px, -24px, 0) scale(1.12); }
}

.mesh {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.045) 1px, transparent 1px);
  background-size: 52px 52px;
  mask-image: radial-gradient(circle at 50% 30%, #000 20%, transparent 72%);
  -webkit-mask-image: radial-gradient(circle at 50% 30%, #000 20%, transparent 72%);
  z-index: 0;
}

.cursor-glow {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: radial-gradient(
    380px circle at var(--mx) var(--my),
    rgba(52, 211, 153, 0.12),
    rgba(91, 157, 255, 0.06) 45%,
    transparent 70%
  );
  z-index: 0;
}

.home-top {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 26px 0 0;
}

.mark {
  display: flex;
  align-items: center;
  gap: 10px;
}

.mark-box {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  font-weight: 800;
  color: #04120c;
  background: linear-gradient(140deg, #8ef0c6, #34d399);
  box-shadow: 0 0 30px rgba(52, 211, 153, 0.45);
}

.mark-text b {
  display: block;
  font-size: 14px;
  letter-spacing: 0.3px;
}

.mark-text i {
  font-style: normal;
  font-size: 11px;
  color: var(--faint);
}

.home-links {
  display: flex;
  gap: 22px;
  font-size: 12.5px;
  color: var(--muted);
}

.home-links a {
  transition: color 0.2s;
}

.home-links a:hover {
  color: var(--brand);
}

.hero {
  position: relative;
  z-index: 2;
  max-width: 900px;
  padding: clamp(60px, 12vh, 130px) 0 20px;
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  margin: 0 0 22px;
  padding: 7px 14px;
  border-radius: 999px;
  border: 1px solid rgba(52, 211, 153, 0.28);
  background: rgba(52, 211, 153, 0.07);
  color: #a8e6c9;
  font-size: 12.5px;
  letter-spacing: 0.2px;
}

.pulse {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--brand);
  box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.7);
  animation: pulse 2.2s infinite;
}

@keyframes pulse {
  70% { box-shadow: 0 0 0 9px rgba(52, 211, 153, 0); }
  100% { box-shadow: 0 0 0 0 rgba(52, 211, 153, 0); }
}

.caret {
  width: 2px;
  height: 13px;
  background: var(--brand);
  animation: blink 1s steps(1) infinite;
}

@keyframes blink {
  50% { opacity: 0; }
}

h1 {
  margin: 0;
  font-size: clamp(38px, 6.2vw, 76px);
  line-height: 1.12;
  letter-spacing: -1.5px;
  font-weight: 750;
}

.shine {
  background: linear-gradient(100deg, #eafff2 0%, #7ef0c0 35%, #6fa8ff 68%, #eafff2 100%);
  background-size: 220% 100%;
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  animation: sweep 9s linear infinite;
}

@keyframes sweep {
  to { background-position: 220% 0; }
}

.lede {
  max-width: 560px;
  margin: 22px 0 0;
  color: var(--muted);
  font-size: 14.5px;
  line-height: 1.9;
}

.cta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 34px;
}

.btn-cta {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 12px 24px;
  border-radius: 12px;
  border: 1px solid var(--border-strong);
  color: var(--text);
  font-size: 13.5px;
  background: rgba(19, 28, 40, 0.7);
  backdrop-filter: blur(8px);
  transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;
}

.btn-cta:hover {
  transform: translateY(-2px);
  border-color: var(--border-strong);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.45);
}

.btn-cta.primary {
  border-color: transparent;
  color: #04120c;
  font-weight: 650;
  background: linear-gradient(135deg, #8ef0c6, #34d399 60%, #2bbd89);
  box-shadow: 0 10px 34px rgba(52, 211, 153, 0.28);
}

.btn-cta.primary:hover {
  box-shadow: 0 16px 44px rgba(52, 211, 153, 0.4);
}

.stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1px;
  margin-top: 58px;
  border-radius: 16px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.07);
  backdrop-filter: blur(10px);
}

.stat {
  padding: 18px 20px 16px;
  background: rgba(9, 14, 20, 0.82);
}

.stat-label {
  display: block;
  font-size: 11.5px;
  color: var(--faint);
  letter-spacing: 0.4px;
}

.stat b {
  display: block;
  margin: 8px 0 6px;
  font-size: 26px;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.5px;
}

.stat i {
  font-style: normal;
  font-size: 11px;
  color: var(--faint);
}

.entries {
  position: relative;
  z-index: 2;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 16px;
  margin-top: 58px;
}

.entry {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: 200px;
  padding: 22px 22px 18px;
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(13, 20, 28, 0.72);
  backdrop-filter: blur(10px);
  overflow: hidden;
  transform-style: preserve-3d;
  transition: transform 0.25s ease-out, border-color 0.25s, box-shadow 0.25s;
}

.entry::before {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(220px circle at var(--cx, 50%) var(--cy, 0%), rgba(255, 255, 255, 0.12), transparent 62%);
  opacity: 0;
  transition: opacity 0.25s;
  pointer-events: none;
}

.entry::after {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: inherit;
  padding: 1px;
  background: linear-gradient(140deg, var(--accent), transparent 55%);
  mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  opacity: 0.35;
  transition: opacity 0.25s;
  pointer-events: none;
}

.entry:hover::before,
.entry:hover::after {
  opacity: 1;
}

.entry:hover {
  box-shadow: 0 22px 48px rgba(0, 0, 0, 0.5);
  border-color: rgba(255, 255, 255, 0.14);
}

.entry-icon {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 12px;
  color: var(--accent);
  background: color-mix(in srgb, var(--accent) 12%, transparent);
  margin-bottom: 18px;
}

.entry-icon :deep(svg) {
  width: 22px;
  height: 22px;
}

.entry h3 {
  margin: 0 0 8px;
  font-size: 16.5px;
}

.entry p {
  margin: 0;
  color: var(--muted);
  font-size: 12.5px;
  line-height: 1.75;
}

.entry footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: auto;
  padding-top: 18px;
  font-size: 11.5px;
  color: var(--faint);
}

.entry footer b {
  color: var(--accent);
  font-weight: 600;
}

.arrow {
  font-size: 15px;
  color: var(--muted);
  transition: transform 0.2s, color 0.2s;
}

.entry:hover .arrow {
  transform: translateX(4px);
  color: var(--accent);
}

.entry.emerald { --accent: #34d399; }
.entry.blue { --accent: #5b9dff; }
.entry.amber { --accent: #f5b545; }
.entry.violet { --accent: #a78bfa; }
.entry.cyan { --accent: #22d3ee; }

.ripple {
  position: absolute;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.3), transparent 68%);
  transform: scale(0);
  animation: ripple 0.65s ease-out forwards;
  pointer-events: none;
}

@keyframes ripple {
  to { transform: scale(1); opacity: 0; }
}

.home-foot {
  position: relative;
  z-index: 2;
  display: flex;
  flex-wrap: wrap;
  gap: 22px;
  margin-top: 64px;
  padding-top: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.07);
  color: var(--faint);
  font-size: 11.5px;
}

.home-foot a:hover {
  color: var(--brand);
}

@media (max-width: 720px) {
  .home-links { display: none; }
  .stats { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .entries { grid-template-columns: 1fr; }
}

@media (prefers-reduced-motion: reduce) {
  .blob,
  .shine,
  .pulse,
  .caret { animation: none; }
}
</style>
