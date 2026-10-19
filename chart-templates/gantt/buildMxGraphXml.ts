/**
 * 甘特图（Gantt Chart）→ Draw.io (mxGraphModel) XML
 * 支持多阶段、每阶段多任务，按月份时间轴排列横道。
 */

export interface GanttTask {
  name: string
  /** 开始月份（1-based，如 1 表示第 1 个月开头，1.5 表示第 1 个月中间） */
  startMonth: number
  /** 持续月份数 */
  duration: number
}

export interface GanttPhase {
  name: string
  /** 阶段主题色 hex，如 #4472C4 */
  color: string
  startMonth: number
  duration: number
  tasks: GanttTask[]
}

export interface GanttPayload {
  title: string
  /** 月份标签，如 ["1月","2月",...,"12月"] */
  months: string[]
  phases: GanttPhase[]
}

const DEFAULT_PHASE_COLORS = [
  '#4472C4', '#548235', '#BF8F00', '#C00000', '#7030A0', '#2E75B6',
  '#ED7D31', '#70AD47', '#FFC000', '#5B9BD5',
]

export function defaultGanttPayload(): GanttPayload {
  return {
    title: '项目甘特图',
    months: Array.from({ length: 12 }, (_, i) => `${i + 1}月`),
    phases: [
      {
        name: '阶段一：需求分析',
        color: '#4472C4',
        startMonth: 1,
        duration: 2,
        tasks: [
          { name: '需求调研', startMonth: 1, duration: 1.5 },
          { name: '需求文档编写', startMonth: 1.5, duration: 1.5 },
        ],
      },
    ],
  }
}

export function exampleGanttPayload(): GanttPayload {
  return {
    title: '12个月实施里程碑',
    months: Array.from({ length: 12 }, (_, i) => `${i + 1}月`),
    phases: [
      {
        name: '阶段一：需求调研与原型设计',
        color: '#4472C4',
        startMonth: 1,
        duration: 2,
        tasks: [
          { name: '行业市场调研与用户访谈', startMonth: 1, duration: 1.5 },
          { name: '竞品分析与场景聚焦', startMonth: 1.1, duration: 1.4 },
          { name: '项目立项与团队组建', startMonth: 1.5, duration: 1.25 },
          { name: '需求文档与功能规划', startMonth: 1.9, duration: 1.1 },
          { name: '交互原型设计与评审', startMonth: 2.15, duration: 1.1 },
        ],
      },
      {
        name: '阶段二：MVP核心功能开发',
        color: '#548235',
        startMonth: 3,
        duration: 2,
        tasks: [
          { name: 'AI人物替换引擎开发', startMonth: 3, duration: 1.7 },
          { name: '固定景别视频合成模块', startMonth: 3.2, duration: 1.5 },
          { name: 'AI配音与语音合成集成', startMonth: 3.6, duration: 1.3 },
          { name: '字幕自动生成与导出', startMonth: 4, duration: 1 },
          { name: 'MVP内部测试与Bug修复', startMonth: 4.3, duration: 0.9 },
        ],
      },
      {
        name: '阶段三：平台功能扩展',
        color: '#BF8F00',
        startMonth: 5,
        duration: 2,
        tasks: [
          { name: '批量视频模板引擎开发', startMonth: 5, duration: 1.6 },
          { name: '素材库搭建与管理后台', startMonth: 5.25, duration: 1.4 },
          { name: '多人协作与权限系统', startMonth: 5.6, duration: 1.2 },
          { name: '内容审核与合规模块', startMonth: 5.9, duration: 1.1 },
        ],
      },
      {
        name: '阶段四：客户试点与验证',
        color: '#C00000',
        startMonth: 7,
        duration: 2,
        tasks: [
          { name: '样板客户筛选与对接', startMonth: 7, duration: 1.4 },
          { name: '客户定制化部署与培训', startMonth: 7.3, duration: 1.4 },
          { name: '使用效果数据采集与分析', startMonth: 7.7, duration: 1.25 },
          { name: '付费意愿调研与定价测试', startMonth: 8, duration: 1 },
        ],
      },
      {
        name: '阶段五：产品迭代与商业化',
        color: '#7030A0',
        startMonth: 9,
        duration: 2,
        tasks: [
          { name: '基于反馈的功能迭代优化', startMonth: 9, duration: 1.6 },
          { name: 'SaaS多租户架构改造', startMonth: 9.3, duration: 1.4 },
          { name: '在线演示版本搭建', startMonth: 9.8, duration: 1.1 },
          { name: '企业级项目方案编制', startMonth: 10.2, duration: 0.9 },
        ],
      },
      {
        name: '阶段六：总结复盘与规划',
        color: '#2E75B6',
        startMonth: 11,
        duration: 2,
        tasks: [
          { name: '答辩材料与PPT制作', startMonth: 11, duration: 1.5 },
          { name: '客户案例集整理与包装', startMonth: 11.3, duration: 1.4 },
          { name: '财务数据复盘与ROI分析', startMonth: 11.7, duration: 1.2 },
          { name: '后续创业计划与融资方案', startMonth: 12, duration: 1.1 },
        ],
      },
    ],
  }
}

function normTask(t: any): GanttTask {
  return {
    name: String(t?.name ?? ''),
    startMonth: Number(t?.startMonth) || 1,
    duration: Number(t?.duration) || 1,
  }
}

function normPhase(p: any, idx: number): GanttPhase {
  const tasks = Array.isArray(p?.tasks) ? p.tasks.map(normTask) : []
  return {
    name: String(p?.name ?? `阶段${idx + 1}`),
    color: String(p?.color ?? DEFAULT_PHASE_COLORS[idx % DEFAULT_PHASE_COLORS.length]),
    startMonth: Number(p?.startMonth) || 1,
    duration: Number(p?.duration) || 2,
    tasks,
  }
}

export function coerceGanttPayload(raw: Record<string, any> | null | undefined): GanttPayload {
  const base = defaultGanttPayload()
  if (!raw || typeof raw !== 'object') return base

  const months = Array.isArray(raw.months) && raw.months.length > 0
    ? raw.months.map((m: any) => String(m))
    : base.months

  const phases = Array.isArray(raw.phases) && raw.phases.length > 0
    ? raw.phases.map((p: any, i: number) => normPhase(p, i))
    : base.phases.map((p, i) => normPhase(p, i))

  return {
    title: raw.title != null && String(raw.title).trim() !== '' ? String(raw.title) : base.title,
    months,
    phases,
  }
}

function escapeXml(s: string): string {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(hex)
  if (!m) return null
  return { r: parseInt(m[1], 16), g: parseInt(m[2], 16), b: parseInt(m[3], 16) }
}

function darkenHex(hex: string, amount = 0.2): string {
  const rgb = hexToRgb(hex)
  if (!rgb) return hex
  const r = Math.round(rgb.r * (1 - amount))
  const g = Math.round(rgb.g * (1 - amount))
  const b = Math.round(rgb.b * (1 - amount))
  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`
}

function lightenHex(hex: string, amount = 0.7): string {
  const rgb = hexToRgb(hex)
  if (!rgb) return hex
  const r = Math.round(rgb.r + (255 - rgb.r) * amount)
  const g = Math.round(rgb.g + (255 - rgb.g) * amount)
  const b = Math.round(rgb.b + (255 - rgb.b) * amount)
  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`
}

export function buildGanttMxGraphXml(payload: GanttPayload): string {
  const cells: string[] = []
  let nid = 2
  const pid = () => String(nid++)

  cells.push('<mxCell id="0"/>')
  cells.push('<mxCell id="1" parent="0"/>')

  const TASK_COL_W = 260
  const MONTH_COL_W = 100
  const HEADER_H = 52
  const PHASE_ROW_H = 42
  const TASK_ROW_H = 36
  const TITLE_H = 56
  const monthCount = payload.months.length

  const totalW = TASK_COL_W + monthCount * MONTH_COL_W
  let totalRows = 0
  for (const phase of payload.phases) {
    totalRows += 1 + phase.tasks.length
  }
  const totalH = TITLE_H + HEADER_H + totalRows * TASK_ROW_H + (payload.phases.length * (PHASE_ROW_H - TASK_ROW_H))

  const groupId = pid()
  cells.push(
    `<mxCell id="${groupId}" value="" style="group;fontSize=14;fillColor=#f5f5f5;fontColor=#333333;strokeColor=#666666;" connectable="0" vertex="1" parent="1"><mxGeometry x="0" y="0" width="${totalW}" height="${totalH}" as="geometry"/></mxCell>`
  )

  // Title
  const titleId = pid()
  cells.push(
    `<mxCell id="${titleId}" value="${escapeXml(payload.title)}" style="text;html=1;fontSize=28;fontStyle=1;align=center;verticalAlign=middle;fillColor=none;strokeColor=none;fontColor=#333333;" vertex="1" parent="${groupId}"><mxGeometry x="0" y="0" width="${totalW}" height="${TITLE_H}" as="geometry"/></mxCell>`
  )

  // Header: task column
  const hdrTaskId = pid()
  cells.push(
    `<mxCell id="${hdrTaskId}" value="${escapeXml('阶段 / 任务')}" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#4a4a4a;strokeColor=#333333;fontColor=#FFFFFF;fontStyle=1;fontSize=14;align=center;" vertex="1" parent="${groupId}"><mxGeometry x="0" y="${TITLE_H}" width="${TASK_COL_W}" height="${HEADER_H}" as="geometry"/></mxCell>`
  )

  // Header: month columns
  for (let i = 0; i < monthCount; i++) {
    const mId = pid()
    const x = TASK_COL_W + i * MONTH_COL_W
    cells.push(
      `<mxCell id="${mId}" value="${escapeXml(payload.months[i])}" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#4a4a4a;strokeColor=#333333;fontColor=#FFFFFF;fontStyle=1;fontSize=14;align=center;" vertex="1" parent="${groupId}"><mxGeometry x="${x}" y="${TITLE_H}" width="${MONTH_COL_W}" height="${HEADER_H}" as="geometry"/></mxCell>`
    )
  }

  // Grid lines (dashed vertical lines)
  const gridTop = TITLE_H + HEADER_H
  for (let i = 1; i < monthCount; i++) {
    const gx = TASK_COL_W + i * MONTH_COL_W
    const glId = pid()
    cells.push(
      `<mxCell id="${glId}" value="" style="endArrow=none;dashed=1;strokeColor=#CCCCCC;dashPattern=4 4;fontSize=14;" edge="1" parent="${groupId}"><mxGeometry relative="1" as="geometry"><mxPoint x="${gx}" y="${gridTop}" as="sourcePoint"/><mxPoint x="${gx}" y="${totalH}" as="targetPoint"/></mxGeometry></mxCell>`
    )
  }

  let curY = TITLE_H + HEADER_H

  for (const phase of payload.phases) {
    const strokeColor = darkenHex(phase.color)
    const taskBarFill = lightenHex(phase.color, 0.75)
    const taskBarStroke = lightenHex(phase.color, 0.3)

    // Phase header row
    const phId = pid()
    cells.push(
      `<mxCell id="${phId}" value="${escapeXml(phase.name)}" style="rounded=0;whiteSpace=wrap;html=1;fillColor=${phase.color};strokeColor=${strokeColor};fontColor=#FFFFFF;fontStyle=1;fontSize=14;align=left;spacingLeft=10;" vertex="1" parent="${groupId}"><mxGeometry x="0" y="${curY}" width="${TASK_COL_W}" height="${PHASE_ROW_H}" as="geometry"/></mxCell>`
    )

    // Phase bar
    const barX = TASK_COL_W + (phase.startMonth - 1) * MONTH_COL_W
    const barW = phase.duration * MONTH_COL_W
    const pbId = pid()
    cells.push(
      `<mxCell id="${pbId}" value="" style="rounded=1;whiteSpace=wrap;html=1;fillColor=${phase.color};strokeColor=${strokeColor};opacity=40;fontSize=14;" vertex="1" parent="${groupId}"><mxGeometry x="${barX}" y="${curY}" width="${barW}" height="${PHASE_ROW_H}" as="geometry"/></mxCell>`
    )

    curY += PHASE_ROW_H

    // Tasks
    phase.tasks.forEach((task, ti) => {
      const isOdd = ti % 2 === 0
      const rowBg = isOdd ? '#F2F2F2' : '#FFFFFF'

      // Task label cell
      const tlId = pid()
      cells.push(
        `<mxCell id="${tlId}" value="${escapeXml(task.name)}" style="rounded=0;whiteSpace=wrap;html=1;fillColor=${rowBg};strokeColor=#D9D9D9;fontSize=14;align=left;spacingLeft=10;" vertex="1" parent="${groupId}"><mxGeometry x="0" y="${curY}" width="${TASK_COL_W}" height="${TASK_ROW_H}" as="geometry"/></mxCell>`
      )

      // Task bar
      const tbX = TASK_COL_W + (task.startMonth - 1) * MONTH_COL_W
      const tbW = task.duration * MONTH_COL_W
      const tbId = pid()
      cells.push(
        `<mxCell id="${tbId}" value="" style="rounded=1;whiteSpace=wrap;html=1;fillColor=${taskBarFill};strokeColor=${taskBarStroke};fontSize=14;fontColor=#333333;" vertex="1" parent="${groupId}"><mxGeometry x="${tbX}" y="${curY + 3}" width="${tbW}" height="${TASK_ROW_H - 6}" as="geometry"/></mxCell>`
      )

      curY += TASK_ROW_H
    })
  }

  const xmlInner = cells.join('')
  const pageW = Math.ceil(totalW + 40)
  const pageH = Math.ceil(totalH + 40)
  const graph = `<mxGraphModel dx="${Math.max(2000, pageW)}" dy="${Math.max(1500, pageH)}" grid="0" gridSize="10" guides="0" tooltips="1" connect="1" arrows="1" fold="1" page="0" pageScale="1" pageWidth="${pageW}" pageHeight="${pageH}" math="0" shadow="0"><root>${xmlInner}</root></mxGraphModel>`
  return `<mxfile host="embed.diagrams.net"><diagram id="gantt" name="甘特图">${graph}</diagram></mxfile>`
}
