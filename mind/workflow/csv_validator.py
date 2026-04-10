import re
from pathlib import Path
import pandas as pd

MASTER_DATA_FILE_REGEX = re.compile(
    r'^(?P<country>.+)__(?P<channel>.+)__(?P<subgroup>.+)__(?P<version>.+)\.csv$')

DOT_NAME_PATTERN = re.compile(r'^[A-Za-z]+(?::[A-Za-z\s\-éèêëàâäôöùûüïîçÉÈÊËÀÂÄÔÖÙÛÜÏÎÇ]+)+$')

REQUIRED_OUTPUT_COLUMNS = ['state', 'year', 'pred', 'pred_upper', 'pred_lower']


def load_upload(path: Path, sheet_name: str | None = None) -> tuple[pd.DataFrame, dict]:
    info = {"file_type": path.suffix.lower(), "sheets": None}
    if path.suffix.lower() in ('.xlsx', '.xls'):
        xls = pd.ExcelFile(path)
        info["sheets"] = xls.sheet_names
        if sheet_name:
            df = pd.read_excel(xls, sheet_name=sheet_name)
        elif len(xls.sheet_names) == 1:
            df = pd.read_excel(xls, sheet_name=xls.sheet_names[0])
        else:
            df = pd.read_excel(xls, sheet_name=xls.sheet_names[0])
    else:
        df = pd.read_csv(path)
    info["columns"] = list(df.columns)
    info["row_count"] = len(df)
    info["dtypes"] = {col: str(df[col].dtype) for col in df.columns}
    return df, info


def validate_output_csv(path: Path) -> list[str]:
    """Validate a finalized CSV matches the SAE Dashboard format."""
    issues = []
    try:
        df = pd.read_csv(path)
    except Exception as e:
        return [f"Cannot read CSV: {e}"]

    for col in REQUIRED_OUTPUT_COLUMNS:
        if col not in df.columns:
            issues.append(f"Missing required column: {col}")

    if 'state' in df.columns:
        sample_states = df['state'].dropna().head(20)
        bad = [s for s in sample_states if not DOT_NAME_PATTERN.match(str(s))]
        if bad:
            issues.append(f"Invalid dot_name format in 'state': {bad[:3]}")

    for col in ['pred', 'pred_upper', 'pred_lower']:
        if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
            issues.append(f"Column '{col}' must be numeric")

    if 'pred' in df.columns and 'pred_lower' in df.columns and 'pred_upper' in df.columns:
        valid = df[['pred', 'pred_lower', 'pred_upper']].dropna()
        if len(valid) > 0:
            violations = valid[valid['pred_lower'] > valid['pred']].shape[0]
            violations += valid[valid['pred'] > valid['pred_upper']].shape[0]
            if violations > 0:
                issues.append(f"{violations} rows where pred_lower > pred or pred > pred_upper")

    if not MASTER_DATA_FILE_REGEX.match(path.name):
        issues.append(f"Filename '{path.name}' doesn't match pattern: {{Country}}__{{Indicator}}__{{Subgroup}}__{{Version}}.csv")

    return issues


def get_upload_summary(df: pd.DataFrame) -> str:
    lines = [
        f"Shape: {df.shape[0]} rows x {df.shape[1]} columns",
        f"Columns: {list(df.columns)}",
        f"Dtypes:\n{df.dtypes.to_string()}",
        f"\nFirst 3 rows:\n{df.head(3).to_string()}",
        f"\nNull counts:\n{df.isnull().sum().to_string()}",
    ]
    if 'year' in [c.lower() for c in df.columns]:
        year_col = [c for c in df.columns if c.lower() == 'year'][0]
        lines.append(f"\nYear range: {df[year_col].min()} - {df[year_col].max()}")
    return "\n".join(lines)
