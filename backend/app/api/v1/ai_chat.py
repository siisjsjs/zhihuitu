import json
import re
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.core.config import get_settings
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.template import Template
from app.models.ai_config import AiConfig
from app.api.response import ok

router = APIRouter()


class ChatBody(BaseModel):
    templateId: str
    messages: list[dict]
    style: str | None = None


@router.post("/chat")
async def ai_chat(body: ChatBody, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    tpl_res = await db.execute(select(Template).where(Template.id == body.templateId))
    tpl = tpl_res.scalar_one_or_none()
    if not tpl:
        raise HTTPException(status_code=404, detail="模板不存在")

    ai_res = await db.execute(select(AiConfig).where(AiConfig.is_enabled == True).order_by(AiConfig.sort_order))
    ai_cfg = ai_res.scalars().first()
    if not ai_cfg:
        raise HTTPException(status_code=503, detail="未配置 AI 服务")

    prompt_content = ""
    if body.style and (styles := (tpl.config or {}).get("styles")):
        matched = next((s for s in styles if s["id"] == body.style), None)
        if matched:
            prompt_content = matched.get("promptContent", "")
    if not prompt_content:
        prompt_content = (tpl.config or {}).get("promptContent", "")
    if not prompt_content:
        pf = Path(get_settings().CHART_TEMPLATES_DIR).resolve() / tpl.id / "prompt.md"
        if pf.is_file():
            prompt_content = pf.read_text(encoding="utf-8")
    messages = [{"role": "system", "content": prompt_content}] + body.messages if prompt_content else body.messages

    reply, chart_data, finished = await _call_llm(ai_cfg, messages, tpl.engine)
    return ok({"reply": reply, "chartData": chart_data, "finished": finished})


def _extract_chart_dict(text: str) -> dict | None:
    """从模型回复中取出第一个 JSON 对象（支持 ```json 围栏、正文内嵌）。"""
    if not text or not isinstance(text, str):
        return None
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    chunks: list[str] = []
    if fenced:
        chunks.append(fenced.group(1).strip())
    chunks.append(text)
    decoder = json.JSONDecoder()
    for chunk in chunks:
        i = 0
        while i < len(chunk):
            j = chunk.find("{", i)
            if j == -1:
                break
            try:
                obj, _end = decoder.raw_decode(chunk, j)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                pass
            i = j + 1
    return None


async def _call_llm(cfg: AiConfig, messages: list, engine: str):
    if cfg.provider == "anthropic":
        import anthropic
        client = anthropic.AsyncAnthropic(
            api_key=cfg.api_key,
            base_url=cfg.base_url or None,
            timeout=get_settings().AI_REQUEST_TIMEOUT_SECONDS,
        )
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        user_msgs = [m for m in messages if m["role"] != "system"]
        resp = await client.messages.create(model=cfg.model, max_tokens=4096, system=system, messages=user_msgs)
        text = resp.content[0].text
    else:
        import openai
        client = openai.AsyncOpenAI(
            api_key=cfg.api_key,
            base_url=cfg.base_url or None,
            timeout=get_settings().AI_REQUEST_TIMEOUT_SECONDS,
        )
        resp = await client.chat.completions.create(model=cfg.model, messages=messages)
        text = resp.choices[0].message.content

    chart_data = _extract_chart_dict(text)
    finished = chart_data is not None

    return text, chart_data, finished
