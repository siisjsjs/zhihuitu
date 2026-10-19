/**
 * 价值流程图 (VSM) → Draw.io (mxGraphModel) XML
 * 消费 vsmLayout.ts 的 computeVsmLayout 产物，逐 primitive 生成 mxCell。
 */
import {
  computeVsmLayout,
  coerceVsmPayload,
  defaultVsmPayload,
  exampleVsmPayload,
  invTypeName,
  TRI_HALF,
  OP_R,
  TRUCK_W,
  TRUCK_H,
  type VsmPayload,
  type VsmPrimitive,
  type BoxStyle,
  type EdgeFlow,
} from './vsmLayout'

export {
  coerceVsmPayload,
  defaultVsmPayload,
  exampleVsmPayload,
  computeVsmLayout,
}
export type { VsmPayload }

function escapeXml(s: string): string {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/\n/g, '&#10;')
}

const BOX_STYLE: Record<BoxStyle, string> = {
  process: 'rounded=0;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontSize=12;fontStyle=1;verticalAlign=middle;align=center;',
  customer: 'rounded=0;whiteSpace=wrap;html=1;fillColor=#ffe6cc;strokeColor=#d79b00;fontSize=12;fontStyle=1;verticalAlign=middle;align=center;',
  supplier: 'rounded=0;whiteSpace=wrap;html=1;fillColor=#ffe6cc;strokeColor=#d79b00;fontSize=12;fontStyle=1;verticalAlign=middle;align=center;',
  control: 'rounded=0;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;fontSize=12;fontStyle=1;verticalAlign=middle;align=center;',
  datatable: 'rounded=0;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;fontSize=10;',
  taktbox: 'rounded=0;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;fontSize=11;fontStyle=1;',
  summary: 'rounded=0;whiteSpace=wrap;html=1;fillColor=#e1d5e7;strokeColor=#9673a6;fontSize=11;align=left;spacingLeft=8;',
}

const EDGE_STYLE: Record<EdgeFlow, string> = {
  push: 'html=1;endArrow=block;startArrow=none;strokeColor=#1f2937;strokeWidth=1.6;rounded=1;',
  pull: 'html=1;endArrow=classic;strokeColor=#1f2937;dashed=0;rounded=1;',
  'manual-mat': 'html=1;endArrow=open;strokeColor=#1f2937;strokeWidth=1;rounded=1;',
  'info-e': 'html=1;endArrow=open;strokeColor=#1f2937;rounded=1;dashed=0;',
  'info-m': 'html=1;endArrow=open;strokeColor=#1f2937;rounded=1;dashed=1;dashPattern=4 3;',
  ship: 'html=1;endArrow=block;strokeColor=#1f2937;strokeWidth=1.5;rounded=1;fillColor=#dddddd;',
  'info-thick': 'html=1;endArrow=block;startArrow=none;strokeColor=#1f2937;strokeWidth=2;rounded=1;',
}

export function buildValueStreamMxGraphXml(payload: VsmPayload): string {
  const layout = computeVsmLayout(payload)
  const cells: string[] = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
  let nid = 2
  const pid = () => String(nid++)

  // 外框 + 标题
  const FRAME_X = 6
  const FRAME_Y = 6
  const FRAME_W = layout.width
  const FRAME_H = layout.height + 36
  const frameId = pid()
  cells.push(
    `<mxCell id="${frameId}" value="" style="rounded=1;arcSize=2;fillColor=#FFFFFF;strokeColor=#000000;strokeWidth=1;whiteSpace=wrap;html=1;verticalAlign=top;" vertex="1" parent="1"><mxGeometry x="${FRAME_X}" y="${FRAME_Y}" width="${FRAME_W}" height="${FRAME_H}" as="geometry"/></mxCell>`
  )
  const titleId = pid()
  cells.push(
    `<mxCell id="${titleId}" value="${escapeXml(payload.title || '价值流程图')}" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;fontSize=21;fontStyle=1;fontColor=#1f2937;" vertex="1" parent="1"><mxGeometry x="${FRAME_X}" y="${FRAME_Y + 4}" width="${FRAME_W}" height="28" as="geometry"/></mxCell>`
  )

  // primitive 内部坐标整体下移，给标题腾空间
  const OFF_Y = FRAME_Y + 34

  // 记录每个 box/triangle 的中心，供 edge 端点对齐（这里用绝对坐标连线，无需 source/target）
  for (const pr of layout.primitives) {
    emitPrimitive(pr, cells, pid, FRAME_X, OFF_Y)
  }

  const inner = cells.join('')
  const pageW = Math.ceil(FRAME_W + FRAME_X * 2)
  const pageH = Math.ceil(FRAME_H + FRAME_Y * 2)
  const graph = `<mxGraphModel dx="1400" dy="900" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="0" pageScale="1" pageWidth="${pageW}" pageHeight="${pageH}" math="0" shadow="0" background="#FFFFFF"><root>${inner}</root></mxGraphModel>`
  return `<mxfile host="embed.diagrams.net"><diagram id="value-stream" name="价值流程图">${graph}</diagram></mxfile>`
}

function emitPrimitive(
  pr: VsmPrimitive,
  cells: string[],
  pid: () => string,
  ox: number,
  oy: number,
): void {
  switch (pr.kind) {
    case 'box': {
      cells.push(
        `<mxCell id="${pid()}" value="${escapeXml(pr.label)}" style="${BOX_STYLE[pr.style]}" vertex="1" parent="1"><mxGeometry x="${pr.x + ox}" y="${pr.y + oy}" width="${pr.w}" height="${pr.h}" as="geometry"/></mxCell>`
      )
      break
    }
    case 'dataRows': {
      const x = pr.x + ox
      let y = pr.y + oy
      for (const [k, v] of pr.rows) {
        const half = pr.w / 2
        cells.push(
          `<mxCell id="${pid()}" value="${escapeXml(k)}" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#9e9e9e;fontSize=10;align=left;spacingLeft=4;" vertex="1" parent="1"><mxGeometry x="${x}" y="${y}" width="${half}" height="${pr.rowH}" as="geometry"/></mxCell>`
        )
        cells.push(
          `<mxCell id="${pid()}" value="${escapeXml(v)}" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#9e9e9e;fontSize=10;align=center;" vertex="1" parent="1"><mxGeometry x="${x + half}" y="${y}" width="${pr.w - half}" height="${pr.rowH}" as="geometry"/></mxCell>`
        )
        y += pr.rowH
      }
      break
    }
    case 'operator': {
      const x = pr.x + ox - OP_R
      const y = pr.y + oy - OP_R
      cells.push(
        `<mxCell id="${pid()}" value="${pr.count}" style="ellipse;whiteSpace=wrap;html=1;fillColor=#ffe6cc;strokeColor=#d79b00;fontSize=10;fontStyle=1;" vertex="1" parent="1"><mxGeometry x="${x}" y="${y}" width="${OP_R * 2}" height="${OP_R * 2}" as="geometry"/></mxCell>`
      )
      break
    }
    case 'triangle': {
      const x = pr.x + ox - TRI_HALF
      const y = pr.y + oy - TRI_HALF
      cells.push(
        `<mxCell id="${pid()}" value="${escapeXml(invTypeName(pr.invType))}" style="triangle;direction=north;whiteSpace=wrap;html=1;fillColor=#ffe6cc;strokeColor=#d79b00;fontSize=12;fontStyle=1;verticalAlign=bottom;spacingBottom=2;" vertex="1" parent="1"><mxGeometry x="${x}" y="${y}" width="${TRI_HALF * 2}" height="${TRI_HALF * 2}" as="geometry"/></mxCell>`
      )
      const tag = `${pr.qty}件 / ${pr.days}天`
      cells.push(
        `<mxCell id="${pid()}" value="${escapeXml(tag)}" style="text;html=1;strokeColor=none;fillColor=none;align=center;fontSize=9;" vertex="1" parent="1"><mxGeometry x="${pr.x + ox - 50}" y="${y - 16}" width="100" height="16" as="geometry"/></mxCell>`
      )
      break
    }
    case 'truck': {
      // 用基础图形拼卡车（embed 版 Draw.io 不带 lean_mapping 模具，stencil 会渲染空白）
      const cx = pr.x + ox
      const cy = pr.y + oy
      const boxX = cx - TRUCK_W / 2
      const boxY = cy - TRUCK_H / 2 + 2
      const boxW = TRUCK_W * 0.6
      const boxH = TRUCK_H - 12
      const cabX = boxX + boxW
      const cabW = TRUCK_W / 2 - TRUCK_W * 0.1
      const cabY = cy - 8
      const cabH = TRUCK_H / 2 - 2
      const wheelR = 8
      const wheelY = cy + TRUCK_H / 2 - 9 - wheelR
      // 货箱
      cells.push(
        `<mxCell id="${pid()}" value="" style="rounded=1;arcSize=12;html=1;fillColor=#eceff1;strokeColor=#546e7a;strokeWidth=1.4;" vertex="1" parent="1"><mxGeometry x="${boxX}" y="${boxY}" width="${boxW}" height="${boxH}" as="geometry"/></mxCell>`
      )
      // 驾驶室（斜切前脸）
      cells.push(
        `<mxCell id="${pid()}" value="" style="shape=trapezoid;direction=south;html=1;fillColor=#90a4ae;strokeColor=#546e7a;strokeWidth=1.4;" vertex="1" parent="1"><mxGeometry x="${cabX}" y="${cabY}" width="${cabW}" height="${cabH}" as="geometry"/></mxCell>`
      )
      // 车窗
      cells.push(
        `<mxCell id="${pid()}" value="" style="rounded=0;html=1;fillColor=#cfe8f5;strokeColor=#546e7a;strokeWidth=1;" vertex="1" parent="1"><mxGeometry x="${cabX + 4}" y="${cabY + 3}" width="${cabW - 12}" height="9" as="geometry"/></mxCell>`
      )
      // 车轮
      for (const wcx of [cx - TRUCK_W * 0.2, cx + TRUCK_W * 0.34]) {
        cells.push(
          `<mxCell id="${pid()}" value="" style="ellipse;html=1;fillColor=#37474f;strokeColor=#263238;" vertex="1" parent="1"><mxGeometry x="${wcx - wheelR}" y="${wheelY}" width="${wheelR * 2}" height="${wheelR * 2}" as="geometry"/></mxCell>`
        )
      }
      if (pr.freq) {
        cells.push(
          `<mxCell id="${pid()}" value="${escapeXml(pr.freq)}" style="text;html=1;strokeColor=none;fillColor=none;align=center;fontSize=9;" vertex="1" parent="1"><mxGeometry x="${cx - 50}" y="${cy - TRUCK_H / 2 - 16}" width="100" height="14" as="geometry"/></mxCell>`
        )
      }
      break
    }
    case 'kaizen': {
      cells.push(
        `<mxCell id="${pid()}" value="${escapeXml(pr.label)}" style="shape=mxgraph.lean_mapping.kaizen_lightening_burst;html=1;fillColor=#ffcccc;strokeColor=#b85450;fontSize=9;whiteSpace=wrap;" vertex="1" parent="1"><mxGeometry x="${pr.x + ox - 45}" y="${pr.y + oy - 30}" width="90" height="60" as="geometry"/></mxCell>`
      )
      break
    }
    case 'text': {
      const align = pr.align || 'left'
      const fs = pr.fontSize || 11
      const fw = pr.bold ? 'fontStyle=1;' : ''
      cells.push(
        `<mxCell id="${pid()}" value="${escapeXml(pr.value)}" style="text;html=1;strokeColor=none;fillColor=none;align=${align};verticalAlign=middle;fontSize=${fs};${fw}whiteSpace=wrap;" vertex="1" parent="1"><mxGeometry x="${pr.x + ox}" y="${pr.y + oy}" width="${pr.w}" height="18" as="geometry"/></mxCell>`
      )
      break
    }
    case 'sawtooth': {
      emitSawtooth(pr, cells, pid, ox, oy)
      break
    }
    case 'edge': {
      const pts = pr.points.map((p) => ({ x: p.x + ox, y: p.y + oy }))
      const src = pts[0]
      const dst = pts[pts.length - 1]
      const waypoints = pts.slice(1, -1)
      const wpXml = waypoints.length
        ? `<Array as="points">${waypoints.map((w) => `<mxPoint x="${w.x}" y="${w.y}"/>`).join('')}</Array>`
        : ''
      const lbl = pr.label ? escapeXml(pr.label) : ''
      const labelStyle = lbl ? 'fontSize=10;fontStyle=1;fontColor=#1f2937;labelBackgroundColor=#FFFFFF;' : ''
      cells.push(
        `<mxCell id="${pid()}" value="${lbl}" style="${EDGE_STYLE[pr.flow]}${labelStyle}" edge="1" parent="1"><mxGeometry relative="1" as="geometry"><mxPoint x="${src.x}" y="${src.y}" as="sourcePoint"/><mxPoint x="${dst.x}" y="${dst.y}" as="targetPoint"/>${wpXml}</mxGeometry></mxCell>`
      )
      break
    }
  }
}

function emitSawtooth(
  pr: Extract<VsmPrimitive, { kind: 'sawtooth' }>,
  cells: string[],
  pid: () => string,
  ox: number,
  oy: number,
): void {
  const baseX = pr.x + ox
  const baseY = pr.y + oy
  const LOW = baseY + 30 // 增值（贴近基线）
  const HIGH = baseY // 非增值（抬高）
  const STEP = 18
  let x = baseX
  const segPts: { x: number; y: number }[] = []
  // 时间线为方波：增值段在下，非增值段在上
  for (const s of pr.segments) {
    const yTop = s.high ? HIGH : LOW
    segPts.push({ x, y: yTop })
    segPts.push({ x: x + s.w, y: yTop })
    // 段标签
    cells.push(
      `<mxCell id="${pid()}" value="${escapeXml(s.label)}" style="text;html=1;strokeColor=none;fillColor=none;align=center;fontSize=9;" vertex="1" parent="1"><mxGeometry x="${x}" y="${(s.high ? HIGH - 16 : LOW + STEP)}" width="${s.w}" height="14" as="geometry"/></mxCell>`
    )
    x += s.w
  }
  // 折线（方波）
  if (segPts.length >= 2) {
    const src = segPts[0]
    const dst = segPts[segPts.length - 1]
    const mid = segPts.slice(1, -1)
    const wp = mid.length ? `<Array as="points">${mid.map((m) => `<mxPoint x="${m.x}" y="${m.y}"/>`).join('')}</Array>` : ''
    cells.push(
      `<mxCell id="${pid()}" value="" style="html=1;endArrow=none;strokeColor=#000000;strokeWidth=1.2;rounded=0;" edge="1" parent="1"><mxGeometry relative="1" as="geometry"><mxPoint x="${src.x}" y="${src.y}" as="sourcePoint"/><mxPoint x="${dst.x}" y="${dst.y}" as="targetPoint"/>${wp}</mxGeometry></mxCell>`
    )
  }
}
