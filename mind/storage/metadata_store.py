import json
from pathlib import Path
from datetime import datetime, timezone
from pydantic import BaseModel

METADATA_PATH = Path("/data/indicator_metadata.json")


class IndicatorMetadata(BaseModel):
    id: str
    display_name: str
    description: str
    country: str
    subgroups: list[str]
    version: str
    color_theme: str = "RdBu"
    shape_version: str = "1"
    hidden: bool = False
    is_user_created: bool = True
    created_at: str = ""
    csv_files: list[str] = []
    onboarding_notes: str = ""


def _load() -> dict[str, dict]:
    if METADATA_PATH.exists():
        return json.loads(METADATA_PATH.read_text())
    return {}


def _save(data: dict[str, dict]):
    METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    METADATA_PATH.write_text(json.dumps(data, indent=2))


def list_indicators() -> list[IndicatorMetadata]:
    return [IndicatorMetadata(**v) for v in _load().values()]


def get_indicator(indicator_id: str) -> IndicatorMetadata | None:
    data = _load()
    if indicator_id in data:
        return IndicatorMetadata(**data[indicator_id])
    return None


def save_indicator(meta: IndicatorMetadata):
    data = _load()
    if not meta.created_at:
        meta.created_at = datetime.now(timezone.utc).isoformat()
    data[meta.id] = meta.model_dump()
    _save(data)


def update_indicator(indicator_id: str, **kwargs) -> IndicatorMetadata | None:
    data = _load()
    if indicator_id not in data:
        return None
    data[indicator_id].update(kwargs)
    _save(data)
    return IndicatorMetadata(**data[indicator_id])


def delete_indicator(indicator_id: str) -> bool:
    data = _load()
    if indicator_id not in data:
        return False
    meta = IndicatorMetadata(**data.pop(indicator_id))
    _save(data)
    indicators_dir = Path("/data/indicators")
    for csv_file in meta.csv_files:
        p = indicators_dir / csv_file
        if p.exists():
            p.unlink()
    return True
