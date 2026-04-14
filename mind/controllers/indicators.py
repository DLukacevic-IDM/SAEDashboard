import json
import os
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
import httpx
import pandas as pd

from storage.metadata_store import (
    list_indicators, get_indicator, update_indicator, delete_indicator
)

router = APIRouter()
INDICATORS_DIR = Path("/data/indicators")
CHATS_DIR = Path("/data/chats")
SERVICE_URL = os.getenv("SERVICE_URL", "http://service:5000")
DATA_FILE_REGEX = re.compile(r'^(?P<country>.+)__(?P<channel>.+)__(?P<subgroup>.+)__(?P<version>.+)\.csv$')


def _scan_indicator_files() -> dict[str, dict]:
    """Scan /data/indicators/ for CSV files and extract metadata from filenames."""
    if not INDICATORS_DIR.exists():
        return {}
    indicators = {}
    for f in INDICATORS_DIR.glob("*.csv"):
        m = DATA_FILE_REGEX.match(f.name)
        if not m:
            continue
        channel = m["channel"]
        if channel not in indicators:
            indicators[channel] = {
                "id": channel,
                "country": m["country"],
                "subgroups": [],
                "version": m["version"],
                "csv_files": [],
            }
        indicators[channel]["subgroups"].append(m["subgroup"])
        indicators[channel]["csv_files"].append(f.name)
    return indicators


def _get_indicator_data_meta(channel: str, country: str, subgroup: str, version: str) -> dict:
    """Extract admin_levels, time range from a specific indicator CSV."""
    filename = f"{country}__{channel}__{subgroup}__{version}.csv"
    path = INDICATORS_DIR / filename
    if not path.exists():
        return {"admin_levels": [], "time": {}}
    df = pd.read_csv(path)
    admin_levels = set()
    if "state" in df.columns:
        admin_levels = {int(x) for x in (df["state"].str.count(":")).unique()}
    time_data = {}
    if "year" in df.columns:
        for year in sorted(df["year"].unique()):
            time_data[int(year)] = []
    return {"admin_levels": sorted(admin_levels), "time": time_data}


@router.get("/indicators")
async def get_indicators():
    file_indicators = _scan_indicator_files()
    metadata = {m.id: m for m in list_indicators()}

    result = []
    for ind_id, file_info in file_indicators.items():
        meta = metadata.get(ind_id)
        first_subgroup = file_info["subgroups"][0] if file_info["subgroups"] else "all"
        data_meta = _get_indicator_data_meta(ind_id, file_info["country"], first_subgroup, file_info["version"])

        result.append({
            "id": ind_id,
            "display_name": meta.display_name if meta else ind_id.replace("_", " ").title(),
            "description": meta.description if meta else "",
            "country": file_info["country"],
            "subgroups": sorted(set(file_info["subgroups"])),
            "version": file_info["version"],
            "color_theme": meta.color_theme if meta else "RdBu",
            "hidden": meta.hidden if meta else False,
            "is_user_created": True,
            "created_at": meta.created_at if meta else "",
            "onboarding_notes": meta.onboarding_notes if meta else "",
            "admin_levels": data_meta["admin_levels"],
            "time": data_meta["time"],
        })
    return {"indicators": result}


@router.get("/indicators/{indicator_id}")
async def get_indicator_detail(indicator_id: str):
    indicators = (await get_indicators())["indicators"]
    ind = next((i for i in indicators if i["id"] == indicator_id), None)
    if not ind:
        raise HTTPException(404, "Indicator not found")
    return ind


@router.patch("/indicators/{indicator_id}")
async def patch_indicator(indicator_id: str, body: dict):
    meta = get_indicator(indicator_id)
    if not meta:
        raise HTTPException(404, "Indicator not found in metadata store")
    if not meta.is_user_created:
        raise HTTPException(403, "Cannot modify default indicators")
    updated = update_indicator(indicator_id, **{k: v for k, v in body.items() if k in ("hidden",)})
    if not updated:
        raise HTTPException(500, "Update failed")

    if "hidden" in body:
        try:
            if updated.hidden:
                httpx.post(
                    f"{SERVICE_URL}/indicators/deregister",
                    json={"indicator_id": indicator_id},
                    timeout=30.0,
                )
            else:
                for csv_file in updated.csv_files:
                    path = INDICATORS_DIR / csv_file
                    if path.exists():
                        with open(path, "rb") as f:
                            httpx.post(
                                f"{SERVICE_URL}/indicators/register",
                                files={"file": (csv_file, f, "text/csv")},
                                timeout=30.0,
                            )
        except Exception:
            pass

    return {"ok": True, "hidden": updated.hidden}


@router.get("/indicators/{indicator_id}/chat")
async def get_indicator_chat(indicator_id: str):
    chat_file = CHATS_DIR / f"{indicator_id}.json"
    if not chat_file.exists():
        return {"messages": []}
    return {"messages": json.loads(chat_file.read_text())}


@router.delete("/indicators/{indicator_id}")
async def delete_indicator_endpoint(indicator_id: str):
    meta = get_indicator(indicator_id)
    if not meta:
        raise HTTPException(404, "Indicator not found")
    if not meta.is_user_created:
        raise HTTPException(403, "Cannot delete default indicators")
    try:
        httpx.post(
            f"{SERVICE_URL}/indicators/deregister",
            json={"indicator_id": indicator_id},
            timeout=30.0,
        )
    except Exception:
        pass
    delete_indicator(indicator_id)
    return {"ok": True}
