import json
import logging
import os
import re
import time
from pathlib import Path

import anthropic

from workflow.constants import FINALIZE_SUCCESS_SENTINEL, MULTI_SHEET_SENTINEL, FILE_SAVED_PREFIX
from workflow.tools import TOOL_DISPATCH, execute_python

logger = logging.getLogger(__name__)

MODEL_FAST = os.getenv("ANTHROPIC_MODEL_FAST", "claude-sonnet-4-6")
#MODEL_FAST = os.getenv("ANTHROPIC_MODEL_FAST",ß "claude-opus-4-6")
MODEL_STRONG = os.getenv("ANTHROPIC_MODEL_STRONG", "claude-opus-4-6")
MAX_ITERATIONS = 25
COMPLEXITY_THRESHOLD = 3

sessions: dict[str, list] = {}
session_models: dict[str, str] = {}


def _complexity_score(tool_output: str, user_message: str) -> int:
    score = 0

    if MULTI_SHEET_SENTINEL in tool_output:
        score += 2
    col_match = re.search(r"(\d+) columns", tool_output)
    if col_match:
        n = int(col_match.group(1))
        score += 2 if n > 10 else (1 if n > 7 else 0)

    standard_cols = ["state", "pred", "pred_upper", "pred_lower", "year"]
    present = sum(1 for c in standard_cols if re.search(rf"\b{c}\b", tool_output))
    if present <= 1:
        score += 2
    elif present <= 3:
        score += 1

    complex_patterns = [
        r"multiple\s+indicators?", r"\bmerge\b|\bjoin\b",
        r"\bpivot\b|\breshape\b|\bmelt\b", r"custom\s+calculat",
        r"\bderiv\w*\b|\baggreg", r"cross[\s-]?tab",
        r"combin.*(?:file|sheet|dataset)", r"\brestructur",
    ]
    for pattern in complex_patterns:
        if re.search(pattern, user_message, re.IGNORECASE):
            score += 1

    return score

TOOLS = [
    {
        "name": "validate_upload",
        "description": "Validate an uploaded CSV or Excel file. Returns column info, row count, data types, and sample rows. For multi-sheet Excel files, specify sheet_name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sheet_name": {"type": "string", "description": "Sheet name for multi-sheet Excel files (optional)"},
            },
            "required": [],
        },
    },
    {
        "name": "preview_data",
        "description": "Show summary statistics and sample rows of the currently loaded data.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "transform_csv",
        "description": (
            "Transform the loaded data. Supports: rename_columns (dict), drop_columns (list), "
            "add_state_column (Python lambda string for constructing dot_name from row), "
            "filter_expr (pandas query string), value_transforms (dict of column: lambda string)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "transformations": {
                    "type": "object",
                    "description": "Dict with keys: rename_columns, drop_columns, add_state_column, filter_expr, value_transforms",
                },
            },
            "required": ["transformations"],
        },
    },
    {
        "name": "list_existing_indicators",
        "description": "List all indicators currently registered in the indicator manager.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "detect_shape_version",
        "description": (
            "Auto-detect which map boundary version best matches the geographic names in the uploaded data. "
            "Compares the data's geographic column against all available shape files and reports match rates. "
            "Call this after validate_upload and before finalize_indicator."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "finalize_indicator",
        "description": (
            "Write the transformed data as a finalized CSV indicator file and register its metadata. "
            "The data must have columns: state, {indicator}, se.{indicator}, year, pred, pred_upper, pred_lower. "
            "The state column must use dot_name format: Africa:Country:Region[:District]."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Indicator ID (snake_case, e.g. 'drug_resistance')"},
                "display_name": {"type": "string", "description": "Human-readable name"},
                "description": {"type": "string", "description": "What this indicator measures"},
                "country": {"type": "string", "description": "Country name (e.g. 'Senegal')"},
                "subgroup": {"type": "string", "description": "Subgroup name (e.g. 'all', '15-24')"},
                "version": {"type": "string", "description": "Version number (e.g. '1')"},
                "color_theme": {"type": "string", "description": "Color palette for map (e.g. 'RdBu', 'Viridis')"},
                "shape_version": {"type": "string", "description": "Map boundary version from detect_shape_version (e.g. '1')"},
            },
            "required": ["name", "display_name", "description", "country", "subgroup", "version"],
        },
    },
    {
        "name": "batch_finalize_indicator",
        "description": (
            "Finalize an indicator with MULTIPLE subgroups from a single transformed dataset. "
            "Splits the data by a subgroup column and creates one CSV file per unique value. "
            "Optionally also creates an 'all' subgroup from the full unfiltered data. "
            "Use this instead of finalize_indicator when the data contains a subgroup column."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Indicator ID (snake_case, e.g. 'drug_resistance')"},
                "display_name": {"type": "string", "description": "Human-readable name"},
                "description": {"type": "string", "description": "What this indicator measures"},
                "country": {"type": "string", "description": "Country name (e.g. 'Senegal')"},
                "version": {"type": "string", "description": "Version number (e.g. '1')"},
                "color_theme": {"type": "string", "description": "Color palette for map (e.g. 'RdBu', 'Viridis')"},
                "shape_version": {"type": "string", "description": "Map boundary version from detect_shape_version (e.g. '1')"},
                "subgroup_column": {"type": "string", "description": "Column name containing subgroup values to split by"},
                "subgroup_mapping": {
                    "type": "object",
                    "description": "Optional mapping from raw column values to sanitized subgroup names (e.g. {'Age 15-24': '15-24'})",
                },
                "include_all": {"type": "boolean", "description": "Also create an 'all' subgroup from the full dataset (default true)"},
                "all_aggregation": {"type": "string", "enum": ["mean", "median", "sum"], "description": "How to aggregate values across subgroups for the 'all' file (default 'mean')"},
                "all_group_columns": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Columns to group by when building the 'all' subgroup (e.g. ['state', 'year']). If omitted, auto-detected.",
                },
            },
            "required": ["name", "display_name", "description", "country", "version", "subgroup_column"],
        },
    },
    {
        "name": "execute_python",
        "description": (
            "Execute Python code for data analysis and visualization. "
            "pandas, matplotlib (Agg auto-set), numpy available. "
            f"Print {FILE_SAVED_PREFIX}/path for each output file. "
            "The uploaded data is available at /data/uploads/{session_id}/. "
            "Finalized indicators are at /data/indicators/."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute"},
                "description": {"type": "string", "description": "Brief description of what this code does"},
            },
            "required": ["code", "description"],
        },
    },
]


def _system_prompt(session_id: str) -> str:
    return f"""You are an AI assistant that helps users add new indicators to the SAE Dashboard.

## Your Role
Help users onboard new health/research indicator data into the dashboard. Users upload CSV or Excel files that may not match the expected format. Guide them through describing, validating, transforming, and finalizing their data.

## SAE Dashboard Data Format

### File Naming Convention
Output CSV files must follow: `{{Country}}__{{Indicator}}__{{Subgroup}}__{{Version}}.csv`
Example: `Senegal__modern_method__all__1.csv`

### Required Output Columns
| Column | Description |
|--------|-------------|
| `state` | Dot-name hierarchical identifier: `Africa:Country:Region[:District]` |
| `{{indicator}}` | Reference/observed value (can be empty if no survey data) |
| `se.{{indicator}}` | Standard error of reference (can be empty) |
| `year` | Year of observation (integer) |
| `pred` | Model prediction / central estimate |
| `pred_upper` | Upper bound (95% CI) |
| `pred_lower` | Lower bound (95% CI) |

### Multi-Subgroup Indicators
An indicator can have multiple subgroups. Each subgroup gets its own CSV file with the same columns but different data.
Example: `Senegal__drug_resistance__DHFR-IRN__1.csv`, `Senegal__drug_resistance__crt-CVIET__1.csv`, plus an optional `Senegal__drug_resistance__all__1.csv` for the full dataset.
When the uploaded data has a column that distinguishes subgroups (e.g., marker type, age group, residence), use `batch_finalize_indicator` to split it into per-subgroup CSV files automatically.

### Dot Name Format
Colon-separated hierarchical identifiers:
- `Africa:Senegal` (country level)
- `Africa:Senegal:Dakar` (region/Admin Level 1)
- `Africa:Senegal:Dakar:Pikine` (district/Admin Level 2)

Senegal regions: Dakar, Diourbel, Fatick, Kaffrine, Kaolack, Kédougou, Kolda, Louga, Matam, Saint-Louis, Sédhiou, Tambacounda, Thiès, Ziguinchor

## Workflow — FOLLOW THESE STEPS EXACTLY

### Step 1: User uploads file
The frontend shows the user a file summary and data preview automatically. You do NOT need to describe the file — the user already sees it. Wait for the user to send a message describing what they want.

### Step 2: User describes their indicator
The user sends a message describing what the data represents and what indicator they want. When you receive this message:
1. Call `validate_upload` to inspect the file columns and data
2. Analyze the data in the context of what the user described
3. Write a SHORT summary (2-3 sentences max) of what you found
4. **IMMEDIATELY emit a structured form** (Form 1) with all the questions you need answered — do NOT ask questions as plain text

### Step 3: User submits Form 1
When the user submits the form:
1. Use `transform_csv`, `execute_python`, and `detect_shape_version` to transform the data
2. When transformation is complete, emit **Form 2** (indicator metadata) so the user can name and configure the indicator
3. Include a short note about what you did (e.g., "Data transformed: 14 regions, years 2020-2023")

### Step 4: User submits Form 2
When the user submits the metadata form:
1. If the user selected a subgroup column in Form 1, call `batch_finalize_indicator` with the `subgroup_column` and any `subgroup_mapping`. Otherwise call `finalize_indicator` with the submitted values.
2. Generate a preview visualization with `execute_python`
3. Respond with a short what-was-done summary (indicator name, subgroups created, row count, regions, year range)

## CRITICAL RULES
- **NEVER ask questions as plain text.** Always use a `<form>` block. The only plain text you should write is short summaries of what you found or did.
- **NEVER list numbered questions** for the user to answer in free text. Use form fields instead.
- After the user describes their indicator in Step 2, your VERY NEXT response MUST contain a `<form>` block.
- If the data requires complex decisions (e.g., aggregation method, filtering by drug/marker), add those as select/radio fields in the form — do not ask about them in text.
- If the data doesn't have uncertainty bounds, generate reasonable ones automatically (pred ± 10% or pred ± 0.05) — do not ask the user about this.
- If the data doesn't have reference/survey values, leave those columns empty.
- Be brief. The user does not need paragraph-length explanations.
- Session ID for file paths: {session_id}
- Upload directory: /data/uploads/{session_id}/
- Output directory: /data/indicators/
- Temp directory for plots: /data/tmp/{session_id}/

## Structured Forms

Wrap a JSON form definition in `<form>...</form>` tags within your response text. You may include a short sentence or two before the form block, but keep it minimal.

### Form Schema
```
<form>
{{
  "id": "unique_form_id",
  "fields": [
    {{"name": "field_name", "type": "select", "label": "Human label", "placeholder": "Select an option...", "options": ["opt1", "opt2"], "default": "opt1", "required": true, "helperText": "Optional hint"}},
    {{"name": "field_name", "type": "radio", "label": "Human label", "options": ["A", "B", "C"], "default": "A", "required": true}},
    {{"name": "field_name", "type": "text", "label": "Human label", "placeholder": "e.g. example_value", "default": "suggested value", "required": true}},
    {{"name": "field_name", "type": "textarea", "label": "Human label", "placeholder": "Describe...", "required": false}}
  ]
}}
</form>
```

Field types: `select` (dropdown), `radio` (radio buttons), `text` (single-line input), `textarea` (multi-line input), `checkbox` (boolean toggle).

Every field MUST have both a `label` and a `placeholder`.

### Form 1 — Data Configuration (emit in Step 2, after user describes their indicator)

Build this form dynamically based on what you find in the data AND what the user described. Include ALL of these, plus any data-specific fields:

Required fields:
- `pred_column` (select): main indicator value column — options from file columns, default to best guess
- `upper_bound_column` (select): upper bound column — include "None - generate automatically" as first option
- `lower_bound_column` (select): lower bound column — include "None - generate automatically" as first option
- `geo_column` (select): geographic regions column — options from file columns
- `year_column` (select): year column — options from file columns
- `granularity` (radio): "Country", "Regions", "Districts" — default based on data analysis

Data-specific fields (add when relevant):
- If data has multiple categories that could be filtered (e.g., drugs, markers, types): add a select field for each with all unique values plus "All" option
- If data needs aggregation from a finer level to a coarser level: add a radio field for aggregation method (e.g., "Weighted average", "Simple average", "Sum")
- If data has a column whose values represent different subgroups/categories that should be displayed separately in the dashboard (e.g., drug markers, age groups, residence type): add a `subgroup_column` (select) field listing candidate columns plus "None - single subgroup only" as the first option. Do NOT drop this column during transformation — `batch_finalize_indicator` needs it.

### Form 2 — Indicator Metadata (emit in Step 3, after transformation)

- `indicator_name` (text): snake_case ID — suggest based on data content. MUST include validation: `{{"pattern": "^[a-z][a-z0-9_]*$", "message": "Must be lowercase letters, numbers, and underscores only (e.g. drug_resistance)"}}`
- `display_name` (text): human-readable name — suggest based on user's description
- `description` (textarea): what the indicator measures — pre-fill with a sensible default
- `country` (text): default "Senegal"
- `version` (text): default "1"
- `color_theme` (select): options ["RdBu", "BuRd", "Viridis", "Blues", "Greens", "Reds", "Oranges", "Purples", "GnBu", "YlOrRd", "Spectral"], default "Viridis"

If a `subgroup_column` was selected in Form 1:
- Show a read-only text field listing the detected subgroup values (e.g., "DHFR-IRN, crt-CVIET, MDR-NFD, ...")
- `include_all` (checkbox): "Also create an 'all' subgroup from the full dataset" — default checked
- `all_aggregation` (radio): "mean", "median", "sum" — how to aggregate values across subgroups for the 'all' file. Default "mean". For percentage data, "mean" is almost always correct.
- `all_group_columns` (text): comma-separated column names to group by when building the 'all' subgroup. Pre-fill with the columns that should be kept as dimensions (e.g., "state, year"). The remaining numeric columns will be aggregated.
- Do NOT include a single `subgroup` select field

If NO `subgroup_column` was selected:
- `subgroup` (select): options — include "all" plus any subgroups identified in the data, default "all"
"""


def content_to_dicts(content) -> list:
    out = []
    for b in content:
        if b.type == "text":
            out.append({"type": "text", "text": b.text})
        elif b.type == "tool_use":
            out.append({"type": "tool_use", "id": b.id, "name": b.name, "input": b.input})
    return out


def _repair_session(messages: list) -> list:
    while messages and messages[-1]["role"] == "assistant":
        content = messages[-1]["content"]
        if any(b.get("type") == "tool_use" for b in content):
            messages.pop()
        else:
            break
    return messages


def _progress_msg(tool_name: str, tool_input: dict) -> str:
    msgs = {
        "validate_upload": "Validating uploaded file...",
        "preview_data": "Analyzing data...",
        "transform_csv": "Transforming data...",
        "list_existing_indicators": "Checking existing indicators...",
        "detect_shape_version": "Detecting map boundary version...",
        "finalize_indicator": "Finalizing indicator...",
        "batch_finalize_indicator": "Creating indicator with multiple subgroups...",
        "execute_python": tool_input.get("description", "Running analysis...")[:80],
    }
    return msgs.get(tool_name, f"Using {tool_name}...")


CHATS_DIR = Path("/data/chats")


def _save_chat_history(session_id: str, indicator_id: str):
    history = sessions.get(session_id, [])
    clean = []
    for msg in history:
        if msg["role"] == "user":
            content = msg["content"]
            if isinstance(content, str):
                clean.append({"role": "user", "content": content})
        elif msg["role"] == "assistant":
            content = msg["content"]
            if isinstance(content, str):
                clean.append({"role": "assistant", "content": content})
            elif isinstance(content, list):
                texts = [b["text"] for b in content if b.get("type") == "text" and b.get("text", "").strip()]
                if texts:
                    combined = "\n\n".join(texts)
                    combined = re.sub(r'<form>.*?</form>', '', combined, flags=re.DOTALL).strip()
                    if combined:
                        clean.append({"role": "assistant", "content": combined})
    CHATS_DIR.mkdir(parents=True, exist_ok=True)
    (CHATS_DIR / f"{indicator_id}.json").write_text(json.dumps(clean, indent=2))


def run_agent_stream(session_id: str, user_message: str, api_key: str | None = None):
    def sse(event: dict) -> str:
        return f"data: {json.dumps(event)}\n\n"

    try:
        if api_key:
            client = anthropic.Anthropic(api_key=api_key)
        else:
            client = anthropic.Anthropic()

        if session_id not in sessions:
            sessions[session_id] = []

        if user_message.strip() == "/clear":
            sessions[session_id] = []
            yield sse({"type": "response", "text": "Session cleared.", "files": []})
            return

        _repair_session(sessions[session_id])
        sessions[session_id].append({"role": "user", "content": user_message})

        generated_files: list[str] = []
        indicator_created = False
        progress = 5
        model = session_models.get(session_id, MODEL_FAST)
        escalated = model == MODEL_STRONG
        yield sse({"type": "progress", "progress": progress, "message": "Thinking..."})

        for _ in range(MAX_ITERATIONS):
            response = client.messages.create(
                model=model,
                max_tokens=8192,
                system=_system_prompt(session_id),
                tools=TOOLS,
                messages=sessions[session_id],
            )
            sessions[session_id].append({
                "role": "assistant",
                "content": content_to_dicts(response.content),
            })

            if response.stop_reason == "end_turn":
                text = "".join(b.text for b in response.content if b.type == "text")
                form_data = None
                form_match = re.search(r'<form>(.*?)</form>', text, re.DOTALL)
                if form_match:
                    raw_json = form_match.group(1).strip()
                    try:
                        form_data = json.loads(raw_json)
                        text = re.sub(r'<form>.*?</form>', '', text, flags=re.DOTALL).strip()
                    except json.JSONDecodeError as exc:
                        logger.warning("Form JSON parse failed in session %s: %s — raw: %.200s", session_id, exc, raw_json)
                        text = re.sub(r'<form>.*?</form>', '', text, flags=re.DOTALL).strip()
                        text += "\n\n(Warning: A form was generated but could not be parsed. Please describe your preferences in text.)"
                yield sse({"type": "response", "text": text, "files": list(dict.fromkeys(generated_files)), "form": form_data, "indicator_created": indicator_created})
                break

            if response.stop_reason != "tool_use":
                yield sse({"type": "error", "message": f"Unexpected stop: {response.stop_reason}"})
                break

            tool_results = []
            try:
                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    progress = min(progress + 15, 85)
                    yield sse({"type": "progress", "progress": progress, "message": _progress_msg(block.name, block.input)})

                    if block.name == "execute_python":
                        out, files = execute_python(block.input["code"], session_id)
                        generated_files.extend(files)
                        file_notes = "\n".join(f"Saved: /data/tmp/{f}" for f in files) if files else ""
                        result_text = "\n".join(filter(None, [out, file_notes])).strip()
                    elif block.name in TOOL_DISPATCH:
                        result_text = TOOL_DISPATCH[block.name](block.input, session_id)
                        if block.name in ("finalize_indicator", "batch_finalize_indicator") and FINALIZE_SUCCESS_SENTINEL in result_text:
                            indicator_created = True
                            _save_chat_history(session_id, block.input.get("name", session_id))
                    else:
                        result_text = f"Unknown tool: {block.name}"

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_text,
                    })
            except Exception:
                sessions[session_id].pop()
                raise

            if not escalated:
                combined = " ".join(r.get("content", "") for r in tool_results)
                if _complexity_score(combined, user_message) >= COMPLEXITY_THRESHOLD:
                    model = MODEL_STRONG
                    session_models[session_id] = model
                    escalated = True
                    yield sse({"type": "progress", "progress": progress, "message": "Complex data detected — switching to advanced model..."})

            sessions[session_id].append({"role": "user", "content": tool_results})
        else:
            yield sse({"type": "error", "message": "Max iterations reached"})

    except anthropic.AuthenticationError:
        yield sse({"type": "error", "message": "Invalid API key. Please provide a valid Anthropic API key."})
    except Exception as e:
        yield sse({"type": "error", "message": str(e)})
