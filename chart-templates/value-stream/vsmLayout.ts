/**
 * 价值流程图 (VSM, Value Stream Mapping) — 共享布局引擎
 *
 * 标准线性 VSM：单条横向物料流。三大区域：
 *   信息流（上）：供应商 / 生产控制(MRP) / 客户 + 信息流箭头（电子/人工，分车道避免交叉）
 *   物料流（中）：工序框（左→右）+ 操作员圆圈 + 数据框(C/T,C/O,可用率,良品率) + 库存三角(I) + 推动箭头 + 卡车
 *   时间线（下）：阶梯双层（上=非增值库存天数、下=增值工序C/T）+ Takt + 交付周期/增值/PCE 汇总
 *
 * 本文件只算一次坐标，输出 VsmPrimitive[]；
 *   - ValueStreamForm.vue 把 primitive → SVG
 *   - buildMxGraphXml.ts  把 primitive → mxCell
 * 两边消费同一份坐标，预览与导出严格一致。
 */

// ---------------- 数据模型 ----------------

export type InvType = 'inventory' | 'supermarket' | 'fifo'
export type InfoType = 'electronic' | 'manual'

export interface VsmProcess {
  id: string
  name: string
  cycleTime: number // C/T 周期时间（秒/件）
  changeover: number // C/O 换模时间（分钟）
  operators: number // 操作员人数
  uptime: number // 设备可用率（%）
  firstYield: number // 良品率 F/Y（%，一次合格率）
  next?: string[] // 后继工序 id 列表（支持并联）；任一工序填了就按有向图布局，否则按数组顺序线性串联
}

/** afterIndex = -1 表示供应商之后（首个工序之前）；否则表示第 afterIndex 个工序之后 */
export interface VsmInventory {
  afterIndex: number
  qty: number // 平均库存量（件）
  days: number // 折算库存天数（天），用于时间线非增值段
  invType: InvType
}

/** id 取值：'supplier' | 'control' | 'customer' | 处理工序的 process.id */
export interface VsmInfoFlow {
  fromId: string
  toId: string
  label: string
  type: InfoType
}

/** afterIndex = -1 供应商后；否则第 afterIndex 个工序上方 */
export interface VsmKaizen {
  afterIndex: number
  label: string
}

export interface VsmPayload {
  title: string
  customer: {
    name: string
    dailyDemand: number // 日需求量（件/天）
    unit: string
    deliveryFreq: string // 发货频率，如 “每日1次”
    infoLabel: string // 生产控制↔客户 主干信息流标签（必备信息流），如 “月客户订单”
  }
  supplier: {
    name: string
    deliveryFreq: string // 送货频率，如 “每周2次”
    infoLabel: string // 生产控制↔供应商 主干信息流标签（必备信息流），如 “月采购订单”
  }
  control: { name: string } // 生产控制框，默认 “生产控制 / MRP”
  processes: VsmProcess[]
  inventories: VsmInventory[]
  infoFlows: VsmInfoFlow[]
  kaizens: VsmKaizen[]
  workingTimePerDay: number // 有效工作时间（秒/天），用于 Takt 计算
  showTakt: boolean
}

// ---------------- Primitive（布局产物） ----------------

export type BoxStyle =
  | 'process'
  | 'customer'
  | 'supplier'
  | 'control'
  | 'datatable'
  | 'taktbox'
  | 'summary'

export type VsmPrimitive =
  | { kind: 'box'; id: string; x: number; y: number; w: number; h: number; label: string; style: BoxStyle }
  | { kind: 'dataRows'; id: string; x: number; y: number; w: number; rowH: number; title: string; rows: [string, string][] }
  | { kind: 'operator'; id: string; x: number; y: number; count: number }
  | { kind: 'triangle'; id: string; x: number; y: number; qty: number; days: number; invType: InvType }
  | { kind: 'truck'; id: string; x: number; y: number; freq: string; dir: 'in' | 'out' }
  | { kind: 'kaizen'; id: string; x: number; y: number; label: string }
  | { kind: 'sawtooth'; id: string; x: number; y: number; segments: SawSeg[] }
  | { kind: 'text'; id: string; x: number; y: number; w: number; value: string; align?: 'left' | 'center' | 'right'; bold?: boolean; fontSize?: number }
  | { kind: 'edge'; id: string; flow: EdgeFlow; points: { x: number; y: number }[]; label?: string; labelPos?: { x: number; y: number } }

export type EdgeFlow = 'push' | 'pull' | 'manual-mat' | 'info-e' | 'info-m' | 'ship' | 'info-thick'
export interface SawSeg { w: number; high: boolean; label: string }

export interface VsmLayout {
  primitives: VsmPrimitive[]
  width: number
  height: number
}

// ---------------- 布局常量 ----------------

const FRAME_PAD = 24
export const PROC_W = 150
export const PROC_H = 54
const PROC_PITCH = 300 // 相邻工序中心间距（留足库存三角 + 推动箭头）
const MATERIAL_Y = 300 // 工序框顶部 Y
export const OP_R = 13 // 操作员圆圈半径
export const DATA_ROW_H = 22
export const TRI_HALF = 24 // 库存三角半宽（SVG/XML 共用）
const INFO_TOP = 56
const CONTROL_W = 180
const ENDBOX_W = 150
const ENDBOX_H = 64
export const TRUCK_W = 132 // 卡车宽（≈ 供应商框，体量更大）
export const TRUCK_H = 56 // 卡车高
const FIRST_PROC_CX = 480 // 首个工序中心 X（给左侧供应商 + 大卡车留位）

const C = {
  invName: { inventory: 'I', supermarket: '超市', fifo: 'FIFO' } as Record<InvType, string>,
}

function fmtMin(min: number): string {
  if (!min) return '0'
  if (min >= 60) {
    const h = Math.floor(min / 60)
    const m = min % 60
    return m ? `${h}h${m}min` : `${h}h`
  }
  return `${min}min`
}

/**
 * 电子信息流锯齿（闪电）折线：在 (x1,y)→(x2,y) 的水平段内生成对称锯齿，
 * 返回不含端点的中间锯齿点。这是 VSM「电子信息流」的专用符号。
 */
function lightning(x1: number, x2: number, y: number, amp = 6): { x: number; y: number }[] {
  const span = Math.abs(x2 - x1)
  if (span < 24) return []
  const dir = x2 >= x1 ? 1 : -1
  const teeth = Math.max(3, Math.round(span / 42))
  const step = span / teeth
  const pts: { x: number; y: number }[] = []
  for (let i = 1; i < teeth; i++) {
    pts.push({ x: x1 + dir * step * i, y: y + (i % 2 === 1 ? -amp : amp) })
  }
  return pts
}

// ---------------- 布局引擎 ----------------

export function computeVsmLayout(p: VsmPayload): VsmLayout {
  const prims: VsmPrimitive[] = []
  let uid = 0
  const nid = (prefix: string) => `${prefix}_${uid++}`

  const procCount = Math.max(p.processes.length, 1)
  // 改善闪电中心相对工序框顶的上移量（与下方 kaizen 绘制保持一致）
  const KAIZEN_LIFT = 64
  // 并联车道行距：容下「工序框 + 间隙 + 4 行数据框」整体后，再为工序上方的改善闪电留净空，
  // 否则下车道工序上方的闪电会压住上车道的数据框。
  const LANE_PITCH = PROC_H + 30 + DATA_ROW_H * 4 + KAIZEN_LIFT + 40

  // —— 有向图：任一工序填了 next 就按图布局；否则按数组顺序线性串联 ——
  const idToIdx = new Map(p.processes.map((pp, i) => [pp.id, i]))
  const hasGraph = p.processes.some((pp) => Array.isArray(pp.next) && pp.next.length > 0)
  const succ = new Map<string, string[]>()
  const pred = new Map<string, string[]>()
  p.processes.forEach((pp) => { succ.set(pp.id, []); pred.set(pp.id, []) })
  const link = (u: string, v: string) => { succ.get(u)!.push(v); pred.get(v)!.push(u) }
  if (hasGraph) {
    p.processes.forEach((pp) => {
      for (const nx of pp.next || []) if (idToIdx.has(nx) && nx !== pp.id) link(pp.id, nx)
    })
  } else {
    p.processes.forEach((pp, i) => { if (i < procCount - 1) link(pp.id, p.processes[i + 1].id) })
  }

  // 最长路径深度（列）。带访问保护，环退化为 0。
  const depthMemo = new Map<string, number>()
  const visiting = new Set<string>()
  const depthOf = (id: string): number => {
    if (depthMemo.has(id)) return depthMemo.get(id)!
    if (visiting.has(id)) return 0
    visiting.add(id)
    let d = 0
    for (const u of pred.get(id) || []) d = Math.max(d, depthOf(u) + 1)
    visiting.delete(id)
    depthMemo.set(id, d)
    return d
  }
  p.processes.forEach((pp) => depthOf(pp.id))
  const maxDepth = p.processes.reduce((m, pp) => Math.max(m, depthOf(pp.id)), 0)

  // 同列内按数组顺序分车道（向下生长，首车道对齐基线 MATERIAL_Y）
  const byDepth = new Map<number, string[]>()
  p.processes.forEach((pp) => {
    const d = depthOf(pp.id)
    if (!byDepth.has(d)) byDepth.set(d, [])
    byDepth.get(d)!.push(pp.id)
  })
  const laneOfId = new Map<string, number>()
  byDepth.forEach((ids) => ids.forEach((id, k) => laneOfId.set(id, k)))

  const colCx = (d: number) => FIRST_PROC_CX + d * PROC_PITCH
  const procCxId = (id: string) => colCx(depthOf(id))
  const procTopOf = (id: string) => MATERIAL_Y + (laneOfId.get(id) || 0) * LANE_PITCH
  const roots = p.processes.filter((pp) => (pred.get(pp.id) || []).length === 0).map((pp) => pp.id)
  const leaves = p.processes.filter((pp) => (succ.get(pp.id) || []).length === 0).map((pp) => pp.id)
  const lastCx = colCx(maxDepth)
  // 端框（供应商/客户）离最近工序的中心距离：留足 卡车 + 库存三角 + 间隙
  const END_OFFSET = 470
  const customerCx = lastCx + END_OFFSET
  const supplierCx = FIRST_PROC_CX - END_OFFSET
  const controlCx = (supplierCx + customerCx) / 2

  // 工序垂直分布范围（用于时间线下移）
  const maxLane = p.processes.reduce((m, pp) => Math.max(m, laneOfId.get(pp.id) || 0), 0)
  const procBandBottom = MATERIAL_Y + maxLane * LANE_PITCH + PROC_H
  const DATA_BLOCK_H = DATA_ROW_H * 4
  const TIMELINE_Y = procBandBottom + 30 + DATA_BLOCK_H + 100

  // 节点中心 X 映射（信息流连线用）
  const cxOf = new Map<string, number>()
  cxOf.set('supplier', supplierCx)
  cxOf.set('control', controlCx)
  cxOf.set('customer', customerCx)
  p.processes.forEach((proc) => cxOf.set(proc.id, procCxId(proc.id)))
  // 工序顶部 Y 映射（信息流/计划箭头落点用）
  const topOf = (id: string) => procTopOf(id)

  // ===== 信息流区（上）—— 供应商 / 生产控制 / 客户 三框水平对齐，文字居中 =====
  const controlY = INFO_TOP
  const supBox = { x: supplierCx - ENDBOX_W / 2, y: INFO_TOP, w: ENDBOX_W, h: ENDBOX_H }
  const cusBox = { x: customerCx - ENDBOX_W / 2, y: INFO_TOP, w: ENDBOX_W, h: ENDBOX_H }
  const ctlBox = { x: controlCx - CONTROL_W / 2, y: controlY, w: CONTROL_W, h: ENDBOX_H }
  prims.push({ kind: 'box', id: nid('supplier'), ...supBox, label: p.supplier.name || '供应商', style: 'supplier' })
  prims.push({ kind: 'box', id: nid('customer'), ...cusBox, label: p.customer.name || '客户', style: 'customer' })
  prims.push({ kind: 'box', id: nid('control'), ...ctlBox, label: p.control.name || '生产控制 / MRP', style: 'control' })
  const demandLines = [
    p.customer.dailyDemand ? `${p.customer.dailyDemand} ${p.customer.unit || '件'}/天` : '',
    p.customer.deliveryFreq || '',
  ].filter(Boolean).join('  ')
  // 供应商/客户的发货频率等文字：放到框的外侧（避开框底垂直连线），字号加大
  const SIDE_W = 132
  const sideY = INFO_TOP + ENDBOX_H / 2 - 9
  if (demandLines) prims.push({ kind: 'text', id: nid('custinfo'), x: cusBox.x + ENDBOX_W + 10, y: sideY, w: SIDE_W, value: demandLines, align: 'left', fontSize: 12 })
  if (p.supplier.deliveryFreq) prims.push({ kind: 'text', id: nid('supinfo'), x: supBox.x - SIDE_W - 10, y: sideY, w: SIDE_W, value: p.supplier.deliveryFreq, align: 'right', fontSize: 12 })

  const controlBottom = controlY + ENDBOX_H

  // —— 主干 1/2：生产控制 ↔ 供应商、生产控制 ↔ 客户（必备，始终绘制）——
  // VSM「电子信息流」专用符号：粗折线 + 水平段上的锯齿（闪电）。
  // 折线走框上方车道：控制框顶 → 上抬到车道 → 锯齿水平到端框正上方 → 下插入端框顶
  const infoLaneY = INFO_TOP - 30
  const supLaneX = controlCx - 36
  prims.push({
    kind: 'edge', id: nid('infobone'), flow: 'info-thick',
    points: [
      { x: supLaneX, y: INFO_TOP },
      { x: supLaneX, y: infoLaneY },
      ...lightning(supLaneX, supplierCx, infoLaneY),
      { x: supplierCx, y: infoLaneY },
      { x: supplierCx, y: supBox.y },
    ],
    label: p.supplier.infoLabel || '',
    labelPos: { x: (supLaneX + supplierCx) / 2, y: infoLaneY - 13 },
  })
  const cusLaneX = controlCx + 36
  prims.push({
    kind: 'edge', id: nid('infobone'), flow: 'info-thick',
    points: [
      { x: cusLaneX, y: INFO_TOP },
      { x: cusLaneX, y: infoLaneY },
      ...lightning(cusLaneX, customerCx, infoLaneY),
      { x: customerCx, y: infoLaneY },
      { x: customerCx, y: cusBox.y },
    ],
    label: p.customer.infoLabel || '',
    labelPos: { x: (cusLaneX + customerCx) / 2, y: infoLaneY - 13 },
  })

  // —— 生产控制 → 工序：计划下达箭头（用户在「信息流」表里选 到=任意工序，头恒为生产控制）——
  const procIds = new Set(p.processes.map((pp) => pp.id))
  for (const f of p.infoFlows) {
    if (!procIds.has(f.toId)) continue
    const tx = cxOf.get(f.toId)
    if (tx == null) continue
    prims.push({ kind: 'edge', id: nid('sched'), flow: 'info-thick', points: [{ x: controlCx, y: controlBottom }, { x: tx, y: topOf(f.toId) }], label: f.label })
  }

  // ===== 物料流区（中） =====
  p.processes.forEach((proc, i) => {
    const cx = procCxId(proc.id)
    const top = procTopOf(proc.id)
    const bx = cx - PROC_W / 2
    prims.push({ kind: 'box', id: nid('proc'), x: bx, y: top, w: PROC_W, h: PROC_H, label: proc.name || `工序${i + 1}`, style: 'process' })
    // 数据框（C/T, C/O, 可用率, 良品率）
    const rows: [string, string][] = [
      ['C/T', `${proc.cycleTime}s`],
      ['C/O', fmtMin(proc.changeover)],
      ['可用率', `${proc.uptime}%`],
      ['良品率', `${proc.firstYield}%`],
    ]
    prims.push({ kind: 'dataRows', id: nid('data'), x: bx, y: top + PROC_H + 30, w: PROC_W, rowH: DATA_ROW_H, title: '', rows })
  })

  // 供应商卡车（放大，体量≈供应商框）；紧贴供应商框右侧
  const truckCx = supplierCx + ENDBOX_W / 2 + 44 + TRUCK_W / 2
  // 客户卡车：紧贴客户框左侧（对称）
  const outTruckCx = customerCx - ENDBOX_W / 2 - 44 - TRUCK_W / 2
  const baseTriY = MATERIAL_Y + PROC_H / 2 // 首车道工序中线（供应商/客户侧三角、卡车用）
  prims.push({ kind: 'truck', id: nid('truck'), x: truckCx, y: baseTriY, freq: p.supplier.deliveryFreq || '', dir: 'in' })
  prims.push({ kind: 'truck', id: nid('truck'), x: outTruckCx, y: baseTriY, freq: p.customer.deliveryFreq || '', dir: 'out' })

  function placeInventory(inv: VsmInventory) {
    let triCx: number
    let triMidY = baseTriY
    if (inv.afterIndex < 0) {
      // 卡车右缘 与 首列工序左缘 之间居中
      triCx = (truckCx + TRUCK_W / 2 + colCx(0) - PROC_W / 2) / 2
    } else if (inv.afterIndex >= procCount - 1) {
      // 末列工序右缘 与 客户卡车左缘 之间居中
      triCx = (lastCx + PROC_W / 2 + outTruckCx - TRUCK_W / 2) / 2
    } else {
      const here = p.processes[inv.afterIndex]
      const dHere = depthOf(here.id)
      triCx = (colCx(dHere) + colCx(dHere + 1)) / 2
      triMidY = procTopOf(here.id) + PROC_H / 2
    }
    const triCenterY = triMidY - TRI_HALF - 4
    prims.push({ kind: 'triangle', id: nid('inv'), x: triCx, y: triCenterY, qty: inv.qty, days: inv.days, invType: inv.invType })
  }
  for (const inv of p.inventories) placeInventory(inv)

  // 工序间推动箭头（黑色折线箭头）：沿有向图每条边。
  // 跨车道时：源右缘短horizontal出框 → 紧贴源框右侧的垂直通道（落在列间隙、避开居中的库存三角）
  // → 垂直到目标车道中线 → 水平进入目标左缘。这样竖线不穿三角，仅保留「物料经库存三角流入工序」的常规水平段。
  let crossLane = 0
  for (const u of p.processes) {
    for (const v of succ.get(u.id) || []) {
      const ux = procCxId(u.id) + PROC_W / 2
      const uy = procTopOf(u.id) + PROC_H / 2
      const vx = procCxId(v) - PROC_W / 2
      const vy = procTopOf(v) + PROC_H / 2
      let pts: { x: number; y: number }[]
      if (uy === vy) {
        pts = [{ x: ux, y: uy }, { x: vx, y: vy }]
      } else {
        // 通道贴源框右侧 24px 起、按边序错位，确保落在「源框右缘」与「源下游库存三角左缘」之间
        const channelX = ux + 24 + (crossLane % 3) * 8
        crossLane++
        pts = [
          { x: ux, y: uy },
          { x: channelX, y: uy },
          { x: channelX, y: vy },
          { x: vx, y: vy },
        ]
      }
      prims.push({ kind: 'edge', id: nid('push'), flow: 'push', points: pts })
    }
  }
  // 供应商 → 卡车：从供应商框底部垂直下来，再水平连到卡车（垂直折线，连线不悬空）
  const supBottom = supBox.y + ENDBOX_H
  prims.push({ kind: 'edge', id: nid('matflow'), flow: 'manual-mat', points: [
    { x: supplierCx, y: supBottom },
    { x: supplierCx, y: baseTriY },
    { x: truckCx - TRUCK_W / 2, y: baseTriY },
  ] })
  // 卡车 → 各根工序（无前驱的起始工序）
  for (const r of roots) {
    const rx = procCxId(r) - PROC_W / 2
    const ry = procTopOf(r) + PROC_H / 2
    const pts = ry === baseTriY
      ? [{ x: truckCx + TRUCK_W / 2, y: baseTriY }, { x: rx, y: ry }]
      : [{ x: truckCx + TRUCK_W / 2, y: baseTriY }, { x: (truckCx + TRUCK_W / 2 + rx) / 2, y: baseTriY }, { x: (truckCx + TRUCK_W / 2 + rx) / 2, y: ry }, { x: rx, y: ry }]
    prims.push({ kind: 'edge', id: nid('matflow'), flow: 'manual-mat', points: pts })
  }
  // 各末工序（无后继）→ 客户卡车（发货）
  for (const lf of leaves) {
    const lx = procCxId(lf) + PROC_W / 2
    const ly = procTopOf(lf) + PROC_H / 2
    const pts = ly === baseTriY
      ? [{ x: lx, y: ly }, { x: outTruckCx - TRUCK_W / 2, y: baseTriY }]
      : [{ x: lx, y: ly }, { x: (lx + outTruckCx - TRUCK_W / 2) / 2, y: ly }, { x: (lx + outTruckCx - TRUCK_W / 2) / 2, y: baseTriY }, { x: outTruckCx - TRUCK_W / 2, y: baseTriY }]
    prims.push({ kind: 'edge', id: nid('ship'), flow: 'ship', points: pts })
  }
  // 客户卡车 → 客户：水平到客户正下方，再垂直上去（垂直折线）
  const cusBottom = cusBox.y + ENDBOX_H
  prims.push({ kind: 'edge', id: nid('ship'), flow: 'ship', points: [
    { x: outTruckCx + TRUCK_W / 2, y: baseTriY },
    { x: customerCx, y: baseTriY },
    { x: customerCx, y: cusBottom },
  ] })

  // 改善闪电：放在工序框正上方足够高处，闪爆全高（约 60）完整位于框顶之上，不遮挡白框/数据框
  for (const k of p.kaizens) {
    let kx: number
    let ky = MATERIAL_Y - KAIZEN_LIFT
    if (k.afterIndex < 0) kx = (supplierCx + colCx(0)) / 2
    else if (k.afterIndex >= procCount) kx = customerCx
    else {
      const here = p.processes[Math.min(k.afterIndex, procCount - 1)]
      kx = procCxId(here.id)
      ky = procTopOf(here.id) - KAIZEN_LIFT
    }
    prims.push({ kind: 'kaizen', id: nid('kaizen'), x: kx, y: ky, label: k.label })
  }

  // ===== 时间线区（下）——沿最长路径（关键路径）=====
  // 关键路径：最大化沿途 C/T 之和。DP（后继最大）+ 前向回溯。
  const vaTail = new Map<string, number>()
  const bestNext = new Map<string, string>()
  const orderByDepthDesc = [...p.processes].sort((a, b) => depthOf(b.id) - depthOf(a.id))
  for (const u of orderByDepthDesc) {
    let best = -1
    let bestId = ''
    for (const v of succ.get(u.id) || []) {
      const t = vaTail.get(v) ?? 0
      if (t > best) { best = t; bestId = v }
    }
    if (bestId) bestNext.set(u.id, bestId)
    vaTail.set(u.id, (u.cycleTime || 0) + (best < 0 ? 0 : best))
  }
  let head = ''
  let headVal = -1
  for (const r of roots) { const t = vaTail.get(r) ?? 0; if (t > headVal) { headVal = t; head = r } }
  const critPath: VsmProcess[] = []
  for (let cur = head; cur; cur = bestNext.get(cur) || '') {
    const proc = p.processes[idToIdx.get(cur)!]
    critPath.push(proc)
    if (!bestNext.has(cur)) break
  }
  buildTimeline(p, prims, nid, critPath, idToIdx, colCx, supplierCx, customerCx, TIMELINE_Y)

  // ===== 自适应画布尺寸 =====
  let maxX = customerCx + ENDBOX_W / 2
  let minX = supplierCx - ENDBOX_W / 2
  const maxY = TIMELINE_Y + 170
  for (const pr of prims) {
    if (pr.kind === 'box' || pr.kind === 'dataRows') maxX = Math.max(maxX, pr.x + pr.w)
    if (pr.kind === 'text') { maxX = Math.max(maxX, pr.x + pr.w); minX = Math.min(minX, pr.x) }
  }
  const width = Math.ceil(maxX - minX + FRAME_PAD * 2)
  const height = Math.ceil(maxY)

  // 整体右移，使最左元素留出边距
  const shift = FRAME_PAD - minX
  if (shift !== 0) {
    for (const pr of prims) {
      if ('x' in pr) pr.x += shift
      if (pr.kind === 'edge') {
        pr.points = pr.points.map((pt) => ({ x: pt.x + shift, y: pt.y }))
        if (pr.labelPos) pr.labelPos = { x: pr.labelPos.x + shift, y: pr.labelPos.y }
      }
    }
  }

  return { primitives: prims, width, height }
}

function buildTimeline(
  p: VsmPayload,
  prims: VsmPrimitive[],
  nid: (s: string) => string,
  critPath: VsmProcess[],
  idToIdx: Map<string, number>,
  colCx: (d: number) => number,
  supplierCx: number,
  customerCx: number,
  y: number,
): void {
  // 阶梯段：交替 非增值(库存天数,上) / 增值(工序C/T,下)，仅沿关键路径取段。
  // 增值段（low）宽度 = 工序框宽 PROC_W；库存段（high）宽度 = 列间隙。
  const GAP = PROC_PITCH - PROC_W // 相邻工序边缘间距
  const segs: SawSeg[] = []
  const lead = p.inventories.find((iv) => iv.afterIndex === -1)
  if (lead) segs.push({ w: GAP, high: true, label: `${lead.days}天` })
  // 关键路径上每个工序：取其 C/T 段；其后若有库存（afterIndex 指向该工序）加非增值段。
  critPath.forEach((proc) => {
    segs.push({ w: PROC_W, high: false, label: `${proc.cycleTime}s` })
    const idx = idToIdx.get(proc.id)
    const inv = idx != null ? p.inventories.find((iv) => iv.afterIndex === idx) : undefined
    if (inv) segs.push({ w: GAP, high: true, label: `${inv.days}天` })
  })
  // startX 使首个增值段中心对齐关键路径首工序（列 0）
  const firstCx = colCx(0)
  const startX = lead ? firstCx - PROC_W / 2 - GAP : firstCx - PROC_W / 2
  prims.push({ kind: 'sawtooth', id: nid('saw'), x: startX, y, segments: segs })

  // 汇总计算：增值时间沿关键路径取和；交付周期含全部库存天数。
  const vaSec = critPath.reduce((a, b) => a + (b.cycleTime || 0), 0)
  const leadDays = p.inventories.reduce((a, b) => a + (b.days || 0), 0)
  const vaDays = vaSec / 86400
  const totalDays = leadDays + vaDays
  const pce = totalDays > 0 ? (vaDays / totalDays) * 100 : 0

  // 时间线右端总计（天 / 秒）
  let segW = 0
  for (const s of segs) segW += s.w
  const endX = startX + segW + 16
  prims.push({ kind: 'text', id: nid('lt'), x: endX, y: y - 10, w: 90, value: `${leadDays}天`, align: 'left', bold: true, fontSize: 12 })
  prims.push({ kind: 'text', id: nid('va'), x: endX, y: y + 24, w: 90, value: `${vaSec}秒`, align: 'left', bold: true, fontSize: 12 })

  // Takt 框（左下）
  if (p.showTakt && p.customer.dailyDemand > 0 && p.workingTimePerDay > 0) {
    const takt = p.workingTimePerDay / p.customer.dailyDemand
    prims.push({ kind: 'box', id: nid('takt'), x: supplierCx - ENDBOX_W / 2, y: y + 70, w: 190, h: 56, label: `节拍时间 Takt\n${takt.toFixed(1)} 秒/件`, style: 'taktbox' })
  }

  // 汇总框（右下）
  const sumLabel = [
    `增值时间：${vaSec} 秒`,
    `交付周期：${totalDays.toFixed(2)} 天`,
    `生产周期效率 PCE：${pce.toFixed(2)}%`,
  ].join('\n')
  prims.push({ kind: 'box', id: nid('summary'), x: customerCx - ENDBOX_W / 2, y: y + 70, w: 230, h: 72, label: sumLabel, style: 'summary' })
}

// ---------------- coerce / default / example ----------------

export function invTypeName(t: InvType): string {
  return C.invName[t] ?? 'I'
}

function num(v: unknown, d = 0): number {
  const n = Number(v)
  return Number.isFinite(n) ? n : d
}

export function defaultVsmPayload(): VsmPayload {
  return {
    title: '价值流程图',
    customer: { name: '客户', dailyDemand: 0, unit: '件', deliveryFreq: '', infoLabel: '月客户订单' },
    supplier: { name: '供应商', deliveryFreq: '', infoLabel: '月采购订单' },
    control: { name: '生产控制 / MRP' },
    processes: [
      { id: 'p1', name: '工序1', cycleTime: 0, changeover: 0, operators: 1, uptime: 100, firstYield: 100 },
    ],
    inventories: [],
    infoFlows: [],
    kaizens: [],
    workingTimePerDay: 0,
    showTakt: true,
  }
}

export function coerceVsmPayload(raw: Record<string, any> | null | undefined): VsmPayload {
  const base = defaultVsmPayload()
  if (!raw || typeof raw !== 'object') return base

  const processes: VsmProcess[] = Array.isArray(raw.processes) && raw.processes.length > 0
    ? raw.processes.map((s: any, i: number) => ({
        id: String(s?.id ?? `p${i + 1}`),
        name: String(s?.name ?? `工序${i + 1}`),
        cycleTime: num(s?.cycleTime),
        changeover: num(s?.changeover),
        operators: num(s?.operators, 1),
        uptime: num(s?.uptime, 100),
        firstYield: num(s?.firstYield, 100),
        next: Array.isArray(s?.next) ? s.next.map((x: any) => String(x)) : [],
      }))
    : base.processes.map((s) => ({ ...s }))

  // 过滤无效后继 id（指向不存在的工序或自身）
  const validIds = new Set(processes.map((s) => s.id))
  processes.forEach((s) => { s.next = (s.next || []).filter((nx) => validIds.has(nx) && nx !== s.id) })

  const procCount = processes.length
  const clampIdx = (v: unknown) => Math.max(-1, Math.min(num(v, -1), procCount))

  const inventories: VsmInventory[] = Array.isArray(raw.inventories)
    ? raw.inventories.map((iv: any) => ({
        afterIndex: clampIdx(iv?.afterIndex),
        qty: num(iv?.qty),
        days: num(iv?.days),
        invType: (['inventory', 'supermarket', 'fifo'].includes(iv?.invType) ? iv.invType : 'inventory') as InvType,
      }))
    : []

  // 信息流：头恒为生产控制（control），尾为某个工序 id
  const infoFlows: VsmInfoFlow[] = Array.isArray(raw.infoFlows)
    ? raw.infoFlows.map((f: any) => ({
        fromId: 'control',
        toId: String(f?.toId ?? ''),
        label: String(f?.label ?? ''),
        type: (f?.type === 'manual' ? 'manual' : 'electronic') as InfoType,
      }))
    : []

  const kaizens: VsmKaizen[] = Array.isArray(raw.kaizens)
    ? raw.kaizens.map((k: any) => ({ afterIndex: clampIdx(k?.afterIndex), label: String(k?.label ?? '') }))
    : []

  return {
    title: raw.title != null && String(raw.title).trim() !== '' ? String(raw.title) : base.title,
    customer: {
      name: String(raw.customer?.name ?? base.customer.name),
      dailyDemand: num(raw.customer?.dailyDemand),
      unit: String(raw.customer?.unit ?? '件'),
      deliveryFreq: String(raw.customer?.deliveryFreq ?? ''),
      infoLabel: String(raw.customer?.infoLabel ?? base.customer.infoLabel),
    },
    supplier: {
      name: String(raw.supplier?.name ?? base.supplier.name),
      deliveryFreq: String(raw.supplier?.deliveryFreq ?? ''),
      infoLabel: String(raw.supplier?.infoLabel ?? base.supplier.infoLabel),
    },
    control: { name: String(raw.control?.name ?? base.control.name) },
    processes,
    inventories,
    infoFlows,
    kaizens,
    workingTimePerDay: num(raw.workingTimePerDay),
    showTakt: raw.showTakt !== false,
  }
}

export function exampleVsmPayload(): VsmPayload {
  return {
    title: '某装配线当前状态价值流程图',
    customer: { name: '客户', dailyDemand: 265, unit: '件', deliveryFreq: '每日1次', infoLabel: '月客户订单' },
    supplier: { name: '钢材供应商', deliveryFreq: '每周2次', infoLabel: '月采购订单' },
    control: { name: '生产控制 / MRP' },
    processes: [
      { id: 'p1', name: '冲压', cycleTime: 2, changeover: 120, operators: 2, uptime: 98, firstYield: 96, next: ['p2', 'p3'] },
      { id: 'p2', name: '焊接', cycleTime: 39, changeover: 20, operators: 1, uptime: 99, firstYield: 90, next: ['p4'] },
      { id: 'p3', name: '去毛边', cycleTime: 17, changeover: 0, operators: 1, uptime: 80, firstYield: 100, next: ['p4'] },
      { id: 'p4', name: '装配', cycleTime: 48, changeover: 15, operators: 2, uptime: 100, firstYield: 98, next: [] },
    ],
    inventories: [
      { afterIndex: -1, qty: 2650, days: 10, invType: 'inventory' },
      { afterIndex: 0, qty: 5300, days: 20, invType: 'inventory' },
      { afterIndex: 1, qty: 1325, days: 5, invType: 'inventory' },
      { afterIndex: 2, qty: 1060, days: 4, invType: 'inventory' },
    ],
    infoFlows: [
      { fromId: 'control', toId: 'p1', label: '周计划', type: 'manual' },
      { fromId: 'control', toId: 'p4', label: '日计划', type: 'manual' },
    ],
    kaizens: [
      { afterIndex: 0, label: '换模时间过长' },
      { afterIndex: 2, label: '在制品积压' },
    ],
    workingTimePerDay: 27600, // 7.67h 有效工时（秒）
    showTakt: true,
  }
}
