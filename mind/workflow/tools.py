import re
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

from workflow.csv_validator import load_upload, get_upload_summary, validate_output_csv, MASTER_DATA_FILE_REGEX
from storage.metadata_store import (
    IndicatorMetadata, save_indicator, list_indicators as list_all_indicators
)

UPLOADS_DIR = Path("/data/uploads")
INDICATORS_DIR = Path("/data/indicators")
TMP_DIR = Path("/data/tmp")

uploads_cache: dict[str, pd.DataFrame] = {}


def validate_upload(session_id: str, sheet_name: str | None = None) -> str:
    upload_dir = UPLOADS_DIR / session_id
    files = list(upload_dir.glob("*"))
    if not files:
        return "ERROR: No uploaded file found for this session."

    path = files[0]
    try:
        df, info = load_upload(path, sheet_name)
        uploads_cache[session_id] = df
    except Exception as e:
        return f"ERROR: Failed to read file: {e}"

    summary = get_upload_summary(df)
    sheets_note = ""
    if info.get("sheets") and len(info["sheets"]) > 1:
        sheets_note = f"\nMultiple sheets found: {info['sheets']}. Currently reading: {sheet_name or info['sheets'][0]}"

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

    return (
        f"Indicator '{display_name}' saved successfully.\n"
        f"File: {filename} ({row_count} rows{year_range}{regions})\n"
        f"Color theme: {color_theme}\n"
        f"The indicator is now available in the dashboard."
    )


METADATA_PREFIXES = ("META:", "FILE_SAVED:", "SCHEMA:", "SHAPE:", "COLUMNS:", "DTYPE:", "ERROR:", "INFO:")


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
        print(f'FILE_SAVED:{{__p}}')
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

    files = re.findall(r"FILE_SAVED:(.+)", out)
    clean = _sanitize_python_output(out)
    clean = re.sub(r"FILE_SAVED:.+\n?", "", clean).strip()
    return clean, [f"{session_id}/{Path(f.strip()).name}" for f in files]


TOOL_DISPATCH = {
    "validate_upload": lambda inp, sid: validate_upload(sid, inp.get("sheet_name")),
    "preview_data": lambda inp, sid: preview_data(sid),
    "transform_csv": lambda inp, sid: transform_csv(sid, inp.get("transformations", {})),
    "list_existing_indicators": lambda inp, sid: list_existing_indicators(),
    "finalize_indicator": lambda inp, sid: finalize_indicator(
        sid, inp["name"], inp["display_name"], inp["description"],
        inp["country"], inp["subgroup"], inp["version"], inp.get("color_theme", "RdBu"),
    ),
}
