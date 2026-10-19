/**
 * 结构化工艺程序图 → Draw.io (mxGraphModel) XML
 * 版式贴近 IE 惯例：左时间、形内序号、右说明；○ 加工 □ 检验；侧分支直角汇入主干。
 */

export type OpProcStepKind = 'operation' | 'inspection'

export interface OpProcStep {
  kind: OpProcStepKind
  /** 填在图形内的序号（可与主干顺序不一致） */
  badge: string
  timeMin: number
  label: string
}

export interface OpProcBranch {
  title: string
  materialLine: string
  steps: OpProcStep[]
  /** 汇入主干时在汇总线上标注的文字，如 —花梳完成— */
  mergeLabel: string
  /**
   * 汇入发生在主干步骤索引 `mergeAfterMainIndex` 与下一步之间（0 起算）。
   * 例：在上轴（主干第 5 条、索引 4）与穿纱（索引 5）之间汇入 → 填 4。
   */
  mergeAfterMainIndex: number
  column: 'left' | 'middle'
}

export interface OpProcSummaryRow {
  /** 汇总表「内容」列，如 加工、检验或自定义项 */
  label: string
  count: number
  time: number
}

export interface OpProcPayload {
  header: {
    productName: string
    department: string
    researcher: string
    date: string
  }
  /** 汇总表各行（可多于加工/检验两行） */
  summaryRows: OpProcSummaryRow[]
  mainTitle: string
  mainMaterialLine: string
  mainSteps: OpProcStep[]
  branches: OpProcBranch[]
}

/** 兼容旧版 summary 对象或新版 summaryRows */
export function normalizeSummaryRowsFromPayload(raw: Record<string, any> | null | undefined): OpProcSummaryRow[] {
  if (!raw || typeof raw !== 'object') {
    return [
      { label: '加工', count: 0, time: 0 },
      { label: '检验', count: 0, time: 0 },
    ]
  }
  if (Array.isArray(raw.summaryRows) && raw.summaryRows.length > 0) {
    return raw.summaryRows.map((r: Record<string, unknown>) => ({
      label: String(r.label ?? ''),
      count: Number(r.count) || 0,
      time: Number(r.time) || 0,
    }))
  }
  const s = raw.summary
  if (s && typeof s === 'object') {
    return [
      { label: '加工', count: Number((s as any).processingCount) || 0, time: Number((s as any).processingTime) || 0 },
      { label: '检验', count: Number((s as any).inspectionCount) || 0, time: Number((s as any).inspectionTime) || 0 },
    ]
  }
  return [
    { label: '加工', count: 0, time: 0 },
    { label: '检验', count: 0, time: 0 },
  ]
}

/** AI / 表单合并：缺字段时用默认值，规整 kind / 数字类型 */
export function coerceOperationProcessPayload(raw: Record<string, any> | null | undefined): OpProcPayload {
  const base = defaultOperationProcessPayload()
  if (!raw || typeof raw !== 'object') return base

  function normStep(s: any): OpProcStep {
    const kind = s?.kind === 'inspection' ? 'inspection' : 'operation'
    return {
      kind,
      badge: String(s?.badge ?? ''),
      timeMin: Number(s?.timeMin) || 0,
      label: String(s?.label ?? ''),
    }
  }

  const mainSteps =
    Array.isArray(raw.mainSteps) && raw.mainSteps.length > 0
      ? raw.mainSteps.map(normStep)
      : base.mainSteps.map((s) => ({ ...s }))

  const branches: OpProcBranch[] = Array.isArray(raw.branches)
    ? raw.branches.map((b: any) => ({
        title: String(b?.title ?? ''),
        materialLine: String(b?.materialLine ?? ''),
        mergeLabel: String(b?.mergeLabel ?? ''),
        mergeAfterMainIndex: Math.max(0, Number(b?.mergeAfterMainIndex) || 0),
        column: b?.column === 'middle' ? 'middle' : 'left',
        steps: Array.isArray(b?.steps) ? b.steps.map(normStep) : [],
      }))
    : []

  return {
    header: { ...base.header, ...(raw.header || {}) },
    summaryRows: normalizeSummaryRowsFromPayload(raw),
    mainTitle:
      raw.mainTitle != null && String(raw.mainTitle).trim() !== '' ? String(raw.mainTitle) : base.mainTitle,
    mainMaterialLine:
      raw.mainMaterialLine != null && String(raw.mainMaterialLine).trim() !== ''
        ? String(raw.mainMaterialLine)
        : base.mainMaterialLine,
    mainSteps,
    branches,
  }
}

export function defaultOperationProcessPayload(): OpProcPayload {
  return {
    header: {
      productName: '',
      department: '',
      researcher: '',
      date: '',
    },
    summaryRows: [
      { label: '加工', count: 0, time: 0 },
      { label: '检验', count: 0, time: 0 },
    ],
    mainTitle: '整经准备',
    mainMaterialLine: '—整经纱线原料—',
    mainSteps: [
      { kind: 'operation', badge: '1', timeMin: 0, label: '' },
      { kind: 'inspection', badge: '1', timeMin: 0, label: '' },
    ],
    branches: [],
  }
}

export function exampleOperationProcessPayload(): OpProcPayload {
  return {
    header: {
      productName: 'S08451A18H',
      department: '生产部',
      researcher: '',
      date: '2025.3.3-2025.3.6',
    },
    summaryRows: [
      { label: '加工', count: 10, time: 547 },
      { label: '检验', count: 2, time: 3706 },
    ],
    mainTitle: '整经准备',
    mainMaterialLine: '—整经纱线原料—',
    mainSteps: [
      { kind: 'operation', badge: '1', timeMin: 156, label: '整经换模' },
      { kind: 'inspection', badge: '1', timeMin: 126, label: '整经开机维护' },
      { kind: 'operation', badge: '2', timeMin: 45, label: '拉盘头' },
      { kind: 'operation', badge: '3', timeMin: 33, label: '下轴' },
      { kind: 'operation', badge: '4', timeMin: 69, label: '上轴' },
      { kind: 'operation', badge: '5', timeMin: 76, label: '穿纱' },
      { kind: 'operation', badge: '10', timeMin: 35, label: '调机' },
      { kind: 'inspection', badge: '2', timeMin: 3580, label: '经编开机维护' },
    ],
    branches: [
      {
        title: '花梳准备',
        materialLine: '—花梳纱线原料—',
        steps: [
          { kind: 'operation', badge: '8', timeMin: 17, label: '花梳换纱' },
          { kind: 'operation', badge: '9', timeMin: 19, label: '花梳穿纱' },
        ],
        mergeLabel: '—花梳完成—',
        mergeAfterMainIndex: 4,
        column: 'left',
      },
      {
        title: '纱架准备',
        materialLine: '—纱架纱线原料—',
        steps: [
          { kind: 'operation', badge: '6', timeMin: 47, label: '纱架换纱' },
          { kind: 'operation', badge: '7', timeMin: 50, label: '纱架穿纱' },
        ],
        mergeLabel: '—纱架完成—',
        mergeAfterMainIndex: 4,
        column: 'middle',
      },
    ],
  }
}

function escapeXml(s: string): string {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

interface PlacedNode {
  shapeId: string
  cx: number
  cy: number
  top: number
  bottom: number
}

const EDGE_STYLE =
  'edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#000000;endArrow=classicThin;endFill=1;'

export function buildOperationProcessMxGraphXml(payload: OpProcPayload): string {
  const cells: string[] = []
  let nid = 2
  const pid = () => String(nid++)

  cells.push('<mxCell id="0"/>')
  cells.push('<mxCell id="1" parent="0"/>')

  const activeBranchCount = payload.branches.filter(b => b.steps.length > 0).length
  const COL_GAP_DIO = Math.max(180, 220 - (activeBranchCount - 1) * 10)
  const LEFT_MARGIN_DIO = 60
  const MAIN_X = LEFT_MARGIN_DIO + activeBranchCount * COL_GAP_DIO + (activeBranchCount > 0 ? 100 : 160)

  const FRAME_X = 10
  const FRAME_Y = 4
  const CONTENT_RIGHT = MAIN_X + 30 + 120 + 10
  const FRAME_W = Math.max(CONTENT_RIGHT - FRAME_X, 600)
  const frameId = pid()
  const frameIdx = cells.length
  cells.push('')

  const h = payload.header
  const summaryRows = normalizeSummaryRowsFromPayload(payload as unknown as Record<string, any>)
  const totalCount = summaryRows.reduce((a, r) => a + r.count, 0)
  const totalTime = summaryRows.reduce((a, r) => a + r.time, 0)

  // --- Title ---
  const TITLE_X = FRAME_X
  const TITLE_Y = FRAME_Y + 4
  const TITLE_W = FRAME_W
  const titleId = pid()
  cells.push(
    `<mxCell id="${titleId}" value="${escapeXml('工艺程序图')}" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;fontSize=16;fontStyle=1;" vertex="1" parent="1"><mxGeometry x="${TITLE_X}" y="${TITLE_Y}" width="${TITLE_W}" height="32" as="geometry"/></mxCell>`
  )

  // --- Header table using individual cells ---
  const HX = FRAME_X
  const HY = TITLE_Y + 36
  const LEFT_W = Math.round(FRAME_W * 0.58)
  const RIGHT_W = FRAME_W - LEFT_W
  const ROW_H = 28
  const dataRows = summaryRows.length + 1
  const HEADER_ROWS = Math.max(4, dataRows)
  const headerH = ROW_H * HEADER_ROWS

  const cellStyle = 'rounded=0;whiteSpace=wrap;html=1;fontSize=11;strokeColor=#94a3b8;'
  const labelStyle = cellStyle + 'fillColor=#f8fafc;fontStyle=1;align=left;spacingLeft=8;'
  const valueStyle = cellStyle + 'fillColor=#ffffff;align=left;spacingLeft=10;'
  const thStyle = cellStyle + 'fillColor=#f1f5f9;fontStyle=1;align=center;'
  const tdStyle = cellStyle + 'fillColor=#ffffff;align=center;'
  const tdBoldStyle = cellStyle + 'fillColor=#f1f5f9;fontStyle=1;align=center;'

  const infoLabels = ['制品名称：', '工作部门：', '研究者：', '日期：']
  const infoValues = [h.productName, h.department, h.researcher || '—', h.date]
  const LABEL_W = 88
  const VAL_W = LEFT_W - LABEL_W

  for (let i = 0; i < 4; i++) {
    const ry = HY + i * ROW_H
    const lId = pid()
    cells.push(`<mxCell id="${lId}" value="${escapeXml(infoLabels[i])}" style="${labelStyle}" vertex="1" parent="1"><mxGeometry x="${HX}" y="${ry}" width="${LABEL_W}" height="${ROW_H}" as="geometry"/></mxCell>`)
    const vId = pid()
    cells.push(`<mxCell id="${vId}" value="${escapeXml(infoValues[i])}" style="${valueStyle}" vertex="1" parent="1"><mxGeometry x="${HX + LABEL_W}" y="${ry}" width="${VAL_W}" height="${ROW_H}" as="geometry"/></mxCell>`)
  }

  const RX = HX + LEFT_W
  const COL_W1 = Math.round(RIGHT_W * 0.4)
  const COL_W2 = Math.round(RIGHT_W * 0.3)
  const COL_W3 = RIGHT_W - COL_W1 - COL_W2

  const thLabels = ['内容', '次数', '时间']
  const thWidths = [COL_W1, COL_W2, COL_W3]
  let rx = RX
  for (let c = 0; c < 3; c++) {
    const tId = pid()
    cells.push(`<mxCell id="${tId}" value="${escapeXml(thLabels[c])}" style="${thStyle}" vertex="1" parent="1"><mxGeometry x="${rx}" y="${HY}" width="${thWidths[c]}" height="${ROW_H}" as="geometry"/></mxCell>`)
    rx += thWidths[c]
  }

  for (let i = 0; i < summaryRows.length; i++) {
    const ry = HY + (i + 1) * ROW_H
    const r = summaryRows[i]
    const vals = [r.label, String(r.count), String(r.time)]
    let cx = RX
    for (let c = 0; c < 3; c++) {
      const cId = pid()
      cells.push(`<mxCell id="${cId}" value="${escapeXml(vals[c])}" style="${tdStyle}" vertex="1" parent="1"><mxGeometry x="${cx}" y="${ry}" width="${thWidths[c]}" height="${ROW_H}" as="geometry"/></mxCell>`)
      cx += thWidths[c]
    }
  }

  const totalRy = HY + (summaryRows.length + 1) * ROW_H
  const totalVals = ['总和', String(totalCount), String(totalTime)]
  let tx = RX
  for (let c = 0; c < 3; c++) {
    const tId = pid()
    cells.push(`<mxCell id="${tId}" value="${escapeXml(totalVals[c])}" style="${tdBoldStyle}" vertex="1" parent="1"><mxGeometry x="${tx}" y="${totalRy}" width="${thWidths[c]}" height="${ROW_H}" as="geometry"/></mxCell>`)
    tx += thWidths[c]
  }

  const HEADER_BOTTOM = HY + headerH
  const DIAGRAM_TOP = HEADER_BOTTOM + 24
  const STEP_PITCH = 88
  const NODE_OP = 58
  const NODE_IN = 52

  function placeStep(cx: number, step: OpProcStep, cy: number): PlacedNode {
    const isOp = step.kind === 'operation'
    const w = isOp ? NODE_OP : NODE_IN
    const hgt = isOp ? NODE_OP : NODE_IN
    const x = cx - w / 2
    const y = cy - hgt / 2
    const sid = pid()
    const st = isOp
      ? `ellipse;whiteSpace=wrap;html=1;aspect=fixed;fillColor=#ffffff;strokeColor=#000000;fontStyle=1;fontSize=13;`
      : `rounded=0;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#000000;fontStyle=1;fontSize=13;`
    cells.push(
      `<mxCell id="${sid}" value="${escapeXml(step.badge)}" style="${st}" vertex="1" parent="1"><mxGeometry x="${x}" y="${y}" width="${w}" height="${hgt}" as="geometry"/></mxCell>`
    )

    const tid = pid()
    cells.push(
      `<mxCell id="${tid}" value="${escapeXml(String(step.timeMin) + 'min')}" style="text;html=1;strokeColor=none;fillColor=none;align=right;verticalAlign=middle;fontSize=11;" vertex="1" parent="1"><mxGeometry x="${cx - w / 2 - 58}" y="${y + hgt / 2 - 11}" width="52" height="22" as="geometry"/></mxCell>`
    )

    const lid = pid()
    cells.push(
      `<mxCell id="${lid}" value="${escapeXml(step.label)}" style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontSize=11;" vertex="1" parent="1"><mxGeometry x="${cx + w / 2 + 6}" y="${y + hgt / 2 - 11}" width="120" height="22" as="geometry"/></mxCell>`
    )

    return { shapeId: sid, cx, cy, top: y, bottom: y + hgt }
  }

  function branchBanner(
    cx: number,
    yTop: number,
    title: string,
    material: string
  ): { nextY: number; titleId: string; materialId: string; anchorId: string; hasMaterial: boolean } {
    const titleId = pid()
    if (title) {
      cells.push(
        `<mxCell id="${titleId}" value="${escapeXml(title)}" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#000000;fontSize=11;fontStyle=1" vertex="1" parent="1"><mxGeometry x="${cx - 78}" y="${yTop}" width="156" height="28" as="geometry"/></mxCell>`
      )
    }
    const materialId = pid()
    let anchorId = ''
    if (material) {
      const matY = yTop + 50
      const dashId = pid()
      cells.push(
        `<mxCell id="${dashId}" value="" style="endArrow=none;dashed=1;dashPattern=8 4;html=1;strokeColor=#000000;rounded=0;" edge="1" parent="1"><mxGeometry relative="1" as="geometry"><mxPoint x="${cx - 80}" y="${matY}" as="sourcePoint"/><mxPoint x="${cx}" y="${matY}" as="targetPoint"/></mxGeometry></mxCell>`
      )
      cells.push(
        `<mxCell id="${materialId}" value="${escapeXml(material)}" style="text;html=1;strokeColor=none;fillColor=none;align=center;fontSize=10;" vertex="1" parent="1"><mxGeometry x="${cx - 120}" y="${matY - 18}" width="160" height="16" as="geometry"/></mxCell>`
      )
      anchorId = pid()
      cells.push(
        `<mxCell id="${anchorId}" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=none;strokeColor=none;" vertex="1" parent="1"><mxGeometry x="${cx - 1}" y="${matY - 1}" width="2" height="2" as="geometry"/></mxCell>`
      )
    }
    return { nextY: yTop + 80, titleId, materialId, anchorId, hasMaterial: !!material }
  }

  function colX(c: 'left' | 'middle'): number {
    return c === 'left' ? LEFT_MARGIN_DIO + 80 : LEFT_MARGIN_DIO + COL_GAP_DIO + 80
  }

  // Build a map of branch index → dynamic X position
  let brDioIdx = 0
  const branchXMap = new Map<number, number>()
  for (let i = 0; i < payload.branches.length; i++) {
    if (payload.branches[i].steps.length > 0) {
      branchXMap.set(i, LEFT_MARGIN_DIO + brDioIdx * COL_GAP_DIO + 80)
      brDioIdx++
    }
  }

  const MERGE_GAP = 44
  const mergeSet = new Set<number>()
  const activeBranches = payload.branches.filter((b) => b.steps.length > 0)
  for (const br of activeBranches) {
    mergeSet.add(Math.max(0, Math.min(br.mergeAfterMainIndex, payload.mainSteps.length - 2)))
  }

  // —— 主干 ——
  let mainY = DIAGRAM_TOP
  const mainBanner = branchBanner(MAIN_X, mainY, payload.mainTitle, payload.mainMaterialLine)
  mainY = mainBanner.nextY
  let cy = mainY + 32
  const mainNodes: PlacedNode[] = []
  const mainEdges: { from: string; to: string }[] = []
  for (let i = 0; i < payload.mainSteps.length; i++) {
    const st = payload.mainSteps[i]
    const n = placeStep(MAIN_X, st, cy)
    mainNodes.push(n)
    if (i === 0) {
      if (mainBanner.hasMaterial) {
        const eDrop = pid()
        cells.push(
          `<mxCell id="${eDrop}" style="${EDGE_STYLE}" edge="1" parent="1" source="${mainBanner.anchorId}" target="${n.shapeId}"><mxGeometry relative="1" as="geometry"/></mxCell>`
        )
      }
    } else {
      mainEdges.push({ from: mainNodes[i - 1].shapeId, to: n.shapeId })
    }
    cy += STEP_PITCH
    if (mergeSet.has(i)) cy += MERGE_GAP
  }

  for (const e of mainEdges) {
    const eid = pid()
    cells.push(
      `<mxCell id="${eid}" style="${EDGE_STYLE}" edge="1" parent="1" source="${e.from}" target="${e.to}"><mxGeometry relative="1" as="geometry"/></mxCell>`
    )
  }

  // —— 侧分支 + 汇入 ——
  function mergeY(mainIdx: number): number {
    if (mainNodes.length === 0) return DIAGRAM_TOP + 200
    const lo = Math.min(mainIdx, mainNodes.length - 1)
    const hi = lo + 1
    if (hi >= mainNodes.length) return mainNodes[lo].bottom + 24
    return (mainNodes[lo].bottom + mainNodes[hi].top) / 2
  }

  const mergeGroups = new Map<number, { br: OpProcBranch; origIdx: number }[]>()
  for (let i = 0; i < payload.branches.length; i++) {
    const br = payload.branches[i]
    if (br.steps.length === 0 || mainNodes.length < 2) continue
    const mi = Math.max(0, Math.min(br.mergeAfterMainIndex, mainNodes.length - 2))
    if (!mergeGroups.has(mi)) mergeGroups.set(mi, [])
    mergeGroups.get(mi)!.push({ br, origIdx: i })
  }

  const sortedMergeKeys = [...mergeGroups.keys()].sort((a, b) => a - b)
  for (const mi of sortedMergeKeys) {
    const group = mergeGroups.get(mi)!
    const baseMy = mergeY(mi)

    for (let rank = 0; rank < group.length; rank++) {
      const { br, origIdx } = group[rank]
      const my = baseMy

      const bx = branchXMap.get(origIdx) ?? colX(br.column)
      let by = DIAGRAM_TOP
      const bBanner = branchBanner(bx, by, br.title, br.materialLine)
      by = bBanner.nextY
      let bcy = by + 32
      const bnodes: PlacedNode[] = []
      for (let j = 0; j < br.steps.length; j++) {
        const n = placeStep(bx, br.steps[j], bcy)
        bnodes.push(n)
        if (j === 0) {
          if (bBanner.hasMaterial) {
            const eDrop = pid()
            cells.push(
              `<mxCell id="${eDrop}" style="${EDGE_STYLE}" edge="1" parent="1" source="${bBanner.anchorId}" target="${n.shapeId}"><mxGeometry relative="1" as="geometry"/></mxCell>`
            )
          }
        } else {
          const eid = pid()
          cells.push(
            `<mxCell id="${eid}" style="${EDGE_STYLE}" edge="1" parent="1" source="${bnodes[j - 1].shapeId}" target="${n.shapeId}"><mxGeometry relative="1" as="geometry"/></mxCell>`
          )
        }
        bcy += STEP_PITCH
      }

      const last = bnodes[bnodes.length - 1]

      // vertical line from last branch step to merge Y
      const vertEndId = pid()
      cells.push(
        `<mxCell id="${vertEndId}" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=none;strokeColor=none;" vertex="1" parent="1"><mxGeometry x="${bx - 2}" y="${my - 2}" width="4" height="4" as="geometry"/></mxCell>`
      )
      const eVert = pid()
      cells.push(
        `<mxCell id="${eVert}" style="${EDGE_STYLE}" edge="1" parent="1" source="${last.shapeId}" target="${vertEndId}"><mxGeometry relative="1" as="geometry"/></mxCell>`
      )

      // horizontal line from branch column to main spine at merge Y
      const hLineId = pid()
      cells.push(
        `<mxCell id="${hLineId}" value="" style="endArrow=none;html=1;strokeColor=#000000;rounded=0;" edge="1" parent="1"><mxGeometry relative="1" as="geometry"><mxPoint x="${bx}" y="${my}" as="sourcePoint"/><mxPoint x="${MAIN_X}" y="${my}" as="targetPoint"/></mxGeometry></mxCell>`
      )

      if (br.mergeLabel) {
        const mlId = pid()
        cells.push(
          `<mxCell id="${mlId}" value="${escapeXml(br.mergeLabel)}" style="text;html=1;strokeColor=none;fillColor=none;align=left;fontSize=10;fontStyle=2;" vertex="1" parent="1"><mxGeometry x="${bx + 4}" y="${my - 18}" width="120" height="16" as="geometry"/></mxCell>`
        )
      }
    }
  }

  // Calculate adaptive frame height from content
  let maxContentY = DIAGRAM_TOP + 100
  for (const n of mainNodes) {
    maxContentY = Math.max(maxContentY, n.bottom + 40)
  }
  for (const mi of sortedMergeKeys) {
    maxContentY = Math.max(maxContentY, mergeY(mi) + 40)
  }
  const FRAME_H = Math.max(400, maxContentY + 20)
  cells[frameIdx] = `<mxCell id="${frameId}" value="" style="rounded=1;arcSize=5;fillColor=#FFFFFF;strokeColor=#000000;strokeWidth=1;whiteSpace=wrap;html=1;" vertex="1" parent="1"><mxGeometry x="${FRAME_X}" y="${FRAME_Y}" width="${FRAME_W}" height="${FRAME_H}" as="geometry"/></mxCell>`

  const xmlInner = cells.join('')
  const pageW = Math.ceil(FRAME_W + FRAME_X * 2)
  const pageH = Math.ceil(FRAME_H + FRAME_Y * 2)
  const graph = `<mxGraphModel dx="1200" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="0" pageScale="1" pageWidth="${pageW}" pageHeight="${pageH}" math="0" shadow="0" background="#FFFFFF"><root>${xmlInner}</root></mxGraphModel>`
  return `<mxfile host="embed.diagrams.net"><diagram id="op-process" name="工艺程序图">${graph}</diagram></mxfile>`
}
