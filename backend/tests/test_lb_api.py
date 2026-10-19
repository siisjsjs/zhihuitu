"""产线平衡工作台 M1（款式/工序 CRUD）集成测试。

用独立内存 SQLite + 依赖覆盖，避免污染开发库。
"""
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.api.deps import get_current_user
from app.models.user import User

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine(TEST_DB_URL)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 注入一个测试用户
    async with Session() as s:
        u = User(username="tester", hashed_password="x", role="user", is_active=True)
        s.add(u)
        await s.commit()
        await s.refresh(u)
        test_user_id = u.id

    async def _override_db():
        async with Session() as s:
            yield s

    async def _override_user():
        async with Session() as s:
            return await s.get(User, test_user_id)

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_style_crud_flow(client):
    # 建款
    r = await client.post("/api/v1/lb/styles", json={"styleCode": "9800", "name": "测试款", "totalWorkers": 56})
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    sid = data["id"]
    assert data["styleCode"] == "9800"
    assert data["totalWorkers"] == 56

    # 重复款号被拒
    dup = await client.post("/api/v1/lb/styles", json={"styleCode": "9800", "name": "重复"})
    assert dup.status_code == 400, dup.text

    # 列表可见
    lst = await client.get("/api/v1/lb/styles")
    assert lst.json()["data"]["total"] == 1

    # 更新
    upd = await client.put(f"/api/v1/lb/styles/{sid}", json={"name": "改名款", "taktTime": 162.3})
    assert upd.json()["data"]["name"] == "改名款"
    assert abs(upd.json()["data"]["taktTime"] - 162.3) < 1e-6


@pytest.mark.asyncio
async def test_process_bulk_and_list(client):
    r = await client.post("/api/v1/lb/styles", json={"styleCode": "1001", "name": "工序款"})
    sid = r.json()["data"]["id"]

    procs = [
        {"originalCode": "S1", "processName": "缝合", "sam": 12.0, "canMerge": True, "canAdd": True},
        {"originalCode": "S2", "originalUpstream": "S1", "processName": "锁边", "sam": 8.5},
    ]
    add = await client.post(f"/api/v1/lb/styles/{sid}/processes", json={"processes": procs, "replace": False})
    assert add.status_code == 200, add.text
    assert add.json()["data"]["count"] == 2

    # 同款重复原始码追加应被拒
    clash = await client.post(f"/api/v1/lb/styles/{sid}/processes",
                              json={"processes": [{"originalCode": "S1", "processName": "x", "sam": 1.0}]})
    assert clash.status_code == 400

    lst = await client.get(f"/api/v1/lb/styles/{sid}/processes")
    rows = lst.json()["data"]["list"]
    assert len(rows) == 2
    assert rows[0]["originalCode"] == "S1"
    assert rows[1]["originalUpstream"] == "S1"


@pytest.mark.asyncio
async def test_process_replace_clears_old(client):
    r = await client.post("/api/v1/lb/styles", json={"styleCode": "2002", "name": "替换款"})
    sid = r.json()["data"]["id"]
    await client.post(f"/api/v1/lb/styles/{sid}/processes",
                      json={"processes": [{"originalCode": "A", "processName": "a", "sam": 1.0}]})
    # replace=True 应清掉旧的
    await client.post(f"/api/v1/lb/styles/{sid}/processes",
                      json={"processes": [{"originalCode": "B", "processName": "b", "sam": 2.0}], "replace": True})
    lst = await client.get(f"/api/v1/lb/styles/{sid}/processes")
    rows = lst.json()["data"]["list"]
    assert len(rows) == 1 and rows[0]["originalCode"] == "B"


@pytest.mark.asyncio
async def test_encode_and_confirm_flow(client):
    # 节拍 20s 的款，录入串行 4 工序
    r = await client.post("/api/v1/lb/styles", json={"styleCode": "3003", "name": "编码款", "taktTime": 20})
    sid = r.json()["data"]["id"]
    procs = [
        {"originalCode": "A", "processName": "a", "sam": 10},
        {"originalCode": "B", "originalUpstream": "A", "processName": "b", "sam": 12},
        {"originalCode": "C", "originalUpstream": "B", "processName": "c", "sam": 40},
        {"originalCode": "D", "originalUpstream": "C", "processName": "d", "sam": 9},
    ]
    await client.post(f"/api/v1/lb/styles/{sid}/processes", json={"processes": procs})

    # 生成编码（预览）
    enc = await client.post(f"/api/v1/lb/styles/{sid}/encode")
    body = enc.json()["data"]
    assert body["ok"] is True
    assert body["terminal"] == "D"
    codes = {p["originalCode"]: p["genCode"] for p in body["processes"]}
    assert codes == {"D": "10", "C": "20", "B": "30", "A": "40"}
    reasons = {p["originalCode"]: p["segmentReason"] for p in body["processes"]}
    assert reasons["C"] == "瓶颈保护"

    # 编码树
    tree = await client.get(f"/api/v1/lb/styles/{sid}/process-tree")
    tdata = tree.json()["data"]
    assert tdata["ok"] is True
    assert len(tdata["nodes"]) == 4 and len(tdata["edges"]) == 3

    # 确认编码写库
    conf = await client.post(f"/api/v1/lb/styles/{sid}/encode/confirm")
    assert conf.status_code == 200, conf.text
    assert conf.json()["data"]["confirmed"] == 4

    # 确认后 list 应带 genCode
    lst = await client.get(f"/api/v1/lb/styles/{sid}/processes")
    rows = {p["originalCode"]: p for p in lst.json()["data"]["list"]}
    assert rows["D"]["genCode"] == "10"
    assert rows["C"]["isBottleneck"] is True


@pytest.mark.asyncio
async def test_encode_empty_style_returns_blank_preview(client):
    # 切换到尚未录入工序的款式时会自动触发诊断，应返回空预览而非 400。
    r = await client.post("/api/v1/lb/styles", json={"styleCode": "4004", "name": "空款"})
    sid = r.json()["data"]["id"]

    enc = await client.post(f"/api/v1/lb/styles/{sid}/encode")
    assert enc.status_code == 200, enc.text
    body = enc.json()["data"]
    assert body["ok"] is True
    assert body["processes"] == []
    assert body["terminal"] is None


@pytest.mark.asyncio
async def test_encode_fork_allowed_on_confirm(client):
    """DAG 放开后，分叉（一上游对多下游）可正常编码并确认。"""
    r = await client.post("/api/v1/lb/styles", json={"styleCode": "4004", "name": "分叉款"})
    sid = r.json()["data"]["id"]
    procs = [
        {"originalCode": "A", "processName": "a", "sam": 5},
        {"originalCode": "B", "originalUpstream": "A", "processName": "b", "sam": 5},
        {"originalCode": "C", "originalUpstream": "A", "processName": "c", "sam": 5},
    ]
    await client.post(f"/api/v1/lb/styles/{sid}/processes", json={"processes": procs})

    enc = await client.post(f"/api/v1/lb/styles/{sid}/encode")
    body = enc.json()["data"]
    assert body["ok"] is True
    # B、C 均为结束点（多结束点 → terminal 为 None，terminals 含两者）
    assert sorted(body["terminals"]) == ["B", "C"]

    # 校验通过 → 允许确认
    conf = await client.post(f"/api/v1/lb/styles/{sid}/encode/confirm")
    assert conf.status_code == 200, conf.text
    assert conf.json()["data"]["confirmed"] == 3


async def _wait_task(client, sid, task_id, timeout=15.0):
    """轮询寻优任务直到完成。"""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        r = await client.get(f"/api/v1/lb/balance/tasks/{task_id}")
        data = r.json()["data"]
        if data["status"] in ("done", "error"):
            return data
        await asyncio.sleep(0.05)
    raise AssertionError("寻优任务超时未完成")


@pytest.mark.asyncio
async def test_optimize_poll_and_save_plan(client):
    # 节拍 60s（target=480, 8h）：6 道串行工序 11..16s，应能合并
    r = await client.post("/api/v1/lb/styles", json={"styleCode": "9800", "name": "寻优款", "taktTime": 60})
    sid = r.json()["data"]["id"]
    procs = []
    prev = None
    for i in range(1, 7):
        procs.append({"originalCode": f"S{i}", "originalUpstream": prev,
                      "processName": f"工序{i}", "sam": 10.0 + i})
        prev = f"S{i}"
    await client.post(f"/api/v1/lb/styles/{sid}/processes", json={"processes": procs})
    # 确认编码（寻优默认要求 gen_code 非空）
    conf = await client.post(f"/api/v1/lb/styles/{sid}/encode/confirm")
    assert conf.status_code == 200, conf.text

    # 提交寻优
    sub = await client.post(f"/api/v1/lb/balance/optimize?style_id={sid}",
                            json={"targetOutput": 480, "workHours": 8.0})
    assert sub.status_code == 200, sub.text
    task_id = sub.json()["data"]["taskId"]

    done = await _wait_task(client, sid, task_id)
    assert done["status"] == "done", done.get("error")
    res = done["result"]
    assert res["timeoutReached"] is False
    assert res["balanceRate"] > 0.8
    assert len(res["stations"]) >= 1
    assert "kpi" in res and res["kpi"]["station_count"] == len(res["stations"])

    # 保存方案快照
    save = await client.post(f"/api/v1/lb/plans?style_id={sid}", json={"taskId": task_id})
    assert save.status_code == 200, save.text
    plan_id = save.json()["data"]["id"]
    assert "_" in save.json()["data"]["name"]  # 自动命名 款号_人数_节拍_平衡率

    # 方案列表 + 工位
    plans = await client.get(f"/api/v1/lb/plans?style_id={sid}")
    assert plans.json()["data"]["list"][0]["id"] == plan_id
    st = await client.get(f"/api/v1/lb/plans/{plan_id}/stations")
    assert len(st.json()["data"]["stations"]) == len(res["stations"])


@pytest.mark.asyncio
async def test_baseline_plan_first_and_style_isolated(client):
    """原始方案置顶 + 款式隔离：基线每工序一工位，列表第一条为基线；另一款式互不可见。"""
    r = await client.post("/api/v1/lb/styles", json={"styleCode": "6006", "name": "基线款", "taktTime": 60})
    sid = r.json()["data"]["id"]
    procs, prev = [], None
    for i in range(1, 5):
        procs.append({"originalCode": f"S{i}", "originalUpstream": prev,
                      "processName": f"工序{i}", "sam": 10.0 + i})
        prev = f"S{i}"
    await client.post(f"/api/v1/lb/styles/{sid}/processes", json={"processes": procs})

    # 生成原始方案（基线）— 每工序一工位
    base = await client.post(f"/api/v1/lb/balance/baseline?style_id={sid}")
    assert base.status_code == 200, base.text
    assert base.json()["data"]["stationCount"] == 4

    # 幂等：再次调用不重复创建
    base2 = await client.post(f"/api/v1/lb/balance/baseline?style_id={sid}")
    assert base2.json()["data"]["id"] == base.json()["data"]["id"]

    # 自动寻优 + 保存 → 列表里基线仍排第一
    sub = await client.post(f"/api/v1/lb/balance/optimize?style_id={sid}", json={})
    task_id = sub.json()["data"]["taskId"]
    await _wait_task(client, sid, task_id)
    await client.post(f"/api/v1/lb/plans?style_id={sid}", json={"taskId": task_id})

    lst = await client.get(f"/api/v1/lb/plans?style_id={sid}")
    plans = lst.json()["data"]["list"]
    assert len(plans) == 2
    assert plans[0]["params"]["baseline"] is True
    assert plans[1]["params"].get("baseline") is not True

    # 款式隔离：新建另一款式，看不到 6006 的方案
    r2 = await client.post("/api/v1/lb/styles", json={"styleCode": "6007", "name": "另一款"})
    sid2 = r2.json()["data"]["id"]
    lst2 = await client.get(f"/api/v1/lb/plans?style_id={sid2}")
    assert lst2.json()["data"]["list"] == []


@pytest.mark.asyncio
async def test_optimize_rejects_unconfirmed_codes(client):
    r = await client.post("/api/v1/lb/styles", json={"styleCode": "5005", "name": "未编码款", "taktTime": 60})
    sid = r.json()["data"]["id"]
    await client.post(f"/api/v1/lb/styles/{sid}/processes",
                      json={"processes": [{"originalCode": "A", "processName": "a", "sam": 10}]})
    # 显式要求已确认编码 → 未确认时拒绝（自动寻优默认不强制）
    sub = await client.post(f"/api/v1/lb/balance/optimize?style_id={sid}",
                            json={"useConfirmedCodes": True})
    assert sub.status_code == 400

    # 默认（自动寻优）不强制编码确认 → 直接受理
    auto = await client.post(f"/api/v1/lb/balance/optimize?style_id={sid}", json={})
    assert auto.status_code == 200, auto.text


async def _make_plan_with_stations(client):
    """建款→工序→确认编码→寻优→存方案，返回 (style_id, plan_id, station_ids)。"""
    r = await client.post("/api/v1/lb/styles", json={"styleCode": "7700", "name": "SOP款", "taktTime": 60})
    sid = r.json()["data"]["id"]
    procs, prev = [], None
    for i in range(1, 7):
        procs.append({"originalCode": f"S{i}", "originalUpstream": prev,
                      "processName": f"工序{i}", "sam": 10.0 + i})
        prev = f"S{i}"
    await client.post(f"/api/v1/lb/styles/{sid}/processes", json={"processes": procs})
    await client.post(f"/api/v1/lb/styles/{sid}/encode/confirm")
    sub = await client.post(f"/api/v1/lb/balance/optimize?style_id={sid}",
                            json={"targetOutput": 480, "workHours": 8.0})
    task_id = sub.json()["data"]["taskId"]
    await _wait_task(client, sid, task_id)
    save = await client.post(f"/api/v1/lb/plans?style_id={sid}", json={"taskId": task_id})
    plan_id = save.json()["data"]["id"]
    st = await client.get(f"/api/v1/lb/plans/{plan_id}/stations")
    station_ids = [s["id"] for s in st.json()["data"]["stations"]]
    return sid, plan_id, station_ids


@pytest.mark.asyncio
async def test_cutpiece_import_and_dedup(client):
    sid, _, _ = await _make_plan_with_stations(client)
    pieces = [
        {"pieceCode": "LD-01", "pieceName": "前片", "fabric": "棉", "sizeMm": "300x200"},
        {"pieceCode": "LD-02", "pieceName": "后片", "fabric": "棉"},
    ]
    imp = await client.post(f"/api/v1/lb/styles/{sid}/cutpieces/import",
                            json={"pieces": pieces, "replace": False})
    assert imp.status_code == 200, imp.text
    assert imp.json()["data"]["count"] == 2

    # 重复编号被拒
    dup = await client.post(f"/api/v1/lb/styles/{sid}/cutpieces/import",
                            json={"pieces": [{"pieceCode": "LD-01", "pieceName": "x"}]})
    assert dup.status_code == 400

    lst = await client.get(f"/api/v1/lb/styles/{sid}/cutpieces")
    assert lst.json()["data"]["total"] == 2


@pytest.mark.asyncio
async def test_cutpiece_bom_reuse_and_quantity(client):
    """装配 BOM 语义：物料可被多工位复用，绑定带数量，工位详情回填数量。"""
    sid, plan_id, station_ids = await _make_plan_with_stations(client)
    imp = await client.post(f"/api/v1/lb/styles/{sid}/cutpieces/import",
                            json={"pieces": [
                                {"pieceCode": "P1"}, {"pieceCode": "P2"}, {"pieceCode": "P3"},
                            ]})
    ids = [c["id"] for c in imp.json()["data"]["list"]]

    # 工位1 绑定 P1(x2),P2(x1)
    b1 = await client.post(f"/api/v1/lb/stations/{station_ids[0]}/cutpieces",
                           json={"items": [
                               {"cutPieceId": ids[0], "quantity": 2},
                               {"cutPieceId": ids[1], "quantity": 1},
                           ]})
    assert b1.status_code == 200, b1.text
    assert b1.json()["data"]["boundCount"] == 2

    # 工位2 也能绑定 P1（标准件复用，不再排他）
    b2 = await client.post(f"/api/v1/lb/stations/{station_ids[1]}/cutpieces",
                           json={"items": [{"cutPieceId": ids[0], "quantity": 5}]})
    assert b2.status_code == 200, b2.text

    # 工位1 详情：P1 数量=2，P2 数量=1
    st1 = await client.get(f"/api/v1/lb/stations/{station_ids[0]}")
    qty = {c["id"]: c["quantity"] for c in st1.json()["data"]["cutPieces"]}
    assert qty[ids[0]] == 2 and qty[ids[1]] == 1

    # 工位2 详情：同一 P1 在本工位数量=5（每工位独立计数）
    st2 = await client.get(f"/api/v1/lb/stations/{station_ids[1]}")
    qty2 = {c["id"]: c["quantity"] for c in st2.json()["data"]["cutPieces"]}
    assert qty2[ids[0]] == 5

    # plan 维度：P1/P2 已被使用，P3 未使用
    lst = await client.get(f"/api/v1/lb/styles/{sid}/cutpieces?plan_id={plan_id}")
    used = {c["id"]: c["used"] for c in lst.json()["data"]["list"]}
    assert used[ids[0]] is True and used[ids[1]] is True and used[ids[2]] is False

    # 覆盖语义：工位1 重绑只留 P3 → P1/P2 在工位1 解除
    rebind = await client.post(f"/api/v1/lb/stations/{station_ids[0]}/cutpieces",
                               json={"items": [{"cutPieceId": ids[2], "quantity": 1}]})
    assert rebind.status_code == 200, rebind.text
    st1b = await client.get(f"/api/v1/lb/stations/{station_ids[0]}")
    assert [c["id"] for c in st1b.json()["data"]["cutPieces"]] == [ids[2]]


@pytest.mark.asyncio
async def test_station_info_and_single_sop(client):
    sid, plan_id, station_ids = await _make_plan_with_stations(client)
    st_id = station_ids[0]

    info = await client.put(f"/api/v1/lb/stations/{st_id}/info", json={
        "workType": "装配",
        "processSeq": 2,
        "checkSteps": "1.核对图纸\n2.检查来料",
        "mainSteps": "1.对位\n2.拧紧螺栓\n3.复检",
        "notes": "扭矩按工艺卡执行",
        "selfCheck": "目视无划伤",
        "techReq": "扭矩 12N·m",
        "equipment": [{"name": "电动扳手", "model": "BT-12", "condition": "12N·m"}],
        "approver": "张三",
        "reviewer": "李四",
        "department": "总装",
        "ownerName": "王五",
        "version": "A",
    })
    assert info.status_code == 200, info.text
    body = info.json()["data"]
    assert body["workType"] == "装配"
    assert body["mainSteps"].startswith("1.对位")
    assert body["equipment"][0]["name"] == "电动扳手"

    # 单工位 SOP（HTML）— 应含装配字段
    html = await client.post(f"/api/v1/lb/sop/{st_id}?fmt=html")
    assert html.status_code == 200
    assert "标准作业指导书" in html.text
    assert "电动扳手" in html.text
    assert "拧紧螺栓" in html.text

    # 单工位 SOP（Excel）— 装配版式
    xlsx = await client.post(f"/api/v1/lb/sop/{st_id}?fmt=xlsx")
    assert xlsx.status_code == 200, xlsx.text
    assert xlsx.json()["data"]["filename"].endswith(".xlsx")

    # 单工位 SOP（PDF）
    pdf = await client.post(f"/api/v1/lb/sop/{st_id}?fmt=pdf")
    assert pdf.status_code == 200, pdf.text
    assert pdf.json()["data"]["filename"].endswith(".pdf")


@pytest.mark.asyncio
async def test_batch_sop_task(client):
    sid, plan_id, station_ids = await _make_plan_with_stations(client)
    sub = await client.post(f"/api/v1/lb/sop/batch?plan_id={plan_id}", json={"fmt": "html"})
    assert sub.status_code == 200, sub.text
    task_id = sub.json()["data"]["taskId"]

    # 轮询批量任务
    done = await _wait_sop_task(client, task_id)
    assert done["status"] == "done", done.get("error")
    assert done["result"]["count"] == len(station_ids)
    assert done["result"]["filename"].startswith("Batch_SOP_7700_")


async def _wait_sop_task(client, task_id, timeout=20.0):
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        r = await client.get(f"/api/v1/lb/sop/tasks/{task_id}")
        data = r.json()["data"]
        if data["status"] in ("done", "error"):
            return data
        await asyncio.sleep(0.05)
    raise AssertionError("批量 SOP 任务超时未完成")
