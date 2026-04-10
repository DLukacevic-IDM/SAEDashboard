import re
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException
import pandas as pd

router = APIRouter()
INDICATORS_DIR = Path("/data/indicators")
DATA_FILE_REGEX = re.compile(r'^(?P<country>.+)__(?P<channel>.+)__(?P<subgroup>.+)__(?P<version>.+)\.csv$')

DATA_CACHE: dict[str, pd.DataFrame] = {}


def _load_indicator(country: str, channel: str, subgroup: str, version: str) -> pd.DataFrame:
    filename = f"{country}__{channel}__{subgroup}__{version}.csv"
    path = INDICATORS_DIR / filename
    if not path.exists():
        raise HTTPException(404, f"Indicator file not found: {filename}")

    if str(path) in DATA_CACHE:
        return DATA_CACHE[str(path)]

    df = pd.read_csv(path)

    renames = {"state": "dot_name", "pred": "data", "pred_upper": "data_upper_bound", "pred_lower": "data_lower_bound"}
    if channel in df.columns:
        renames[channel] = "reference"
    se_col = f"se.{channel}"
    if se_col in df.columns:
        renames[se_col] = "reference_stderr"
    df = df.rename(columns=renames)

    if "reference" in df.columns and "reference_stderr" in df.columns:
        df["reference_lower_bound"] = df["reference"] - df["reference_stderr"] * 1.96
        df["reference_upper_bound"] = df["reference"] + df["reference_stderr"] * 1.96
        df = df.drop(columns=["reference_stderr"])

    DATA_CACHE[str(path)] = df
    return df


def _find_version(country: str, channel: str) -> str:
    if not INDICATORS_DIR.exists():
        raise HTTPException(404, "No indicators directory")
    pattern = re.compile(rf'^{re.escape(country)}__{re.escape(channel)}__.+__(?P<version>\d+)\.csv$')
    for f in INDICATORS_DIR.glob("*.csv"):
        m = pattern.match(f.name)
        if m:
            return m["version"]
    raise HTTPException(404, f"No data found for {country}/{channel}")


@router.get("/map")
async def get_map(request: Request):
    params = request.query_params
    dot_name = params.get("dot_name", "")
    channel = params.get("channel", "")
    subgroup = params.get("subgroup", "all")
    year = int(params.get("year", 0))
    admin_level = int(params.get("admin_level", 2))
    version = params.get("shape_version", None)

    country = dot_name.split(":")[1] if ":" in dot_name else dot_name
    if not version:
        version = _find_version(country, channel)

    df = _load_indicator(country, channel, subgroup, version)

    if "dot_name" in df.columns:
        target_depth = admin_level + 1
        mask = df["dot_name"].str.startswith(dot_name) & (df["dot_name"].str.count(":") == target_depth)
        df = df[mask]

    if "year" in df.columns and year:
        df = df[df["year"] == year]

    result = []
    for _, row in df.iterrows():
        entry = {
            "id": row.get("dot_name", ""),
            "value": row.get("data", None),
            "data_lower_bound": row.get("data_lower_bound", None),
            "data_upper_bound": row.get("data_upper_bound", None),
        }
        result.append(entry)
    return result


@router.get("/timeseries")
async def get_timeseries(request: Request):
    params = request.query_params
    dot_name = params.get("dot_name", "")
    channel = params.get("channel", "")
    subgroup = params.get("subgroup", "all")
    version = params.get("shape_version", None)

    country = dot_name.split(":")[1] if ":" in dot_name else dot_name
    if not version:
        version = _find_version(country, channel)

    df = _load_indicator(country, channel, subgroup, version)

    if "dot_name" in df.columns:
        df = df[df["dot_name"] == dot_name]

    result = []
    for _, row in df.iterrows():
        entry = {
            "year": int(row.get("year", 0)),
            "lower_bound": row.get("data_lower_bound", None),
            "middle": row.get("data", None),
            "upper_bound": row.get("data_upper_bound", None),
        }
        if "reference" in df.columns:
            ref = row.get("reference")
            if pd.notna(ref):
                entry["reference_middle"] = ref
                entry["reference_lower_bound"] = row.get("reference_lower_bound")
                entry["reference_upper_bound"] = row.get("reference_upper_bound")
        if "month" in df.columns and pd.notna(row.get("month")):
            entry["month"] = row["month"]
        result.append(entry)

    return sorted(result, key=lambda x: (x.get("year", 0), x.get("month", 0)))


@router.get("/indicators-data")
async def get_indicators_data(request: Request):
    """Return indicator metadata in the same format as the main service's GET /indicators."""
    if not INDICATORS_DIR.exists():
        return {"indicators": []}

    indicators: dict[str, dict] = {}
    for f in INDICATORS_DIR.glob("*.csv"):
        m = DATA_FILE_REGEX.match(f.name)
        if not m:
            continue
        channel = m["channel"]
        if channel not in indicators:
            indicators[channel] = {
                "id": channel,
                "text": channel.replace("_", " ").title(),
                "version": int(m["version"]),
                "admin_levels": set(),
                "subgroups": set(),
                "time": {},
            }
        indicators[channel]["subgroups"].add(m["subgroup"])

        try:
            df = pd.read_csv(f, usecols=lambda c: c in ("state", "year"))
            if "state" in df.columns:
                levels = (df["state"].str.count(":")).unique()
                indicators[channel]["admin_levels"].update(int(l) for l in levels)
            if "year" in df.columns:
                for yr in df["year"].unique():
                    indicators[channel]["time"][int(yr)] = []
        except Exception:
            pass

    result = []
    for ind in indicators.values():
        ind["admin_levels"] = sorted(ind["admin_levels"])
        ind["subgroups"] = sorted(ind["subgroups"])
        result.append(ind)
    return {"indicators": result}
