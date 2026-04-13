from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from starlette.concurrency import iterate_in_threadpool

from workflow.agent import run_agent_stream

router = APIRouter()


@router.post("/chat")
async def chat(request: Request):
    data = await request.json()
    session_id = data["session_id"]
    message = data["message"]
    api_key = data.get("api_key")

    if isinstance(message, dict) and message.get("form_id"):
        formatted = f"[Form submission: {message['form_id']}]\n"
        for k, v in message.get("values", {}).items():
            formatted += f"- {k}: {v}\n"
        message = formatted

    gen = run_agent_stream(session_id, message, api_key)
    return StreamingResponse(
        iterate_in_threadpool(gen),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
