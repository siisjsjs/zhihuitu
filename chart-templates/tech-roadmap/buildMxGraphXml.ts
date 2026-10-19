/**
 * 技术路线图（Tech Roadmap）→ Draw.io (mxGraphModel) XML
 *
 * 布局：统一格子大小，蛇形排列（左→右，右→左交替），行内居中。
 * 连线：同行水平连接（LTR右出左入 / RTL左出右入），跨行垂直连接（底出顶入）。
 */

export interface RoadmapNode {
  id: string
  label: string
  detail: string
}

export interface RoadmapStage {
  name: string
  color: string
  nodes: RoadmapNode[]
}

export interface RoadmapPayload {
  title: string
  stages: RoadmapStage[]
}

const STAGE_COLORS = ['#6c8ebf', '#d79b00', '#82b366', '#9673a6', '#b85450', '#2E75B6']

export function defaultRoadmapPayload(): RoadmapPayload {
  return {
    title: '技术路线图',
    stages: [
      {
        name: '第一阶段\n理论研究',
        color: '#6c8ebf',
        nodes: [
          { id: 'n1', label: '文献综述', detail: '' },
          { id: 'n2', label: '理论框架', detail: '' },
        ],
      },
    ],
  }
}

export function exampleRoadmapPayload(): RoadmapPayload {
  return {
    title: '数字经济赋能乡村振兴研究技术路线图',
    stages: [
      {
        name: '第一阶段\n理论基础',
        color: '#6c8ebf',
        nodes: [
          { id: 's1_a', label: '文献梳理', detail: '' },
          { id: 's1_b', label: '概念界定', detail: '' },
          { id: 's1_c', label: '框架构建', detail: '' },
          { id: 's1_d', label: '假设提出', detail: '' },
        ],
      },
      {
        name: '第二阶段\n实证分析',
        color: '#d79b00',
        nodes: [
          { id: 's2_a', label: '指标构建', detail: '' },
          { id: 's2_b', label: '数据采集', detail: '' },
          { id: 's2_c', label: '模型设定', detail: '' },
          { id: 's2_d', label: '稳健检验', detail: '' },
        ],
      },
      {
        name: '第三阶段\n机制分解',
        color: '#82b366',
        nodes: [
          { id: 's3_a', label: '效应测度', detail: '' },
          { id: 's3_b', label: '路径识别', detail: '' },
          { id: 's3_c', label: '异质分析', detail: '' },
          { id: 's3_d', label: '空间检验', detail: '' },
        ],
      },
      {
        name: '第四阶段\n政策建议',
        color: '#9673a6',
        nodes: [
          { id: 's4_a', label: '结论提炼', detail: '' },
          { id: 's4_b', label: '政策设计', detail: '' },
          { id: 's4_c', label: '方案验证', detail: '' },
          { id: 's4_d', label: '展望创新', detail: '' },
        ],
      },
    ],
  }
}

function normNode(n: any, idx: number): RoadmapNode {
  return {
    id: String(n?.id ?? `n${idx}`),
    label: String(n?.label ?? ''),
    detail: String(n?.detail ?? ''),
  }
}

function normStage(s: any, idx: number): RoadmapStage {
  const nodes = Array.isArray(s?.nodes) ? s.nodes.map((n: any, i: number) => normNode(n, i)) : []
  return {
    name: String(s?.name ?? `第${idx + 1}阶段`),
    color: String(s?.color ?? STAGE_COLORS[idx % STAGE_COLORS.length]),
    nodes,
  }
}

export function coerceRoadmapPayload(raw: Record<string, any> | null | undefined): RoadmapPayload {
  const base = defaultRoadmapPayload()
  if (!raw || typeof raw !== 'object') return base
  return {
    title: raw.title != null && String(raw.title).trim() !== '' ? String(raw.title) : base.title,
    stages: Array.isArray(raw.stages) && raw.stages.length > 0
      ? raw.stages.map((s: any, i: number) => normStage(s, i))
      : base.stages.map((s, i) => normStage(s, i)),
  }
}

/* ─── helpers ─── */

function escapeXml(s: string): string {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

const BG_FILL_MAP: Record<string, string> = {
  '#6c8ebf': '#dae8fc', '#d79b00': '#ffe6cc', '#82b366': '#d5e8d4',
  '#9673a6': '#e1d5e7', '#b85450': '#f8cecc', '#2E75B6': '#BDD7EE',
}

function estimateLineW(line: string): number {
  let w = 0
  for (const ch of line) {
    w += ch.charCodeAt(0) > 127 ? 22 : 12
  }
  return w
}

function calcNodeW(node: RoadmapNode): number {
  const lines = [node.label]
  if (node.detail) lines.push(...node.detail.split('\n'))
  const maxLineW = Math.max(...lines.map(l => estimateLineW(l)))
  return Math.min(Math.max(maxLineW + 60, 200), 420)
}

function calcNodeH(node: RoadmapNode): number {
  const detailLines = node.detail ? node.detail.split('\n').length : 0
  const totalLines = 1 + (detailLines > 0 ? 1 + detailLines : 0)
  return Math.max(totalLines * 22 + 16, 60)
}

function nodeDisplayText(node: RoadmapNode): string {
  if (!node.detail) return escapeXml(node.label)
  return escapeXml(node.label) + '&#xa;━━━━━━━━━━━━&#xa;' + escapeXml(node.detail).replace(/\n/g, '&#xa;')
}

/* ─── XML builder ─── */

export function buildRoadmapMxGraphXml(payload: RoadmapPayload): string {
  const cells: string[] = []
  let nid = 2
  const pid = () => String(nid++)

  cells.push('<mxCell id="0"/>')
  cells.push('<mxCell id="1" parent="0"/>')

  const LABEL_W = 150
  const CONTENT_W = 1410
  const CONTENT_X = LABEL_W + 20
  const TOTAL_W = CONTENT_X + CONTENT_W
  const TITLE_H = 50
  const STAGE_PAD = 15
  const NODE_GAP = 40
  const ROW_GAP = 28
  const STAGE_GAP = 20

  const groupId = pid()
  const groupIdx = cells.length
  cells.push('')

  const titleId = pid()
  cells.push(
    `<mxCell id="${titleId}" value="${escapeXml(payload.title)}" style="text;html=1;align=center;verticalAlign=middle;fontSize=41;fontStyle=1;fillColor=#f5f5f5;strokeColor=#cccccc;" vertex="1" parent="${groupId}"><mxGeometry height="${TITLE_H}" width="${TOTAL_W}" as="geometry"/></mxCell>`
  )

  let curY = TITLE_H + 20

  for (const stage of payload.stages) {
    const bgFill = BG_FILL_MAP[stage.color] || '#f5f5f5'
    const nodeCount = stage.nodes.length
    if (nodeCount === 0) continue

    const AVAIL_W = CONTENT_W - STAGE_PAD * 2

    const uniformW = Math.max(200, ...stage.nodes.map(n => calcNodeW(n)))
    const uniformH = Math.max(60, ...stage.nodes.map(n => calcNodeH(n)))
    const maxPerRow = Math.max(1, Math.floor((AVAIL_W + NODE_GAP) / (uniformW + NODE_GAP)))

    // Split into rows
    const rows: number[][] = []
    for (let i = 0; i < nodeCount; i += maxPerRow) {
      const row: number[] = []
      for (let j = i; j < Math.min(i + maxPerRow, nodeCount); j++) row.push(j)
      rows.push(row)
    }

    // Grid-based placement: fixed slot positions, LTR left-align, RTL right-align
    const cellIds: string[] = []
    const nodeRowIdx: number[] = []
    const nodeIsRTL: boolean[] = []
    const placements: Array<{ idx: number; cellId: string; x: number; y: number; w: number; h: number }> = []
    let rowY = curY + STAGE_PAD

    const totalGridW = maxPerRow * uniformW + (maxPerRow - 1) * NODE_GAP
    const gridBaseX = CONTENT_X + STAGE_PAD + Math.max((AVAIL_W - totalGridW) / 2, 0)
    const slotX = (s: number) => gridBaseX + s * (uniformW + NODE_GAP)

    for (let ri = 0; ri < rows.length; ri++) {
      const row = rows[ri]
      const isRTL = ri % 2 === 1

      for (let ci = 0; ci < row.length; ci++) {
        const idx = row[ci]
        const cellId = pid()
        cellIds[idx] = cellId
        nodeRowIdx[idx] = ri
        nodeIsRTL[idx] = isRTL

        // LTR: fill slots from left (0,1,2...) / RTL: fill slots from right (max-1, max-2...)
        const slot = isRTL ? (maxPerRow - 1 - ci) : ci
        placements.push({ idx, cellId, x: Math.round(slotX(slot)), y: rowY, w: uniformW, h: uniformH })
      }
      rowY += uniformH + ROW_GAP
    }

    const stageH = (rowY - ROW_GAP + STAGE_PAD) - curY

    // Label
    const labelId = pid()
    cells.push(
      `<mxCell id="${labelId}" value="${escapeXml(stage.name).replace(/\n/g, '&#xa;')}" style="rounded=0;whiteSpace=wrap;html=1;dashed=1;dashPattern=4 4;fillColor=#f5f5f5;strokeColor=${stage.color};fontSize=21;fontStyle=1;align=center;verticalAlign=middle;" vertex="1" parent="${groupId}"><mxGeometry y="${curY}" height="${stageH}" width="${LABEL_W}" as="geometry"/></mxCell>`
    )

    // Background
    const bgId = pid()
    cells.push(
      `<mxCell id="${bgId}" value="" style="rounded=1;whiteSpace=wrap;html=1;fillColor=${bgFill};strokeColor=${stage.color};fillOpacity=30;" vertex="1" parent="${groupId}"><mxGeometry x="${CONTENT_X}" y="${curY}" height="${stageH}" width="${CONTENT_W}" as="geometry"/></mxCell>`
    )

    // Nodes
    for (const p of placements) {
      const node = stage.nodes[p.idx]
      const style = `rounded=1;whiteSpace=wrap;html=1;fontSize=21;align=center;verticalAlign=middle;fillColor=#ffffff;strokeColor=${stage.color};`
      cells.push(
        `<mxCell id="${p.cellId}" value="${nodeDisplayText(node)}" style="${style}" vertex="1" parent="${groupId}"><mxGeometry x="${p.x}" y="${p.y}" width="${p.w}" height="${p.h}" as="geometry"/></mxCell>`
      )
    }

    // Auto-connect with direction-aware entry/exit points
    const EDGE_BASE = `edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;strokeColor=${stage.color};strokeWidth=2;`
    for (let i = 0; i < nodeCount - 1; i++) {
      const edgeId = pid()
      let entryExit = ''

      if (nodeRowIdx[i] === nodeRowIdx[i + 1]) {
        // Same row
        if (nodeIsRTL[i]) {
          // RTL row: arrow goes ← (exit left, enter right)
          entryExit = 'exitX=0;exitY=0.5;exitDx=0;exitDy=0;entryX=1;entryY=0.5;entryDx=0;entryDy=0;'
        } else {
          // LTR row: arrow goes → (exit right, enter left)
          entryExit = 'exitX=1;exitY=0.5;exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;'
        }
      } else {
        // Cross-row: check if same column (grid-aligned)
        const fromP = placements.find(p => p.idx === i)!
        const toP = placements.find(p => p.idx === i + 1)!
        if (Math.abs(fromP.x - toP.x) < 2) {
          // Same column → straight down
          entryExit = 'exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;'
        } else if (nodeIsRTL[i + 1]) {
          entryExit = 'exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=1;entryY=0.5;entryDx=0;entryDy=0;'
        } else {
          entryExit = 'exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;'
        }
      }

      cells.push(
        `<mxCell id="${edgeId}" style="${EDGE_BASE}${entryExit}" edge="1" source="${cellIds[i]}" target="${cellIds[i + 1]}" parent="${groupId}"><mxGeometry relative="1" as="geometry"/></mxCell>`
      )
    }

    curY += stageH + STAGE_GAP
  }

  const totalH = curY
  cells[groupIdx] = `<mxCell id="${groupId}" value="" style="group" connectable="0" vertex="1" parent="1"><mxGeometry x="60" y="20" width="${TOTAL_W}" height="${totalH}" as="geometry"/></mxCell>`

  const xmlInner = cells.join('')
  const pageW = TOTAL_W + 140
  const pageH = totalH + 60
  const graph = `<mxGraphModel dx="${Math.max(2200, pageW)}" dy="${Math.max(1600, pageH)}" grid="0" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="${pageW}" pageHeight="${pageH}" math="0" shadow="0"><root>${xmlInner}</root></mxGraphModel>`
  return `<mxfile host="embed.diagrams.net"><diagram id="tech-roadmap" name="技术路线图">${graph}</diagram></mxfile>`
}
