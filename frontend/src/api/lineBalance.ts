/** 产线平衡 / SOP 工作台 API 封装（对应后端 /api/v1/lb）。 */
import request from './request'

// —— 款式 ——
export interface Style {
  id: number
  styleCode: string
  name: string
  totalWorkers?: number | null
  taktTime?: number | null
  hourlyOutput?: number | null
}

export interface Process {
  id: number
  originalCode: string
  originalUpstream?: string | null
  processName: string
  actualTime?: number | null
  relaxRate?: number
  ratingFactor?: number
  sam?: number | null
  machineType?: string | null
  workerMachine?: string | null
  genCode?: string | null
  genUpstream?: string | null
  segmentReason?: string | null
  load?: number | null
  loadRatio?: number | null
  isBottleneck?: boolean
  canMerge?: boolean
  canAdd?: boolean
  twoHandData?: Record<string, any> | null
}

export interface EncodePreview {
  ok: boolean
  errors: string[]
  terminal: string | null
  terminals?: string[]
  roots: string[]
  processes: Array<{
    originalCode: string
    genCode: string | null
    genUpstream: string | null
    processName: string
    sam: number
    load?: number | null
    loadRatio?: number | null
    isBottleneck?: boolean
    segmentReason?: string | null
  }>
}

export interface TreeNode { id: string; label?: string; [k: string]: any }
export interface TreeEdge { source: string; target: string }
export interface ProcessTree { ok: boolean; errors: string[]; nodes: TreeNode[]; edges: TreeEdge[] }

export interface TaskState<T = any> {
  taskId: string
  status: 'pending' | 'running' | 'done' | 'error'
  progress: string
  result: T | null
  error: string | null
}

export interface OptimizeResult {
  styleId: number
  balanceRate: number
  timeoutReached: boolean
  baseline?: boolean
  kpi: Record<string, any>
  stations: Array<{
    stationCode: string
    workerCount: number
    time: number
    mergeNames: string[]
    name: string
    originalId: number
    originalIds?: number[]
  }>
}

export interface Plan {
  id: number
  name: string
  workerCount?: number | null
  takt?: number | null
  balanceRate?: number | null
  totalWorkTime?: number | null
  timeoutReached?: boolean
  isSelected?: boolean
  params?: Record<string, any> | null
}

export interface EquipmentItem {
  name?: string | null
  model?: string | null
  condition?: string | null
}

export interface Station {
  id: number
  stationCode: string
  workerCount: number
  stationTakt?: number | null
  upstreamStation?: string | null
  downstreamStation?: string | null
  processDetail?: any[] | null
  // 旧 5 段（兼容）
  workSteps?: string | null
  tools?: string | null
  processReq?: string | null
  qualityReq?: string | null
  refImages?: string[] | null
  // 装配 SOP 段
  processSeq?: number | null
  workType?: string | null
  checkSteps?: string | null
  mainSteps?: string | null
  notes?: string | null
  selfCheck?: string | null
  techReq?: string | null
  equipment?: EquipmentItem[] | null
  approver?: string | null
  reviewer?: string | null
  department?: string | null
  ownerName?: string | null
  fileNo?: string | null
  version?: string | null
}

export interface CutPiece {
  id: number
  pieceCode: string        // 材料编号
  pieceName?: string | null // 材料名称
  spec?: string | null      // 材料规格
  material?: string | null  // 材质（金属/塑料…）
  shape?: string | null
  fabric?: string | null
  areaCm2?: number | null
  sizeMm?: string | null
  refImage?: string | null
  used?: boolean
  quantity?: number | null  // 当前工位上下文中的关联数量
}

export interface StationCutPieceItem {
  cutPieceId: number
  quantity: number
}

export interface ProcessMaterial {
  pieceCode: string
  pieceName?: string | null
  quantity?: number | null
}

const lb = {
  // 款式
  listStyles: (params?: { page?: number; pageSize?: number; keyword?: string }) =>
    request.get<{ list: Style[]; total: number }>('/lb/styles', { params }),
  createStyle: (body: Partial<Style>) => request.post<Style>('/lb/styles', body),
  getStyle: (id: number) => request.get<Style>(`/lb/styles/${id}`),
  updateStyle: (id: number, body: Partial<Style>) => request.put<Style>(`/lb/styles/${id}`, body),
  deleteStyle: (id: number) => request.delete(`/lb/styles/${id}`),

  // 工序
  listProcesses: (styleId: number) =>
    request.get<{ list: Process[] }>(`/lb/styles/${styleId}/processes`),
  addProcesses: (styleId: number, processes: Partial<Process>[], replace = false) =>
    request.post<{ list: Process[]; count: number }>(`/lb/styles/${styleId}/processes`, { processes, replace }),
  updateProcess: (id: number, body: Partial<Process>) => request.put<Process>(`/lb/processes/${id}`, body),
  deleteProcess: (id: number) => request.delete(`/lb/processes/${id}`),

  // 视频分析（工序录入第二入口）
  uploadVideo: (styleId: number, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request.post<{ url: string; filename: string; duration: number }>(
      `/lb/styles/${styleId}/video`, form,
      { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 600000 },
    )
  },
  clipVideo: (filename: string, start: number, end: number) =>
    request.post<{ url: string; filename: string }>(`/lb/video/clip`, { filename, start, end }),

  // 编码
  encode: (styleId: number) => request.post<EncodePreview>(`/lb/styles/${styleId}/encode`),
  processTree: (styleId: number) => request.get<ProcessTree>(`/lb/styles/${styleId}/process-tree`),
  confirmEncode: (styleId: number) =>
    request.post<{ confirmed: number; terminal: string }>(`/lb/styles/${styleId}/encode/confirm`),

  // 平衡寻优
  optimize: (styleId: number, body?: { targetOutput?: number; workHours?: number; addPeopleFix?: boolean; useConfirmedCodes?: boolean }) =>
    request.post<{ taskId: string; status: string }>(`/lb/balance/optimize?style_id=${styleId}`, body || {}),
  getOptimizeTask: (taskId: string) => request.get<TaskState<OptimizeResult>>(`/lb/balance/tasks/${taskId}`),
  saveBaseline: (styleId: number) =>
    request.post<Plan & { stationCount: number }>(`/lb/balance/baseline?style_id=${styleId}`),

  // 方案
  savePlan: (styleId: number, taskId: string, name?: string) =>
    request.post<Plan & { stationCount: number }>(`/lb/plans?style_id=${styleId}`, { taskId, name }),
  listPlans: (styleId: number) => request.get<{ list: Plan[] }>(`/lb/plans?style_id=${styleId}`),
  selectedPlan: (styleId: number) =>
    request.get<{ plan: Plan | null }>(`/lb/plans/selected?style_id=${styleId}`),
  selectPlan: (planId: number) => request.post<Plan>(`/lb/plans/${planId}/select`),
  planStations: (planId: number) =>
    request.get<{ plan: Plan; stations: Station[] }>(`/lb/plans/${planId}/stations`),

  // 裁片
  importCutpieces: (styleId: number, pieces: Partial<CutPiece>[], replace = false) =>
    request.post<{ list: CutPiece[]; count: number }>(`/lb/styles/${styleId}/cutpieces/import`, { pieces, replace }),
  listCutpieces: (styleId: number, params?: { plan_id?: number; unused_only?: boolean }) =>
    request.get<{ list: CutPiece[]; total: number }>(`/lb/styles/${styleId}/cutpieces`, { params }),
  bindStationCutpieces: (stationId: number, items: StationCutPieceItem[]) =>
    request.post<{ stationId: number; boundCount: number }>(`/lb/stations/${stationId}/cutpieces`, { items }),

  // 工序级物料绑定（新绑定单位：工序）
  getProcessMaterials: (processId: number) =>
    request.get<{ processId: number; materials: CutPiece[] }>(`/lb/processes/${processId}/materials`),
  bindProcessMaterials: (processId: number, items: StationCutPieceItem[]) =>
    request.post<{ processId: number; boundCount: number }>(`/lb/processes/${processId}/materials`, { items }),

  // 工序双手作业分析
  getTwoHand: (processId: number) =>
    request.get<{ processId: number; data: Record<string, any> | null }>(`/lb/processes/${processId}/two-hand`),
  saveTwoHand: (processId: number, data: Record<string, any> | null) =>
    request.put<{ processId: number }>(`/lb/processes/${processId}/two-hand`, { data }),

  // 工位信息 + SOP
  getStation: (stationId: number) => request.get<Station & { cutPieces: CutPiece[] }>(`/lb/stations/${stationId}`),
  updateStationInfo: (stationId: number, body: Partial<Station>) =>
    request.put<Station>(`/lb/stations/${stationId}/info`, body),
  singleSopUrl: (stationId: number, fmt: 'html' | 'pdf' = 'html') =>
    `/lb/sop/${stationId}?fmt=${fmt}`,
  generateSinglePdf: (stationId: number) =>
    request.post<{ url: string; filename: string }>(`/lb/sop/${stationId}?fmt=pdf`),
  generateSingleXlsx: (stationId: number) =>
    request.post<{ url: string; filename: string }>(`/lb/sop/${stationId}?fmt=xlsx`),
  batchSop: (planId: number, body: { stationIds?: number[]; fmt?: 'html' | 'pdf' | 'xlsx' }) =>
    request.post<{ taskId: string; status: string; total: number }>(`/lb/sop/batch?plan_id=${planId}`, body),
  getSopTask: (taskId: string) =>
    request.get<TaskState<{ url: string; filename: string; count: number; fmt: string }>>(`/lb/sop/tasks/${taskId}`),

  // 生产线平衡图（复用模板中心 line-balance matplotlib 模板）
  generateBalanceChart: (params: { title?: string; station_names: string[]; station_times: number[] }) =>
    request.post<{ image_base64: string; summary?: Record<string, any> }>(
      '/charts/generate', { templateId: 'line-balance', params }),
}

export default lb
