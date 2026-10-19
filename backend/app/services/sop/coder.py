"""工序自动编码引擎（F2，确定性规则，零 LLM 依赖）。

工艺关系按 DAG（有向无环图）建模，贴合真实装配场景：
- 关系图边：downstream.original_upstream 指向 upstream.original_code。
- 允许分叉（一上游对多下游，A→B、A→C）、汇流（多上游对一下游）、多个结束点（多条成品线）。
- 生成编码：直接沿用录入的原始码（gen_code = original_code），不再重排，
  让「生成编码」与「原编码」保持一致，便于用户对照。
- gen_upstream：本工序各直接上游的 gen_code（即各上游原始码）。

校验（硬门禁，仅拦真正非法的结构）：
- 原始码重复；
- 引用了不存在的上游码；
- 存在环（DAG 不允许成环）。
分叉与多结束点不再拦截（真实装配里普遍存在）。
分段判断：瓶颈保护（单序过长）/ 支路不均（并行支路时长悬殊）/ 复合均衡（留接口）。
"""
from __future__ import annotations
import re

SEG_SPLIT = re.compile(r"[,，、/\s]+")
SEGMENT_BOTTLENECK = "瓶颈保护"
SEGMENT_BRANCH_UNEVEN = "支路不均"
SEGMENT_COMPOSITE = "复合均衡"  # 计划书：演示未触发，先留常量


def _parse_upstreams(raw) -> list[str]:
    """把 original_upstream 解析成上游码列表（支持多上游汇流，逗号/顿号/空格分隔）。"""
    if raw is None:
        return []
    s = str(raw).strip()
    if not s:
        return []
    return [c for c in SEG_SPLIT.split(s) if c]


def _detect_cycle(by_code: dict, up_map: dict[str, list[str]]) -> list[str]:
    """DAG 环检测。返回构成环的部分节点（用于报错提示），无环则空列表。"""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {c: WHITE for c in by_code}
    on_cycle: list[str] = []

    def visit(node: str) -> bool:
        color[node] = GRAY
        for up in up_map.get(node, []):
            if up not in by_code:
                continue
            if color[up] == GRAY:
                on_cycle.append(up)
                return True
            if color[up] == WHITE and visit(up):
                on_cycle.append(up)
                return True
        color[node] = BLACK
        return False

    for c in by_code:
        if color[c] == WHITE and visit(c):
            break
    return on_cycle


def validate_single_flow(processes: list[dict]) -> tuple[bool, list[str], dict]:
    """工艺关系校验（DAG 语义）。返回 (ok, errors, info)。

    仅拦真正非法的结构：原始码重复、引用不存在的上游、存在环。
    允许分叉（一对多）、汇流（多对一）、多结束点。
    info 含 downstream_map / terminals / roots / by_code，供编码与可视化复用。
    """
    errors: list[str] = []
    by_code: dict[str, dict] = {}
    for p in processes:
        code = p["original_code"]
        if code in by_code:
            errors.append(f"原始码重复：{code}")
        by_code[code] = p

    up_map: dict[str, list[str]] = {}
    downstream_map: dict[str, list[str]] = {c: [] for c in by_code}
    for p in processes:
        ups = _parse_upstreams(p.get("original_upstream"))
        up_map[p["original_code"]] = ups
        for up in ups:
            if up not in by_code:
                errors.append(f"工序 {p['original_code']} 的上游 {up} 不存在")
                continue
            downstream_map[up].append(p["original_code"])

    cycle = _detect_cycle(by_code, up_map)
    if cycle:
        errors.append(f"工艺关系存在环：{'→'.join(cycle)}（DAG 不允许成环）")

    terminals = [c for c, downs in downstream_map.items() if not downs]
    roots = [p["original_code"] for p in processes if not up_map.get(p["original_code"])]

    # 无环时必有结束点；只有成环才会出现空 terminals，已由 cycle 报错覆盖。
    info = {"downstream_map": downstream_map, "terminals": terminals,
            "roots": roots, "by_code": by_code, "up_map": up_map}
    return (len(errors) == 0, errors, info)


def encode_processes(
    processes: list[dict],
    takt: float | None = None,
    bottleneck_ratio: float = 1.0,
    branch_imbalance_ratio: float = 3.0,
) -> dict:
    """对工序列表生成编码 + 分段判断。不修改入参，返回新结构。

    Args:
        processes: [{original_code, original_upstream, process_name, sam, ...}]
        takt: 目标节拍(s)，用于瓶颈判断；None 时以均值 1.5 倍兜底。
        bottleneck_ratio: 瓶颈阈值（× takt），sam 超过即标 瓶颈保护。
        branch_imbalance_ratio: 并行支路时长 max/min 超过即标 支路不均。

    Returns:
        {ok, errors, processes: [带 gen_code/.../segment_reason 的副本], terminal, roots}
    """
    ok, errors, info = validate_single_flow(processes)
    by_code = info["by_code"]
    total_sam = sum(float(p["sam"]) for p in processes) or 1.0
    sams = [float(p["sam"]) for p in processes]
    mean_sam = sum(sams) / len(sams) if sams else 0.0
    bottleneck_threshold = (takt * bottleneck_ratio) if takt else (mean_sam * 1.5)

    # 生成编码直接沿用原始码，让「生成编码」与「原编码」保持一致。
    gen: dict[str, str] = {p["original_code"]: p["original_code"] for p in processes}

    # 分支汇流处的支路不均：对每个有多上游的节点，比较各上游的 sam
    uneven_codes: set[str] = set()
    for p in processes:
        ups = _parse_upstreams(p.get("original_upstream"))
        if len(ups) >= 2:
            loads = [float(by_code[u]["sam"]) for u in ups if u in by_code]
            if loads and min(loads) > 0 and max(loads) / min(loads) >= branch_imbalance_ratio:
                # 标记较短支路（时长偏小的上游）为支路不均
                shortest = min(loads)
                for u in ups:
                    if u in by_code and float(by_code[u]["sam"]) == shortest:
                        uneven_codes.add(u)

    out = []
    for p in processes:
        code = p["original_code"]
        sam = float(p["sam"])
        is_bottleneck = sam > bottleneck_threshold
        reason = None
        if is_bottleneck:
            reason = SEGMENT_BOTTLENECK
        elif code in uneven_codes:
            reason = SEGMENT_BRANCH_UNEVEN
        item = dict(p)
        item["gen_code"] = gen.get(code)
        item["load"] = round(sam, 2)
        item["load_ratio"] = round(sam / total_sam * 100, 2)
        item["is_bottleneck"] = is_bottleneck
        item["segment_reason"] = reason
        out.append(item)

    # gen_upstream：用各自上游的 gen_code 回填
    for item in out:
        ups = _parse_upstreams(item.get("original_upstream"))
        up_codes = [gen.get(u) for u in ups if gen.get(u)]
        item["gen_upstream"] = ",".join(up_codes) if up_codes else None

    return {
        "ok": ok,
        "errors": errors,
        "processes": out,
        "terminal": info["terminals"][0] if len(info["terminals"]) == 1 else None,
        "terminals": info["terminals"],
        "roots": info["roots"],
    }


def to_tree(encoded_processes: list[dict]) -> dict:
    """把编码结果转为前端流程图（X6）所需的 nodes/edges 数据。"""
    nodes = []
    edges = []
    for p in encoded_processes:
        nodes.append({
            "id": p["original_code"],
            "genCode": p.get("gen_code"),
            "name": p.get("process_name"),
            "sam": p.get("sam"),
            "machineType": p.get("machine_type"),
            "loadRatio": p.get("load_ratio"),
            "isBottleneck": p.get("is_bottleneck", False),
            "segmentReason": p.get("segment_reason"),
        })
        for up in _parse_upstreams(p.get("original_upstream")):
            edges.append({"source": up, "target": p["original_code"]})
    return {"nodes": nodes, "edges": edges}
