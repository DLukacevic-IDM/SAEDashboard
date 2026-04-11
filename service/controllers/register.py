import logging
import os
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from service.helpers.controller_helpers import (
    MASTER_DATA_FILE_REGEX, data_dir, clear_data_cache
)
from service.helpers.csv_validator import validate_indicator_csv

logger = logging.getLogger(__name__)
router = APIRouter()


class DeregisterRequest(BaseModel):
    indicator_id: str


@router.post("/indicators/register")
async def register_indicator(file: UploadFile = File(...)):
    filename = file.filename
    if not filename or not MASTER_DATA_FILE_REGEX.match(filename):
        raise HTTPException(
            status_code=400,
            detail=f"Filename '{filename}' does not match pattern: "
                   "{{Country}}__{{Indicator}}__{{Subgroup}}__{{Version}}.csv",
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    dest_path = os.path.join(data_dir, filename)
    tmp_path = dest_path + ".tmp"

    try:
        with open(tmp_path, "wb") as f:
            f.write(content)

        issues = validate_indicator_csv(Path(tmp_path))
        if issues:
            os.unlink(tmp_path)
            raise HTTPException(
                status_code=400,
                detail={"message": "CSV content validation failed", "issues": issues},
            )

        os.replace(tmp_path, dest_path)
    except HTTPException:
        raise
    except OSError as e:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise HTTPException(status_code=500, detail=f"Failed to write file: {e}")

    clear_data_cache(filename)
    logger.info(f"Registered indicator file: {filename} ({len(content)} bytes)")
    return {"status": "ok", "filename": filename, "bytes": len(content)}


@router.post("/indicators/deregister")
async def deregister_indicator(body: DeregisterRequest):
    removed = []
    for f in Path(data_dir).glob("*.csv"):
        m = MASTER_DATA_FILE_REGEX.match(f.name)
        if m and m["channel"] == body.indicator_id:
            clear_data_cache(f.name)
            f.unlink()
            removed.append(f.name)
    if not removed:
        raise HTTPException(status_code=404, detail=f"No files found for indicator '{body.indicator_id}'")
    logger.info(f"Deregistered indicator: {body.indicator_id}, removed {len(removed)} files")
    return {"status": "ok", "removed": removed}
