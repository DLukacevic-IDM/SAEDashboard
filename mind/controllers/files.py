from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, PlainTextResponse

router = APIRouter()
TMP_DIR = Path("/data/tmp")


@router.get("/files/{session_id}/{filename}")
async def serve_file(session_id: str, filename: str):
    path = TMP_DIR / session_id / filename
    if not path.exists():
        return PlainTextResponse("File not found", status_code=404)
    return FileResponse(path)


@router.get("/files/{session_id}/{filename}/raw")
async def serve_file_raw(session_id: str, filename: str):
    path = TMP_DIR / session_id / filename
    if not path.exists():
        return PlainTextResponse("File not found", status_code=404)
    return PlainTextResponse(path.read_text())
