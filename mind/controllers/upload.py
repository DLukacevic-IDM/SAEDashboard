import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File

from workflow.csv_validator import load_upload

router = APIRouter()
UPLOADS_DIR = Path("/data/uploads")


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    session_id = str(uuid.uuid4())[:8]
    session_dir = UPLOADS_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    file_path = session_dir / file.filename
    content = await file.read()
    file_path.write_bytes(content)

    try:
        df, info = load_upload(file_path)
        sample_rows = df.head(5).fillna("").to_dict(orient="records")
    except Exception as e:
        return {
            "session_id": session_id,
            "validation": {"columns": [], "row_count": 0, "issues": [str(e)], "file_type": file_path.suffix},
            "sample_rows": [],
        }

    return {
        "session_id": session_id,
        "validation": {
            "columns": info["columns"],
            "row_count": info["row_count"],
            "file_type": info["file_type"],
            "sheets": info.get("sheets"),
            "issues": [],
        },
        "sample_rows": sample_rows,
    }
