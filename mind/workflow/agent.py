import json
import logging
import os
import re
import time
from pathlib import Path
from string import Template

import anthropic

from workflow.constants import FINALIZE_SUCCESS_SENTINEL, MULTI_SHEET_SENTINEL, FILE_SAVED_PREFIX
from workflow.tools import TOOL_DISPATCH, execute_python

logger = logging.getLogger(__name__)

MODEL_FAST = os.getenv("ANTHROPIC_MODEL_FAST", "claude-opus-4-6") #"claude-sonnet-4-6")
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


_SYSTEM_PROMPT = Template("""\
You help users add new indicators to the SAE Dashboard by validating, transforming, and finalizing uploaded CSV/Excel data.

## Session
- session_id: $session_id
- Uploads: /data/uploads/$session_id/
- Output: /data/indicators/
- Plots: /data/tmp/$session_id/

## Rules
- NEVER ask questions as plain text — always use a `<form>` block. Only write short summaries (2-3 sentences) of what you found or did.
- NEVER list numbered questions for free-text answers. All user choices go through form fields.
- After the user describes their indicator, your VERY NEXT response MUST contain a `<form>` block.
- Complex decisions (aggregation method, category filters) → add as form fields, don't ask in text.
- Missing uncertainty bounds → generate automatically (pred ± 10% or pred ± 0.05), don't ask.
- Missing reference/survey values → leave `{indicator}` and `se.{indicator}` columns empty.
- Use `transform_csv` for simple operations (rename, drop, filter, apply). Use `execute_python` for pivots, merges, aggregations, multi-step logic, or when `transform_csv` fails.
- If a tool returns ERROR: diagnose, fix input, and retry — or switch to `execute_python`. Never show raw errors to the user.
- If the user sends free text instead of submitting a form, address their message, then re-emit the appropriate form.

## Workflow

### Step 1: User uploads file
The frontend already shows the file summary and preview. Wait for the user to describe what they want.

### Step 2: User describes their indicator
1. Call `validate_upload` to inspect columns and data
2. Write a SHORT summary (2-3 sentences)
3. Emit Form 1 (data configuration) immediately

### Step 3: User submits Form 1
1. Transform data using `transform_csv` / `execute_python` + call `detect_shape_version`
2. Emit Form 2 (indicator metadata) with a short note (e.g., "14 regions, years 2020-2023")

### Step 4: User submits Form 2
1. Call `finalize_indicator` with submitted values
2. Generate a preview visualization with `execute_python`
3. Short summary: indicator name, row count, regions, year range

## Data Format

CSV filename: `{Country}__{Indicator}__{Subgroup}__{Version}.csv` (e.g., `Senegal__modern_method__all__1.csv`)

Required columns: `state` (dot_name), `{indicator}` (reference, can be empty), `se.{indicator}` (stderr, can be empty), `year` (int), `pred` (central estimate), `pred_upper` (95% CI upper), `pred_lower` (95% CI lower).

Dot names — colon-separated hierarchy: `Africa:Senegal` (country), `Africa:Senegal:Dakar` (region), `Africa:Senegal:Dakar:Pikine` (district).

## Forms

Emit JSON inside `<form>...</form>` tags. Each field needs: `name`, `type`, `label`, `placeholder`, `required`. Optional: `options` (for select/radio), `default`, `helperText`, `validation`.

Field types: `select` (dropdown with options), `radio` (option buttons), `text` (single line), `textarea` (multi-line), `checkbox` (boolean).

### Form 1 — Data Configuration (emit after Step 2)
Build dynamically from the data. Required fields:
- `pred_column` (select): indicator value column — options from file columns, default to best guess
- `upper_bound_column` (select): upper bound — first option "None - generate automatically"
- `lower_bound_column` (select): lower bound — first option "None - generate automatically"
- `geo_column` (select): geographic column
- `year_column` (select): year column
- `granularity` (radio): Country / Regions / Districts — default from data analysis

Add when relevant: category filters (select, unique values + "All"), aggregation method (radio), subgroup selection (select).

### Form 2 — Indicator Metadata (emit after Step 3)
- `indicator_name` (text): snake_case ID, validation: `{"pattern": "^[a-z][a-z0-9_]*$$", "message": "Lowercase letters, numbers, underscores only"}`
- `display_name` (text): human-readable name
- `description` (textarea): what the indicator measures — pre-fill a default
- `country` (text): default "Senegal"
- `subgroup` (select): "all" + any identified subgroups
- `version` (text): default "1"
- `color_theme` (select): RdBu, BuRd, Viridis, Blues, Greens, Reds, Oranges, Purples, GnBu, YlOrRd, Spectral — default Viridis
""")


def _system_prompt(session_id: str) -> str:
    return _SYSTEM_PROMPT.substitute(session_id=session_id)


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
                        if block.name == "finalize_indicator" and FINALIZE_SUCCESS_SENTINEL in result_text:
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
