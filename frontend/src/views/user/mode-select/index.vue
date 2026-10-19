<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { ref, onMounted } from 'vue'
import request from '@/api/request'

const router = useRouter()
const route = useRoute()
const template = ref<any>(null)

onMounted(async () => {
  template.value = await request.get(`/templates/${route.params.templateId}`)
})

const modes = [
  {
    key: 'form',
    title: '表单模式',
    desc: '通过结构化表单填写数据，实时预览图表效果，适合数据已准备好的场景',
    features: ['结构化数据输入', '实时图表预览', '快速生成'],
    accent: '#2563eb',
    soft: '#eff6ff',
    primary: true,
  },
  {
    key: 'ai',
    title: 'AI 对话模式',
    desc: '通过自然语言描述你的需求，AI 自动理解并生成图表，支持多轮对话调整',
    features: ['自然语言交互', '智能理解意图', '多轮对话调整'],
    accent: '#8b5cf6',
    soft: '#f5f3ff',
    primary: false,
  },
]

function pickMode(key: string) {
  if (key === 'form') router.push(`/form/${route.params.templateId}`)
  else router.push(`/ai-chat/${route.params.templateId}`)
}
</script>

<template>
  <div class="ms-page">
    <header class="ms-head">
      <button class="ms-back" type="button" @click="router.push('/templates')">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <line x1="19" y1="12" x2="5" y2="12"/>
          <polyline points="12 19 5 12 12 5"/>
        </svg>
        返回模板中心
      </button>
      <span class="ms-tpl">{{ template?.name || '加载中…' }}</span>
    </header>

    <main class="ms-main">
      <div v-if="template">
        <div class="ms-intro">
          <span class="ms-chip">{{ template.name }}</span>
          <h2 class="ms-title">选择生成方式</h2>
          <p class="ms-sub">两种创作路径，挑一个开始</p>
        </div>

        <div class="ms-grid">
          <article
            v-for="m in modes"
            :key="m.key"
            class="ms-card"
            :class="{ 'is-primary': m.primary, 'is-ai': !m.primary }"
            :style="{ '--accent': m.accent, '--soft': m.soft } as any"
            tabindex="0"
            @click="pickMode(m.key)"
            @keyup.enter="pickMode(m.key)"
          >
            <span class="ms-card-glow" aria-hidden="true" />

            <div class="ms-icon-wrap">
              <span class="ms-icon-bg" aria-hidden="true" />

              <!-- 表单模式：纸张表单 + 复选 + 数据点 -->
              <svg v-if="m.key === 'form'" class="ms-icon" viewBox="0 0 56 56" aria-hidden="true">
                <rect x="10" y="8" width="36" height="44" rx="5" fill="#fff" stroke="currentColor" stroke-width="1.6"/>
                <line x1="16" y1="16" x2="34" y2="16" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
                <line x1="16" y1="22" x2="40" y2="22" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" opacity="0.55"/>
                <rect x="16" y="28" width="24" height="4" rx="1" fill="currentColor" opacity="0.18"/>
                <rect x="16" y="36" width="18" height="4" rx="1" fill="currentColor" opacity="0.32"/>
                <rect x="16" y="44" width="12" height="4" rx="1" fill="currentColor" opacity="0.5"/>
                <circle cx="42" cy="44" r="6" fill="currentColor"/>
                <polyline points="39 44 41.5 46.5 45 42.8" fill="none" stroke="#fff" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>

              <!-- AI 对话模式：对话气泡 + 闪光（AI sparkle） -->
              <svg v-else class="ms-icon" viewBox="0 0 56 56" aria-hidden="true">
                <path d="M10 14a4 4 0 0 1 4-4h22a4 4 0 0 1 4 4v14a4 4 0 0 1-4 4H22l-7 6v-6h-1a4 4 0 0 1-4-4Z"
                      fill="#fff" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>
                <circle cx="20" cy="21" r="1.6" fill="currentColor"/>
                <circle cx="26" cy="21" r="1.6" fill="currentColor"/>
                <circle cx="32" cy="21" r="1.6" fill="currentColor"/>
                <path d="M42 36 L43.6 41 L48.5 42.5 L43.6 44 L42 49 L40.4 44 L35.5 42.5 L40.4 41 Z"
                      fill="currentColor"/>
                <path d="M16 42 L16.8 44.4 L19.2 45.2 L16.8 46 L16 48.4 L15.2 46 L12.8 45.2 L15.2 44.4 Z"
                      fill="currentColor" opacity="0.55"/>
              </svg>
            </div>

            <h3 class="ms-card-title">{{ m.title }}</h3>
            <p class="ms-card-desc">{{ m.desc }}</p>

            <ul class="ms-features">
              <li v-for="f in m.features" :key="f">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <polyline points="5 12.5 10 17.5 19 7.5"/>
                </svg>
                <span>{{ f }}</span>
              </li>
            </ul>

            <button class="ms-cta" type="button" @click.stop="pickMode(m.key)">
              <span>选择此模式</span>
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <line x1="5" y1="12" x2="19" y2="12"/>
                <polyline points="13 6 19 12 13 18"/>
              </svg>
            </button>
          </article>
        </div>
      </div>

      <el-skeleton v-else :rows="6" animated />
    </main>
  </div>
</template>

<style scoped lang="scss">
.ms-page {
  --ink: #0f172a;
  --ink-2: #475569;
  --ink-3: #94a3b8;
  --line: #e5e7ef;
  --line-strong: #d4d8e3;
  --bg: #f7f9fc;

  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg);
  color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
               'PingFang SC', 'Microsoft YaHei', 'Helvetica Neue', Arial, sans-serif;
}

/* ===== 头部 ===== */
.ms-head {
  height: 56px;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 24px;
  background: #fff;
  border-bottom: 1px solid var(--line);
}
.ms-back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 0;
  background: transparent;
  font: inherit;
  font-size: 13px;
  color: var(--ink-2);
  border-radius: 8px;
  cursor: pointer;
  transition: color 0.18s ease, background 0.18s ease;
}
.ms-back:hover { color: var(--ink); background: #f1f5f9; }
.ms-back svg {
  width: 16px; height: 16px;
  fill: none; stroke: currentColor;
  stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round;
}
.ms-tpl {
  font-weight: 600;
  color: var(--ink);
  font-size: 14px;
  padding-left: 14px;
  border-left: 1px solid var(--line);
}

/* ===== 内容区 ===== */
.ms-main {
  width: 100%;
  max-width: 920px;
  margin: 0 auto;
  padding: 56px 24px 64px;
}

.ms-intro {
  text-align: center;
  margin-bottom: 44px;
}
.ms-chip {
  display: inline-flex;
  padding: 4px 14px;
  font-size: 12px;
  letter-spacing: 0.06em;
  color: #2563eb;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 999px;
}
.ms-title {
  font-size: clamp(26px, 3vw, 32px);
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--ink);
  margin: 16px 0 6px;
}
.ms-sub {
  font-size: 14px;
  color: var(--ink-3);
  margin: 0;
}

/* ===== 卡片 ===== */
.ms-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 22px;
}
@media (max-width: 720px) {
  .ms-grid { grid-template-columns: 1fr; }
  .ms-main { padding: 36px 16px 48px; }
}

.ms-card {
  position: relative;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 30px 28px 26px;
  cursor: pointer;
  overflow: hidden;
  transition: transform 0.22s cubic-bezier(0.22, 1, 0.36, 1),
              box-shadow 0.22s ease,
              border-color 0.22s ease;
  display: flex;
  flex-direction: column;
}
.ms-card:hover,
.ms-card:focus-visible {
  transform: translateY(-3px);
  border-color: color-mix(in srgb, var(--accent) 40%, var(--line));
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.04),
    0 18px 40px -18px color-mix(in srgb, var(--accent) 50%, transparent);
}
.ms-card:focus-visible { outline: 0; }

/* hover 时左上角浮现的柔光 */
.ms-card-glow {
  position: absolute;
  top: -60px; left: -60px;
  width: 220px; height: 220px;
  border-radius: 50%;
  background: radial-gradient(closest-side, color-mix(in srgb, var(--accent) 28%, transparent), transparent);
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
}
.ms-card:hover .ms-card-glow,
.ms-card:focus-visible .ms-card-glow { opacity: 1; }

/* 图标块 */
.ms-icon-wrap {
  position: relative;
  width: 76px;
  height: 76px;
  margin-bottom: 22px;
  display: grid;
  place-items: center;
}
.ms-icon-bg {
  position: absolute;
  inset: 0;
  border-radius: 20px;
  background: var(--soft);
  border: 1px solid color-mix(in srgb, var(--accent) 18%, transparent);
  transition: transform 0.4s cubic-bezier(0.22, 1, 0.36, 1);
}
.ms-card:hover .ms-icon-bg { transform: rotate(-4deg) scale(1.04); }

.ms-icon {
  position: relative;
  width: 44px;
  height: 44px;
  color: var(--accent);
}

.ms-card-title {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.005em;
  color: var(--ink);
  margin: 0 0 8px;
}
.ms-card-desc {
  font-size: 14px;
  line-height: 1.7;
  color: var(--ink-2);
  margin: 0 0 18px;
}

.ms-features {
  list-style: none;
  margin: 0 0 22px;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.ms-features li {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--ink-2);
}
.ms-features svg {
  width: 16px; height: 16px;
  fill: none;
  stroke: var(--accent);
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
  flex: none;
}

.ms-cta {
  margin-top: auto;
  width: 100%;
  height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 1px solid var(--accent);
  background: var(--accent);
  color: #fff;
  font-family: inherit;
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.04em;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.18s ease, color 0.18s ease,
              transform 0.18s ease, box-shadow 0.18s ease;
}
.ms-cta svg {
  width: 16px; height: 16px;
  fill: none; stroke: currentColor;
  stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round;
  transition: transform 0.22s ease;
}
.ms-cta:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px -10px color-mix(in srgb, var(--accent) 70%, transparent);
}
.ms-cta:hover svg { transform: translateX(4px); }
.ms-cta:focus-visible {
  outline: 0;
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent) 22%, transparent);
}

/* AI 卡 → 改成描边按钮，区分主次（保持视觉层级一致性） */
.ms-card.is-ai .ms-cta {
  background: #fff;
  color: var(--accent);
}
.ms-card.is-ai .ms-cta:hover {
  background: var(--soft);
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    transition: none !important;
    animation: none !important;
  }
}
</style>
