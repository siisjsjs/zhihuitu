"""Lightweight SQLite column additions for dev DBs without Alembic."""

from sqlalchemy import text, inspect


def migrate_announcement_columns(connection) -> None:
    insp = inspect(connection)
    if not insp.has_table("announcements"):
        return
    col_names = {c["name"] for c in insp.get_columns("announcements")}
    if "is_highlight" not in col_names:
        connection.execute(text("ALTER TABLE announcements ADD COLUMN is_highlight BOOLEAN NOT NULL DEFAULT 0"))
    if "image_url" not in col_names:
        connection.execute(text("ALTER TABLE announcements ADD COLUMN image_url VARCHAR(1000)"))


def _add_columns(connection, table: str, columns: dict[str, str]) -> None:
    """对已存在的表补加缺失列（SQLite 友好；create_all 不会 ALTER 既有表）。"""
    insp = inspect(connection)
    if not insp.has_table(table):
        return
    existing = {c["name"] for c in insp.get_columns(table)}
    for name, ddl in columns.items():
        if name not in existing:
            connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def migrate_lb_columns(connection) -> None:
    """产线平衡：装配 BOM + 装配 SOP 字段补迁移。

    - lb_cut_pieces：新增 spec / material（材料规格、材质）。
    - lb_process_cut_pieces：新增 quantity（关联数量，复用语义）。
    - lb_stations：新增装配 SOP 各段字段 + 审批/文档头。
    旧的排他唯一索引 uq_lb_pcp_plan_piece 若存在则丢弃（改为可跨工位复用）。
    """
    _add_columns(connection, "lb_balance_plans", {
        "is_selected": "BOOLEAN NOT NULL DEFAULT 0",
    })
    _add_columns(connection, "lb_cut_pieces", {
        "spec": "VARCHAR(200)",
        "material": "VARCHAR(100)",
    })
    _add_columns(connection, "lb_process_cut_pieces", {
        "quantity": "FLOAT NOT NULL DEFAULT 1",
    })
    # 工序级双手作业分析数据快照 + 实测/系数（标准工时派生）
    _add_columns(connection, "lb_processes", {
        "two_hand_data": "JSON",
        "actual_time": "FLOAT",
        "relax_rate": "FLOAT NOT NULL DEFAULT 0",
        "rating_factor": "FLOAT NOT NULL DEFAULT 1",
    })
    _add_columns(connection, "lb_stations", {
        "process_seq": "INTEGER",
        "work_type": "VARCHAR(50)",
        "check_steps": "VARCHAR(2000)",
        "main_steps": "VARCHAR(4000)",
        "notes": "VARCHAR(2000)",
        "self_check": "VARCHAR(2000)",
        "tech_req": "VARCHAR(2000)",
        "equipment": "JSON",
        "approver": "VARCHAR(50)",
        "reviewer": "VARCHAR(50)",
        "department": "VARCHAR(100)",
        "owner_name": "VARCHAR(50)",
        "file_no": "VARCHAR(50)",
        "version": "VARCHAR(20)",
    })
    # 丢弃旧排他唯一索引（裁片排他 → BOM 复用）。索引名来自旧 UniqueConstraint。
    insp = inspect(connection)
    if insp.has_table("lb_process_cut_pieces"):
        idx_names = {i["name"] for i in insp.get_indexes("lb_process_cut_pieces")}
        if "uq_lb_pcp_plan_piece" in idx_names:
            connection.execute(text("DROP INDEX uq_lb_pcp_plan_piece"))
        if "uq_lb_pcp_station_piece" not in idx_names:
            connection.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_lb_pcp_station_piece "
                "ON lb_process_cut_pieces (station_id, cut_piece_id)"
            ))
