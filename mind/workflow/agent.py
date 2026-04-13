import json
import os
import re
import time
from pathlib import Path

import anthropic

from workflow.tools import TOOL_DISPATCH, execute_python

MODEL_FAST = os.getenv("ANTHROPIC_MODEL_FAST", "claude-opus-4-6") #"claude-sonnet-4-6")
MODEL_STRONG = os.getenv("ANTHROPIC_MODEL_STRONG", "claude-opus-4-6")
MAX_ITERATIONS = 25
COMPLEXITY_THRESHOLD = 3

sessions: dict[str, list] = {}
session_models: dict[str, str] = {}


def _complexity_score(tool_output: str, user_message: str) -> int:
    score = 0

    if "Multiple sheets found" in tool_output:
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
            "Print FILE_SAVED:/path for each output file. "
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

### Dot Name Format
Colon-separated hierarchical identifiers:
- `Africa:Senegal` (country level)
- `Africa:Senegal:Dakar` (region/Admin Level 1)
- `Africa:Senegal:Dakar:Pikine` (district/Admin Level 2)

Senegal regions: Dakar, Diourbel, Fatick, Kaffrine, Kaolack, Kédougou, Kolda, Louga, Matam, Saint-Louis, Sédhiou, Tambacounda, Thiès, Ziguinchor

## Workflow
1. When the user uploads a file, call `validate_upload` to inspect it
2. Describe what you see and ask the user what the indicator represents
3. Ask clarifying questions:
   - Which column contains the main indicator value? (will become `pred`)
   - Do they have uncertainty bounds? If not, you can generate reasonable bounds.
   - Which column(s) map to geographic regions? How should they be converted to dot_names?
   - What year(s) does the data cover?
   - What subgroup does this represent?
   - **Geographic granularity** — ask the user: "Does your data cover the whole country, individual regions (like Dakar, Diourbel), or individual districts (like Pikine, Bambey)?" This determines the admin level for map visualization.
4. Use `transform_csv` to reshape the data step by step
5. Call `detect_shape_version` after the geographic/state column is present in the data. This auto-detects which map boundary version best matches the data. Use the recommended `shape_version` when finalizing. If the match rate is low, ask the user to clarify their geographic naming.
6. Use `execute_python` for complex transformations or to generate preview visualizations
7. Call `finalize_indicator` when the data is ready
8. After finalization, use `execute_python` to generate a preview visualization (map or chart)

## Important Rules
- Be conversational and helpful — users may not be technical
- Show progress at each step — describe what you found and what you're doing
- If the data doesn't have uncertainty bounds, create reasonable ones (e.g., pred ± 10% or pred ± 0.05)
- If the data doesn't have reference/survey values, leave those columns empty
- Always validate the final output before telling the user it's complete
- Session ID for file paths: {session_id}
- Upload directory: /data/uploads/{session_id}/
- Output directory: /data/indicators/
- Temp directory for plots: /data/tmp/{session_id}/

## Structured Forms

Instead of asking questions as plain text, emit structured forms so the user can select from dropdowns, radio buttons, and text fields. Wrap a JSON form definition in `<form>...</form>` tags within your response text.

### When to Use Forms
- When collecting information that has known, constrained options (column selection, subgroups, color themes, geographic granularity)
- When you can batch multiple related questions together
- Always set smart defaults based on your file analysis (e.g., a column named "estimate" likely maps to `pred`)

### When NOT to Use Forms
- For open-ended explanations or follow-up questions
- When asking about edge cases or ambiguous data
- For error messages or status updates

### Form Schema
```
<form>
{{
  "id": "unique_form_id",
  "fields": [
    {{"name": "field_name", "type": "select", "label": "Human label", "options": ["opt1", "opt2"], "default": "opt1", "required": true, "helperText": "Optional hint"}},
    {{"name": "field_name", "type": "radio", "label": "Human label", "options": ["A", "B", "C"], "default": "A", "required": true}},
    {{"name": "field_name", "type": "text", "label": "Human label", "default": "suggested value", "required": true}},
    {{"name": "field_name", "type": "textarea", "label": "Human label", "required": false}}
  ]
}}
</form>
```

Field types: `select` (dropdown), `radio` (radio buttons), `text` (single-line input), `textarea` (multi-line input), `checkbox` (boolean toggle).

### Recommended Form Sequence

**Form 1 — Column Mapping** (emit after `validate_upload`):
- `pred_column` (select): which column is the main indicator value — options from file columns, default to best guess
- `upper_bound_column` (select): upper bound column — include "None - generate automatically" option
- `lower_bound_column` (select): lower bound column — include "None - generate automatically" option
- `geo_column` (select): which column has geographic regions — options from file columns
- `year_column` (select): which column has years — options from file columns
- `granularity` (radio): "Country", "Regions", "Districts"

**Form 2 — Indicator Metadata** (emit after column mapping is confirmed and data is transformed):
- `indicator_name` (text): snake_case ID — suggest based on filename or content
- `display_name` (text): human-readable name
- `description` (textarea): what the indicator measures
- `country` (text): default "Senegal"
- `subgroup` (select): options ["all", "15-24", "25plus", "Parity-0", "Parity-1plus", "urban", "rural"]
- `version` (text): default "1"
- `color_theme` (select): options ["RdBu", "BuRd", "Viridis", "Blues", "Greens", "Reds", "Oranges", "Purples", "GnBu", "YlOrRd", "Spectral"]

You may include additional text before or after the `<form>` block to explain what you found in the data.
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
        "execute_python": tool_input.get("description", "Running analysis...")[:80],
    }
    return msgs.get(tool_name, f"Using {tool_name}...")


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
                    try:
                        form_data = json.loads(form_match.group(1))
                        text = re.sub(r'<form>.*?</form>', '', text, flags=re.DOTALL).strip()
                    except json.JSONDecodeError:
                        pass
                yield sse({"type": "response", "text": text, "files": list(dict.fromkeys(generated_files)), "form": form_data})
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
