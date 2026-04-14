import os
import pickle
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

import pandas as pd

from workflow.constants import FINALIZE_SUCCESS_SENTINEL, MULTI_SHEET_SENTINEL, FILE_SAVED_PREFIX, METADATA_PREFIXES
from workflow.csv_validator import load_upload, get_upload_summary, validate_output_csv, MASTER_DATA_FILE_REGEX
from storage.metadata_store import (
    IndicatorMetadata, save_indicator, list_indicators as list_all_indicators
)

UPLOADS_DIR = Path("/data/uploads")
INDICATORS_DIR = Path("/data/indicators")
TMP_DIR = Path("/data/tmp")
SHAPES_DIR = Path(os.getenv("SHAPES_DIR", "/data/shapefiles"))

uploads_cache: dict[str, pd.DataFrame] = {}
uploads_cache_original: dict[str, pd.DataFrame] = {}


def validate_upload(session_id: str, sheet_name: str | None = None) -> str:
    upload_dir = UPLOADS_DIR / session_id
    files = list(upload_dir.glob("*"))
    if not files:
        return "ERROR: No uploaded file found for this session."

    path = files[0]
    try:
        df, info = load_upload(path, sheet_name)
        uploads_cache[session_id] = df
        uploads_cache_original[session_id] = df.copy()
    except Exception as e:
        return f"ERROR: Failed to read file: {e}"

    summary = get_upload_summary(df)
    sheets_note = ""
    if info.get("sheets") and len(info["sheets"]) > 1:
        sheets_note = f"\n{MULTI_SHEET_SENTINEL}: {info['sheets']}. Currently reading: {sheet_name or info['sheets'][0]}"

    return f"File: {path.name} ({info['file_type']})\n{sheets_note}\n\n{summary}"


def preview_data(session_id: str) -> str:
    if session_id not in uploads_cache:
        return "ERROR: No data loaded. Call validate_upload first."
    df = uploads_cache[session_id]
    return get_upload_summary(df)


def transform_csv(session_id: str, transformations: dict) -> str:
    if session_id not in uploads_cache:
        return "ERROR: No data loaded. Call validate_upload first."
    df = uploads_cache[session_id].copy()

    if "rename_columns" in transformations:
        df = df.rename(columns=transformations["rename_columns"])

    if "drop_columns" in transformations:
        df = df.drop(columns=[c for c in transformations["drop_columns"] if c in df.columns])

    if "add_state_column" in transformations:
        expr = transformations["add_state_column"]
        try:
            df["state"] = df.eval(expr) if isinstance(expr, str) and not expr.startswith("lambda") else df.apply(eval(expr), axis=1)
        except Exception as e:
            return f"ERROR: Failed to create state column: {e}"

    if "filter_expr" in transformations:
        try:
            df = df.query(transformations["filter_expr"])
        except Exception as e:
            return f"ERROR: Filter failed: {e}"

    if "value_transforms" in transformations:
        for col, expr in transformations["value_transforms"].items():
            if col in df.columns:
                try:
                    df[col] = df[col].apply(eval(expr))
                except Exception as e:
                    return f"ERROR: Transform on {col} failed: {e}"

    uploads_cache[session_id] = df
    return f"Transformed. New shape: {df.shape}\nColumns: {list(df.columns)}\n\nFirst 3 rows:\n{df.head(3).to_string()}"


def list_existing_indicators() -> str:
    indicators = list_all_indicators()
    if not indicators:
        return "No user-created indicators found."
    lines = []
    for ind in indicators:
        status = "HIDDEN" if ind.hidden else "visible"
        lines.append(f"- {ind.id} ({ind.display_name}) [{status}] — {ind.description[:80]}")
    return "\n".join(lines)


def finalize_indicator(
    session_id: str,
    name: str,
    display_name: str,
    description: str,
    country: str,
    subgroup: str,
    version: str,
    color_theme: str,
    shape_version: str = "1",
) -> str:
    if session_id not in uploads_cache:
        return "ERROR: No data loaded. Call validate_upload and transform_csv first."

    df = uploads_cache[session_id]
    INDICATORS_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"{country}__{name}__{subgroup}__{version}.csv"
    output_path = INDICATORS_DIR / filename
    df.to_csv(output_path, index=False)

    issues = validate_output_csv(output_path)
    if issues:
        output_path.unlink()
        return f"ERROR: Validation failed:\n" + "\n".join(f"  - {i}" for i in issues)

    meta = IndicatorMetadata(
        id=name,
        display_name=display_name,
        description=description,
        country=country,
        subgroups=[subgroup],
        version=version,
        color_theme=color_theme,
        shape_version=shape_version,
        csv_files=[filename],
        onboarding_notes=f"Onboarded via AI chat in session {session_id}",
    )

    existing = list_all_indicators()
    existing_meta = next((i for i in existing if i.id == name), None)
    if existing_meta:
        meta.subgroups = list(set(existing_meta.subgroups + [subgroup]))
        meta.csv_files = list(set(existing_meta.csv_files + [filename]))
        meta.created_at = existing_meta.created_at

    save_indicator(meta)

    row_count = len(df)
    year_range = ""
    if "year" in df.columns:
        year_range = f", years {df['year'].min()}-{df['year'].max()}"
    regions = ""
    if "state" in df.columns:
        n_regions = df["state"].nunique()
        regions = f", {n_regions} regions"

    summary = (
        f"Indicator '{display_name}' {FINALIZE_SUCCESS_SENTINEL}.\n"
        f"File: {filename} ({row_count} rows{year_range}{regions})\n"
        f"Color theme: {color_theme}\n"
    )

    import httpx
    service_url = os.getenv("SERVICE_URL", "http://service:5000")
    try:
        with open(output_path, "rb") as f:
            resp = httpx.post(
                f"{service_url}/indicators/register",
                files={"file": (filename, f, "text/csv")},
                timeout=30.0,
            )
        if resp.status_code == 200:
            summary += "The indicator is now available in the dashboard."
        else:
            detail = resp.text[:200]
            summary += (
                f"WARNING: Failed to register with dashboard service "
                f"(HTTP {resp.status_code}: {detail}). "
                f"The indicator may not appear until manually synced."
            )
    except Exception as e:
        summary += (
            f"WARNING: Could not reach dashboard service "
            f"({type(e).__name__}: {e}). "
            f"The indicator may not appear until manually synced."
        )

    return summary



def _sanitize_subgroup_name(value: str) -> str:
    s = str(value).strip()
    s = re.sub(r'[\s]+', '-', s)
    s = re.sub(r'[^A-Za-z0-9\-_]', '_', s)
    s = re.sub(r'_+', '_', s).strip('_')
    return s or "unknown"


def batch_finalize_indicator(
    session_id: str,
    name: str,
    display_name: str,
    description: str,
    country: str,
    version: str,
    color_theme: str,
    shape_version: str,
    subgroup_column: str,
    subgroup_mapping: dict | None = None,
    include_all: bool = True,
) -> str:
    if session_id not in uploads_cache:
        return "ERROR: No data loaded. Call validate_upload and transform_csv first."

    df = uploads_cache[session_id]

    if subgroup_column not in df.columns:
        if session_id in uploads_cache_original and subgroup_column in uploads_cache_original[session_id].columns:
            df[subgroup_column] = uploads_cache_original[session_id][subgroup_column]
        else:
            return f"ERROR: Column '{subgroup_column}' not found in data."

    unique_values = df[subgroup_column].dropna().unique().tolist()
    if len(unique_values) > 20:
        return f"ERROR: Too many subgroups ({len(unique_values)}). Maximum is 20."
    if not unique_values:
        return "ERROR: Subgroup column has no values."

    INDICATORS_DIR.mkdir(parents=True, exist_ok=True)
    mapping = subgroup_mapping or {}
    created = []
    warnings = []
    all_filenames = []

    tasks = [(v, mapping.get(str(v), _sanitize_subgroup_name(v))) for v in unique_values]
    if include_all:
        tasks.append((None, "all"))

    for raw_value, sg_name in tasks:
        if raw_value is None:
            subset = df.drop(columns=[subgroup_column])
        else:
            subset = df[df[subgroup_column] == raw_value].drop(columns=[subgroup_column])

        if subset.empty:
            warnings.append(f"  - {sg_name}: skipped (no rows)")
            continue

        filename = f"{country}__{name}__{sg_name}__{version}.csv"
        output_path = INDICATORS_DIR / filename
        subset.to_csv(output_path, index=False)

        issues = validate_output_csv(output_path)
        if issues:
            output_path.unlink()
            warnings.append(f"  - {sg_name}: validation failed — {'; '.join(issues)}")
            continue

        all_filenames.append(filename)
        created.append(sg_name)

        import httpx
        service_url = os.getenv("SERVICE_URL", "http://service:5000")
        try:
            with open(output_path, "rb") as f:
                httpx.post(
                    f"{service_url}/indicators/register",
                    files={"file": (filename, f, "text/csv")},
                    timeout=30.0,
                )
        except Exception:
            pass

    if not created:
        return "ERROR: No subgroups were created successfully.\n" + "\n".join(warnings)

    meta = IndicatorMetadata(
        id=name,
        display_name=display_name,
        description=description,
        country=country,
        subgroups=created,
        version=version,
        color_theme=color_theme,
        shape_version=shape_version,
        csv_files=all_filenames,
        onboarding_notes=f"Batch onboarded via AI chat in session {session_id}",
    )

    existing = list_all_indicators()
    existing_meta = next((i for i in existing if i.id == name), None)
    if existing_meta:
        meta.subgroups = list(set(existing_meta.subgroups + created))
        meta.csv_files = list(set(existing_meta.csv_files + all_filenames))
        meta.created_at = existing_meta.created_at

    save_indicator(meta)

    summary = (
        f"Indicator '{display_name}' {FINALIZE_SUCCESS_SENTINEL}.\n"
        f"Created {len(created)} subgroup(s): {', '.join(created)}\n"
        f"Color theme: {color_theme}\n"
    )
    if warnings:
        summary += "Warnings:\n" + "\n".join(warnings) + "\n"
    summary += "The indicator is now available in the dashboard."
    return summary


def _sanitize_python_output(out: str) -> str:
    lines = out.splitlines()
    kept = []
    for line in lines:
        if any(line.startswith(p) for p in METADATA_PREFIXES):
            kept.append(line)
        elif line.strip() == "":
            continue
        else:
            kept.append("META:[output hidden — save to file for user display]")
            break
    return "\n".join(kept)


def execute_python(code: str, session_id: str) -> tuple[str, list[str]]:
    tmpdir = TMP_DIR / session_id
    tmpdir.mkdir(parents=True, exist_ok=True)

    setup = "import matplotlib\nmatplotlib.use('Agg')\nimport warnings\nwarnings.filterwarnings('ignore')\n"
    auto_save = f"""
try:
    import matplotlib.pyplot as __plt, time as __t
    for __n in list(__plt.get_fignums()):
        __f = __plt.figure(__n)
        __p = f'{tmpdir}/autoplot_{{int(__t.time()*1000)}}_{{__n}}.png'
        __f.savefig(__p, dpi=150, bbox_inches='tight')
        print(f'{FILE_SAVED_PREFIX}{{__p}}')
        __plt.close(__f)
except Exception:
    pass
"""
    full_code = setup + code + "\n" + auto_save
    script_path = tmpdir / f"script_{int(time.time()*1000)}.py"
    script_path.write_text(full_code)
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True, text=True, timeout=120, cwd=str(INDICATORS_DIR),
        )
        out = result.stdout
        if result.returncode != 0:
            out += f"\nERROR: {result.stderr[:1500]}"
    except subprocess.TimeoutExpired:
        return "Error: code timed out", []

    files = re.findall(FILE_SAVED_PREFIX + r"(.+)", out)
    clean = _sanitize_python_output(out)
    clean = re.sub(FILE_SAVED_PREFIX + r".+\n?", "", clean).strip()
    return clean, [f"{session_id}/{Path(f.strip()).name}" for f in files]


def _normalize(s: str) -> str:
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()


GEO_COLUMNS = ["state", "dot_name", "region", "district", "location", "area", "admin", "name"]
SHAPE_RE = re.compile(r"^(.+)__l(\d+)__(\d+)\.shp\.pickle$")


def detect_shape_version(session_id: str) -> str:
    if session_id not in uploads_cache:
        return "ERROR: No data loaded. Call validate_upload first."

    df = uploads_cache[session_id]
    geo_col = next((c for c in df.columns if c.lower() in GEO_COLUMNS), None)
    if geo_col is None:
        return (
            "No geographic column found in the data. "
            "Expected one of: " + ", ".join(GEO_COLUMNS)
        )

    geo_values = set(df[geo_col].dropna().unique())
    if not geo_values:
        return "Geographic column is empty."

    geo_norm = {_normalize(str(v)): v for v in geo_values}

    if not SHAPES_DIR.exists():
        return "ERROR: Shapes directory not found at " + str(SHAPES_DIR)

    results = []
    for f in sorted(SHAPES_DIR.glob("*.shp.pickle")):
        m = SHAPE_RE.match(f.name)
        if not m:
            continue
        country, level, version = m.group(1), m.group(2), m.group(3)

        with open(f, "rb") as fh:
            geojson_dicts = pickle.load(fh)

        shape_dns = set(geojson_dicts.keys())
        shape_norm = {_normalize(dn): dn for dn in shape_dns}
        shape_suffixes = {}
        for norm_dn, orig_dn in shape_norm.items():
            last = norm_dn.rsplit(":", 1)[-1]
            shape_suffixes.setdefault(last, []).append(orig_dn)

        matched = 0
        for gn in geo_norm:
            if gn in shape_norm:
                matched += 1
            elif gn.rsplit(":", 1)[-1] in shape_suffixes:
                matched += 1

        rate = matched / len(geo_values)
        results.append({
            "country": country, "admin_level": level, "shape_version": version,
            "shape_regions": len(shape_dns), "data_regions": len(geo_values),
            "matched": matched, "match_rate": rate,
        })

    if not results:
        return "No shape files found in " + str(SHAPES_DIR)

    results.sort(key=lambda r: (-r["match_rate"], -r["matched"]))
    best = results[0]

    lines = [f"Shape version detection (geographic column: '{geo_col}', {len(geo_values)} unique values):\n"]
    for r in results:
        marker = "  ** BEST MATCH" if r is best else ""
        lines.append(
            f"  {r['country']} admin_level={r['admin_level']} shape_version={r['shape_version']}: "
            f"{r['matched']}/{r['data_regions']} matched ({r['match_rate']:.0%}), "
            f"{r['shape_regions']} shapes available{marker}"
        )

    lines.append(f"\nRecommended: shape_version={best['shape_version']}, admin_level={best['admin_level']}")
    if best["match_rate"] < 0.5:
        lines.append(
            "WARNING: Low match rate. The geographic names in the data may not align "
            "with any available shape boundaries. Ask the user about their data source."
        )
    return "\n".join(lines)


TOOL_DISPATCH = {
    "validate_upload": lambda inp, sid: validate_upload(sid, inp.get("sheet_name")),
    "preview_data": lambda inp, sid: preview_data(sid),
    "transform_csv": lambda inp, sid: transform_csv(sid, inp.get("transformations", {})),
    "list_existing_indicators": lambda inp, sid: list_existing_indicators(),
    "detect_shape_version": lambda inp, sid: detect_shape_version(sid),
    "finalize_indicator": lambda inp, sid: finalize_indicator(
        sid, inp["name"], inp["display_name"], inp["description"],
        inp["country"], inp["subgroup"], inp["version"], inp.get("color_theme", "RdBu"),
        inp.get("shape_version", "1"),
    ),
    "batch_finalize_indicator": lambda inp, sid: batch_finalize_indicator(
        sid, inp["name"], inp["display_name"], inp["description"],
        inp["country"], inp["version"], inp.get("color_theme", "RdBu"),
        inp.get("shape_version", "1"), inp["subgroup_column"],
        inp.get("subgroup_mapping"), inp.get("include_all", True),
    ),
}
