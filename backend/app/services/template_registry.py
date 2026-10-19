import json
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.template import Template
from app.core.config import get_settings

settings = get_settings()


async def sync_templates(db: AsyncSession) -> None:
    templates_dir = Path(settings.CHART_TEMPLATES_DIR)
    registry_path = templates_dir / "_registry.json"
    if not registry_path.exists():
        return

    with open(registry_path, encoding="utf-8") as f:
        data = json.load(f)

    registry = data if isinstance(data, list) else data.get("templates", [])

    registry_ids = set()
    for item in registry:
        tid = item["id"]
        registry_ids.add(tid)
        result = await db.execute(select(Template).where(Template.id == tid))
        existing = result.scalar_one_or_none()

        meta_path = templates_dir / tid / "meta.json"
        config = {}
        if meta_path.exists():
            with open(meta_path, encoding="utf-8") as f:
                config = json.load(f)

        prompt_path = templates_dir / tid / "prompt.md"
        if prompt_path.exists():
            config["promptContent"] = prompt_path.read_text(encoding="utf-8")

        for style in config.get("styles", []):
            pf = templates_dir / tid / style.get("promptFile", "")
            if pf.exists():
                style["promptContent"] = pf.read_text(encoding="utf-8")

        if existing:
            existing.name = item.get("name", existing.name)
            existing.engine = item.get("engine", existing.engine)
            existing.category = item.get("category", existing.category)
            existing.description = item.get("description", existing.description)
            existing.tags = item.get("tags", existing.tags)
            existing.sort_order = item.get("sortOrder", existing.sort_order)
            existing.config = config
        else:
            db.add(Template(
                id=tid,
                name=item.get("name", ""),
                engine=item.get("engine", "matplotlib"),
                category=item.get("category", ""),
                description=item.get("description", ""),
                tags=item.get("tags", []),
                status="published",
                sort_order=item.get("sortOrder", 0),
                config=config,
            ))

    all_res = await db.execute(select(Template))
    for t in all_res.scalars().all():
        if t.id not in registry_ids:
            await db.delete(t)

    await db.commit()
