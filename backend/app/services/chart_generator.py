import importlib.util
import sys
import asyncio
import hashlib
import json
import time
from pathlib import Path
from collections import OrderedDict
from app.core.config import get_settings

settings = get_settings()
_generate_semaphore = asyncio.Semaphore(settings.CHART_GENERATION_MAX_CONCURRENCY)
_cache: OrderedDict[str, tuple[float, dict]] = OrderedDict()


def _cache_key(template_id: str, params: dict) -> str:
    payload = json.dumps(params, ensure_ascii=False, sort_keys=True, default=str)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"{template_id}:{digest}"


def _get_cached(key: str) -> dict | None:
    if settings.CHART_GENERATION_CACHE_TTL_SECONDS <= 0:
        return None
    item = _cache.get(key)
    if not item:
        return None
    expires_at, value = item
    if expires_at < time.monotonic():
        _cache.pop(key, None)
        return None
    _cache.move_to_end(key)
    return value.copy()


def _set_cached(key: str, value: dict) -> None:
    ttl = settings.CHART_GENERATION_CACHE_TTL_SECONDS
    if ttl <= 0 or settings.CHART_GENERATION_CACHE_MAX_ITEMS <= 0:
        return
    _cache[key] = (time.monotonic() + ttl, value.copy())
    _cache.move_to_end(key)
    while len(_cache) > settings.CHART_GENERATION_CACHE_MAX_ITEMS:
        _cache.popitem(last=False)


def _run_generator(template_id: str, params: dict) -> dict:
    templates_dir = Path(settings.CHART_TEMPLATES_DIR).resolve()
    gen_path = templates_dir / template_id / "generator.py"
    if not gen_path.exists():
        raise FileNotFoundError(f"generator.py not found for template: {template_id}")

    templates_str = str(templates_dir)
    if templates_str not in sys.path:
        sys.path.insert(0, templates_str)

    spec = importlib.util.spec_from_file_location(
        f"chart_gen_{template_id}", str(gen_path)
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    result = mod.generate(params)
    return {"image_base64": result["image_base64"], "summary": result.get("summary", {})}


async def generate_chart(template_id: str, params: dict) -> dict:
    key = _cache_key(template_id, params)
    cached = _get_cached(key)
    if cached is not None:
        return cached

    async with _generate_semaphore:
        cached = _get_cached(key)
        if cached is not None:
            return cached
        result = await asyncio.to_thread(_run_generator, template_id, params)
        _set_cached(key, result)
        return result
