<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import request from '@/api/request'

const router = useRouter()
const templates = ref<any[]>([])
const categories = ref<string[]>(['全部'])
const search = ref('')
const activeCat = ref('全部')

// 预加载 chart-templates 各目录下 preview.png（eager + ?url）；键在 Windows 上可能含反斜杠，需兼容解析
const previewModules = import.meta.glob('../../../../../chart-templates/*/preview.png', { eager: true, query: '?url', import: 'default' })
const previewMap: Record<string, string> = {}
for (const [rawPath, url] of Object.entries(previewModules)) {
  const normalized = rawPath.replace(/\\/g, '/')
  const low = normalized.toLowerCase()
  const suffix = '/preview.png'
  if (!low.endsWith(suffix)) continue
  const dirPath = normalized.slice(0, -suffix.length)
  const id = dirPath.split('/').pop()?.trim()
  if (id) previewMap[id] = url as string
}

function getPreview(t: any): string | null {
  return previewMap[t.id] || null
}

async function loadTemplates() {
  const data = await request.get('/templates')
  templates.value = data || []
  const cats = new Set<string>()
  cats.add('全部')
  data?.forEach((t: any) => { if (t.category) cats.add(t.category) })
  categories.value = Array.from(cats)
}

const filtered = computed(() => {
  return templates.value.filter(t => {
    const matchCat = activeCat.value === '全部' || t.category === activeCat.value
    const matchSearch = !search.value || t.name?.includes(search.value) || t.description?.includes(search.value)
    return matchCat && matchSearch
  })
})

onMounted(loadTemplates)

function selectTemplate(tpl: any) {
  router.push(`/mode-select/${tpl.id}`)
}

const colorMap: Record<string, string> = {
  '常用图表': '#0ea5e9',
  '柱状图': '#3b82f6', '折线图': '#8b5cf6', '饼图': '#f59e0b', '雷达图': '#10b981',
  '散点图': '#ef4444', '流程图': '#6366f1', '架构图': '#0ea5e9', '热力图': '#ef4444',
}

function getColor(t: any) {
  return colorMap[t.category] || '#3b82f6'
}

function shouldShowHot(t: any) {
  const sortOrder = t.sort_order ?? t.sortOrder
  return t.category !== '常用图表' && sortOrder && sortOrder <= 3
}
</script>

<template>
  <div class="tpl-page">
    <header class="tpl-head">
      <div class="tpl-eyebrow">模板中心</div>
      <h1 class="tpl-title">选择图表模板</h1>
      <p class="tpl-sub">从丰富的模板库中选择，快速开始你的图表创作</p>
    </header>

    <div class="tpl-toolbar">
      <div class="tpl-search">
        <span class="tpl-search-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7.5"/><line x1="20.5" y1="20.5" x2="16.4" y2="16.4"/></svg>
        </span>
        <input v-model="search" placeholder="搜索模板名称或描述…" />
        <button v-if="search" class="tpl-search-clear" type="button" aria-label="清除搜索" @click="search = ''">
          <svg viewBox="0 0 24 24"><line x1="6" y1="6" x2="18" y2="18"/><line x1="18" y1="6" x2="6" y2="18"/></svg>
        </button>
      </div>

      <div class="tpl-cats">
        <button
          v-for="cat in categories"
          :key="cat"
          type="button"
          :class="['tpl-cat', { active: activeCat === cat }]"
          @click="activeCat = cat"
        >{{ cat }}</button>
      </div>
    </div>

    <div class="tpl-meta">
      共 <strong>{{ filtered.length }}</strong> 个模板
      <span v-if="activeCat !== '全部'"> · 分类「{{ activeCat }}」</span>
      <span v-if="search"> · 关键字「{{ search }}」</span>
    </div>

    <div v-if="filtered.length > 0" class="tpl-grid">
      <article
        v-for="t in filtered"
        :key="t.id"
        class="tpl-card"
        @click="selectTemplate(t)"
      >
        <div
          class="tpl-cover"
          :style="{ background: getPreview(t)
            ? '#fff'
            : `linear-gradient(135deg, ${getColor(t)}1A, ${getColor(t)}0A)` }"
        >
          <img
            v-if="getPreview(t)"
            :src="getPreview(t)!"
            :alt="t.name"
            loading="lazy"
            decoding="async"
            class="tpl-cover-img"
          />
          <div
            v-else
            class="tpl-cover-icon"
            :style="{ background: `${getColor(t)}18`, color: getColor(t) }"
          >
            <svg v-if="t.engine === 'vue-component'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><path d="M10 6.5h4.5a2 2 0 0 1 2 2V14"/></svg>
            <svg v-else-if="t.engine === 'drawio'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="9" y1="9" x2="15" y2="15"/><line x1="15" y1="9" x2="9" y2="15"/></svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
          </div>

          <span v-if="shouldShowHot(t)" class="tpl-badge-hot">HOT</span>
          <span class="tpl-badge-cat">{{ t.category }}</span>
        </div>

        <div class="tpl-body">
          <div class="tpl-name">{{ t.name }}</div>
          <div class="tpl-desc">{{ t.description }}</div>
        </div>

        <div class="tpl-footer">
          <span class="tpl-cta">使用模板</span>
          <svg class="tpl-arrow" viewBox="0 0 24 24" aria-hidden="true">
            <line x1="5" y1="12" x2="19" y2="12"/>
            <polyline points="13 6 19 12 13 18"/>
          </svg>
        </div>
      </article>
    </div>

    <div v-else class="tpl-empty">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="11" cy="11" r="7.5"/>
        <line x1="20.5" y1="20.5" x2="16.4" y2="16.4"/>
      </svg>
      <p>没有找到匹配的模板</p>
      <button v-if="search || activeCat !== '全部'" type="button" class="tpl-empty-reset" @click="search = ''; activeCat = '全部'">清除筛选</button>
    </div>
  </div>
</template>

<style scoped lang="scss">
.tpl-page {
  --ink: #0f172a;
  --ink-2: #475569;
  --ink-3: #94a3b8;
  --line: #e5e7ef;
  --line-strong: #d4d8e3;
  --primary: #2563eb;
  --primary-soft: rgba(37, 99, 235, 0.08);
  --primary-ring: rgba(37, 99, 235, 0.18);
  --surface: #fff;
  --surface-soft: #f8fafc;

  max-width: 1240px;
  margin: 0 auto;
  padding: 40px 28px 64px;
  color: var(--ink);
}

/* ===== 头部 ===== */
.tpl-head {
  text-align: center;
  margin-bottom: 36px;
}
.tpl-eyebrow {
  display: inline-block;
  font-size: 12px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--primary);
  background: var(--primary-soft);
  padding: 4px 12px;
  border-radius: 999px;
  margin-bottom: 16px;
}
.tpl-title {
  font-size: clamp(28px, 3vw, 36px);
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--ink);
  margin: 0 0 10px;
}
.tpl-sub {
  font-size: 15px;
  color: var(--ink-3);
  max-width: 520px;
  margin: 0 auto;
  line-height: 1.7;
}

/* ===== 工具栏 ===== */
.tpl-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
  margin-bottom: 14px;
}
.tpl-search {
  position: relative;
  flex: 0 0 360px;
  max-width: 100%;
}
.tpl-search input {
  width: 100%;
  height: 44px;
  padding: 0 36px 0 42px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--surface);
  font: inherit;
  font-size: 14px;
  color: var(--ink);
  outline: 0;
  transition: border-color 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
}
.tpl-search input::placeholder { color: var(--ink-3); }
.tpl-search input:hover { border-color: var(--line-strong); }
.tpl-search input:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 4px var(--primary-ring);
}
.tpl-search-icon {
  position: absolute;
  top: 50%; left: 14px;
  transform: translateY(-50%);
  color: var(--ink-3);
  display: grid; place-items: center;
}
.tpl-search-icon svg {
  width: 16px; height: 16px;
  fill: none; stroke: currentColor;
  stroke-width: 1.7; stroke-linecap: round;
}
.tpl-search-clear {
  position: absolute;
  top: 50%; right: 8px;
  transform: translateY(-50%);
  width: 28px; height: 28px;
  display: grid; place-items: center;
  border: 0; background: transparent;
  color: var(--ink-3);
  cursor: pointer;
  border-radius: 8px;
  transition: background 0.15s ease, color 0.15s ease;
}
.tpl-search-clear:hover { background: var(--surface-soft); color: var(--ink-2); }
.tpl-search-clear svg {
  width: 14px; height: 14px;
  fill: none; stroke: currentColor;
  stroke-width: 1.8; stroke-linecap: round;
}

.tpl-cats {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  flex: 1;
  justify-content: flex-end;
}
.tpl-cat {
  padding: 7px 14px;
  font-family: inherit;
  font-size: 13px;
  color: var(--ink-2);
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 999px;
  cursor: pointer;
  transition: color 0.18s ease, background 0.18s ease,
              border-color 0.18s ease, box-shadow 0.18s ease;
}
.tpl-cat:hover {
  color: var(--primary);
  border-color: rgba(37, 99, 235, 0.35);
  background: var(--primary-soft);
}
.tpl-cat.active {
  color: #fff;
  background: var(--primary);
  border-color: var(--primary);
  box-shadow: 0 4px 12px -6px rgba(37, 99, 235, 0.5);
}

/* ===== 计数 ===== */
.tpl-meta {
  font-size: 13px;
  color: var(--ink-3);
  margin: 0 0 22px;
}
.tpl-meta strong {
  color: var(--ink);
  font-weight: 600;
}

/* ===== 卡片网格 ===== */
.tpl-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 22px;
}

.tpl-card {
  position: relative;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 16px;
  cursor: pointer;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: transform 0.22s cubic-bezier(0.22, 1, 0.36, 1),
              box-shadow 0.22s ease,
              border-color 0.22s ease;
}
.tpl-card:hover {
  transform: translateY(-3px);
  border-color: rgba(37, 99, 235, 0.35);
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.04),
    0 18px 40px -18px rgba(15, 23, 42, 0.18);
}
.tpl-card:focus-visible {
  outline: 0;
  border-color: var(--primary);
  box-shadow: 0 0 0 4px var(--primary-ring);
}

.tpl-cover {
  position: relative;
  height: 150px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-bottom: 1px solid var(--line);
}
.tpl-cover-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
  transition: transform 0.4s cubic-bezier(0.22, 1, 0.36, 1);
}
.tpl-card:hover .tpl-cover-img { transform: scale(1.04); }

.tpl-cover-icon {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  display: grid;
  place-items: center;
}
.tpl-cover-icon svg {
  width: 30px;
  height: 30px;
}

.tpl-badge-hot {
  position: absolute;
  top: 10px; right: 10px;
  padding: 2px 8px;
  background: linear-gradient(135deg, #f43f5e, #ef4444);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  border-radius: 999px;
  box-shadow: 0 4px 10px -4px rgba(239, 68, 68, 0.55);
}
.tpl-badge-cat {
  position: absolute;
  bottom: 10px; left: 12px;
  padding: 3px 10px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid var(--line);
  border-radius: 999px;
  font-size: 11px;
  color: var(--ink-2);
  backdrop-filter: blur(6px);
}

.tpl-body {
  padding: 14px 18px 4px;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.tpl-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--ink);
  letter-spacing: 0.01em;
}
.tpl-desc {
  font-size: 13px;
  line-height: 1.55;
  color: var(--ink-3);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.tpl-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 18px 14px;
  font-size: 13px;
  color: var(--ink-3);
  transition: color 0.2s ease;
}
.tpl-card:hover .tpl-footer { color: var(--primary); }
.tpl-cta {
  font-weight: 500;
  letter-spacing: 0.04em;
}
.tpl-arrow {
  width: 18px; height: 18px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.6;
  stroke-linecap: round;
  stroke-linejoin: round;
  transition: transform 0.22s ease;
}
.tpl-card:hover .tpl-arrow { transform: translateX(4px); }

/* ===== 空状态 ===== */
.tpl-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 80px 24px;
  color: var(--ink-3);
}
.tpl-empty svg {
  width: 44px; height: 44px;
  fill: none;
  stroke: #cbd5e1;
  stroke-width: 1.6;
  stroke-linecap: round;
}
.tpl-empty p {
  margin: 0;
  font-size: 14px;
}
.tpl-empty-reset {
  margin-top: 4px;
  padding: 6px 14px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: #fff;
  font-family: inherit;
  font-size: 13px;
  color: var(--primary);
  cursor: pointer;
  transition: border-color 0.18s ease, background 0.18s ease;
}
.tpl-empty-reset:hover {
  border-color: rgba(37, 99, 235, 0.35);
  background: var(--primary-soft);
}

@media (max-width: 720px) {
  .tpl-page { padding: 28px 16px 48px; }
  .tpl-toolbar { flex-direction: column; align-items: stretch; }
  .tpl-search { flex: 1 1 auto; }
  .tpl-cats { justify-content: flex-start; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    transition: none !important;
    animation: none !important;
  }
}
</style>
