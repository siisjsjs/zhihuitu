<script setup lang="ts">
/** 编码树：纯 SVG 分层渲染（无第三方图库）。上游→下游从左到右布局。 */
import { computed } from 'vue'
import type { TreeNode, TreeEdge } from '@/api/lineBalance'

const props = defineProps<{ nodes: TreeNode[]; edges: TreeEdge[] }>()

const BOX_W = 150
const BOX_H = 56
const GAP_X = 70
const GAP_Y = 30
const PAD = 20
const MAT_LH = 13   // 物料每行高度

type Laid = TreeNode & { _x: number; _y: number; _level: number }

function matList(n: TreeNode): string[] {
  const ms = (n as any).materials
  if (!Array.isArray(ms)) return []
  return ms.map((m: any) => {
    const name = m.pieceName || m.pieceCode || ''
    const qty = m.quantity != null ? `×${m.quantity}` : ''
    return `${name}${qty}`
  }).filter(Boolean)
}
function boxH(n: TreeNode): number {
  return BOX_H + matList(n).length * MAT_LH
}

const layout = computed(() => {
  const nodes = props.nodes
  const edges = props.edges
  if (!nodes.length) return { laid: [] as Laid[], width: 0, height: 0, links: [] as any[] }

  const incoming: Record<string, string[]> = {}
  const outgoing: Record<string, string[]> = {}
  nodes.forEach((n) => { incoming[n.id] = []; outgoing[n.id] = [] })
  edges.forEach((e) => {
    if (incoming[e.target]) incoming[e.target].push(e.source)
    if (outgoing[e.source]) outgoing[e.source].push(e.target)
  })

  // 最长路径定层级
  const level: Record<string, number> = {}
  const visiting: Record<string, boolean> = {}
  function lv(id: string): number {
    if (level[id] !== undefined) return level[id]
    if (visiting[id]) return 0
    visiting[id] = true
    const ups = incoming[id] || []
    const v = ups.length ? Math.max(...ups.map(lv)) + 1 : 0
    visiting[id] = false
    level[id] = v
    return v
  }
  nodes.forEach((n) => lv(n.id))

  const byLevel: Record<number, TreeNode[]> = {}
  nodes.forEach((n) => {
    const l = level[n.id]
    ;(byLevel[l] ||= []).push(n)
  })

  const laid: Laid[] = []
  const pos: Record<string, { x: number; y: number; h: number }> = {}
  Object.keys(byLevel).map(Number).sort((a, b) => a - b).forEach((l) => {
    let y = PAD
    byLevel[l].forEach((n) => {
      const x = PAD + l * (BOX_W + GAP_X)
      const h = boxH(n)
      pos[n.id] = { x, y, h }
      laid.push({ ...n, _x: x, _y: y, _level: l })
      y += h + GAP_Y
    })
  })

  const maxLevel = Math.max(...Object.keys(byLevel).map(Number))
  const colHeights = Object.values(byLevel).map(
    (col) => PAD * 2 + col.reduce((s, n) => s + boxH(n), 0) + (col.length - 1) * GAP_Y,
  )
  const width = PAD * 2 + (maxLevel + 1) * BOX_W + maxLevel * GAP_X
  const height = Math.max(...colHeights)

  const links = edges
    .filter((e) => pos[e.source] && pos[e.target])
    .map((e) => {
      const s = pos[e.source], t = pos[e.target]
      const x1 = s.x + BOX_W, y1 = s.y + BOX_H / 2
      const x2 = t.x, y2 = t.y + BOX_H / 2
      const mx = (x1 + x2) / 2
      return { d: `M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}` }
    })

  return { laid, width, height, links }
})

function fill(n: Laid): string {
  if (n.isBottleneck) return '#fef2f2'
  if (n.segmentReason) return '#fffbeb'
  return '#f0f9ff'
}
function stroke(n: Laid): string {
  if (n.isBottleneck) return '#dc2626'
  if (n.segmentReason) return '#d97706'
  return '#2563eb'
}
</script>

<template>
  <div v-if="!layout.laid.length" style="color:#94a3b8;padding:24px;text-align:center">暂无编码树，请先生成编码</div>
  <div v-else style="overflow:auto;border:1px solid #e2e8f0;border-radius:8px;background:#fff">
    <svg :width="layout.width" :height="layout.height" :viewBox="`0 0 ${layout.width} ${layout.height}`">
      <path v-for="(lk, i) in layout.links" :key="i" :d="lk.d" fill="none" stroke="#94a3b8" stroke-width="1.5" />
      <g v-for="n in layout.laid" :key="n.id">
        <rect :x="n._x" :y="n._y" :width="150" :height="56 + matList(n).length * 13" rx="8"
          :fill="fill(n)" :stroke="stroke(n)" stroke-width="1.5" />
        <text :x="n._x + 8" :y="n._y + 18" font-size="12" font-weight="700" fill="#0f172a">
          {{ n.genCode || n.id }}
        </text>
        <text :x="n._x + 8" :y="n._y + 34" font-size="11" fill="#475569">
          {{ (n.name || '').slice(0, 12) }}
        </text>
        <text :x="n._x + 8" :y="n._y + 49" font-size="10" fill="#64748b">
          SAM {{ n.sam }}s · {{ n.loadRatio ?? '-' }}%
        </text>
        <text v-if="n.segmentReason || n.isBottleneck" :x="n._x + 142" :y="n._y + 16"
          font-size="9" text-anchor="end" :fill="stroke(n)">
          {{ n.isBottleneck ? '瓶颈' : n.segmentReason }}
        </text>
        <template v-if="matList(n).length">
          <line :x1="n._x + 6" :y1="n._y + 56" :x2="n._x + 144" :y2="n._y + 56"
            stroke="#cbd5e1" stroke-width="0.8" stroke-dasharray="2 2" />
          <text v-for="(m, mi) in matList(n)" :key="mi"
            :x="n._x + 8" :y="n._y + 56 + 11 + mi * 13" font-size="9" fill="#0891b2">
            🔩 {{ m.slice(0, 16) }}
          </text>
        </template>
      </g>
    </svg>
  </div>
</template>
