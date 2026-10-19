"""工序自动编码引擎单元测试（M2）。

注：固化的是“结构规则”行为（生成编码=原始码、单向流门禁、分段判断、树形结构）。
生成编码直接沿用录入原始码，使「生成编码」与「原编码」保持一致。
"""
from app.services.sop.coder import (
    encode_processes, validate_single_flow, to_tree,
    SEGMENT_BOTTLENECK, SEGMENT_BRANCH_UNEVEN,
)


def _serial():
    return [
        {"original_code": "A", "original_upstream": None, "process_name": "a", "sam": 10},
        {"original_code": "B", "original_upstream": "A", "process_name": "b", "sam": 12},
        {"original_code": "C", "original_upstream": "B", "process_name": "c", "sam": 40},
        {"original_code": "D", "original_upstream": "C", "process_name": "d", "sam": 9},
    ]


def test_serial_codes_match_original():
    r = encode_processes(_serial(), takt=20)
    assert r["ok"] is True and r["errors"] == []
    assert r["terminal"] == "D"
    codes = {p["original_code"]: p["gen_code"] for p in r["processes"]}
    assert codes == {"A": "A", "B": "B", "C": "C", "D": "D"}


def test_serial_gen_upstream_links():
    r = encode_processes(_serial(), takt=20)
    up = {p["original_code"]: p["gen_upstream"] for p in r["processes"]}
    assert up["D"] == "C"  # D 的上游 C 的 gen_code（即原始码）
    assert up["C"] == "B"
    assert up["A"] is None  # 起点无上游


def test_bottleneck_flag():
    r = encode_processes(_serial(), takt=20)
    reasons = {p["original_code"]: p["segment_reason"] for p in r["processes"]}
    assert reasons["C"] == SEGMENT_BOTTLENECK  # sam=40 > takt 20
    assert reasons["A"] is None


def test_load_ratio_sums_100():
    r = encode_processes(_serial(), takt=20)
    total = sum(p["load_ratio"] for p in r["processes"])
    assert abs(total - 100.0) < 0.1


def _branch():
    # X、Y 两支汇入 Z，Z->W 成品
    return [
        {"original_code": "X", "original_upstream": None, "process_name": "x", "sam": 100},
        {"original_code": "Y", "original_upstream": None, "process_name": "y", "sam": 14},
        {"original_code": "Z", "original_upstream": "X,Y", "process_name": "z", "sam": 20},
        {"original_code": "W", "original_upstream": "Z", "process_name": "w", "sam": 15},
    ]


def test_branch_confluence_codes():
    r = encode_processes(_branch(), takt=60)
    assert r["ok"] is True
    codes = {p["original_code"]: p["gen_code"] for p in r["processes"]}
    # 生成编码即原始码
    assert codes == {"X": "X", "Y": "Y", "Z": "Z", "W": "W"}
    # 汇流节点 Z 的上游编码列出两支
    up = {p["original_code"]: p["gen_upstream"] for p in r["processes"]}
    assert up["Z"] == "X,Y"


def test_branch_uneven_flag():
    r = encode_processes(_branch(), takt=60)
    reasons = {p["original_code"]: p["segment_reason"] for p in r["processes"]}
    assert reasons["X"] == SEGMENT_BOTTLENECK       # 100 > 60
    assert reasons["Y"] == SEGMENT_BRANCH_UNEVEN    # 短支路且 100/14 ≥ 3


def test_fork_allowed():
    """DAG 放开后，分叉（一上游对多下游）不再拦截。"""
    fork = [
        {"original_code": "A", "original_upstream": None, "process_name": "a", "sam": 5},
        {"original_code": "B", "original_upstream": "A", "process_name": "b", "sam": 5},
        {"original_code": "C", "original_upstream": "A", "process_name": "c", "sam": 5},
    ]
    ok, errors, info = validate_single_flow(fork)
    assert ok is True
    assert errors == []
    # A 分叉到 B、C，二者均为结束点
    assert sorted(info["terminals"]) == ["B", "C"]
    assert info["downstream_map"]["A"] == ["B", "C"] or sorted(info["downstream_map"]["A"]) == ["B", "C"]


def test_cycle_rejected():
    """成环仍属非法结构，必须拦截。"""
    cyc = [
        {"original_code": "A", "original_upstream": "C", "process_name": "a", "sam": 5},
        {"original_code": "B", "original_upstream": "A", "process_name": "b", "sam": 5},
        {"original_code": "C", "original_upstream": "B", "process_name": "c", "sam": 5},
    ]
    ok, errors, _ = validate_single_flow(cyc)
    assert ok is False
    assert any("环" in e for e in errors)


def test_multi_terminal_codes():
    """多结束点：两条成品线各起一级百位基码，互不冲突。"""
    multi = [
        {"original_code": "A", "original_upstream": None, "process_name": "a", "sam": 10},
        {"original_code": "B", "original_upstream": "A", "process_name": "b", "sam": 10},
        {"original_code": "C", "original_upstream": None, "process_name": "c", "sam": 10},
        {"original_code": "D", "original_upstream": "C", "process_name": "d", "sam": 10},
    ]
    r = encode_processes(multi, takt=20)
    assert r["ok"] is True
    assert sorted(r["terminals"]) == ["B", "D"]
    assert r["terminal"] is None  # 多结束点时 terminal 为 None
    codes = {p["original_code"]: p["gen_code"] for p in r["processes"]}
    # 生成编码即原始码，多结束点也保持一致
    assert codes == {"A": "A", "B": "B", "C": "C", "D": "D"}


def test_missing_upstream_rejected():
    bad = [
        {"original_code": "A", "original_upstream": "Z", "process_name": "a", "sam": 5},
    ]
    ok, errors, _ = validate_single_flow(bad)
    assert ok is False
    assert any("不存在" in e for e in errors)


def test_to_tree_shape():
    r = encode_processes(_serial(), takt=20)
    tree = to_tree(r["processes"])
    assert len(tree["nodes"]) == 4
    assert len(tree["edges"]) == 3  # A->B, B->C, C->D
    assert {"source": "A", "target": "B"} in tree["edges"]
