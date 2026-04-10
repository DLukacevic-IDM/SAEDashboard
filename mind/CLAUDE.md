# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

An AI-powered indicator onboarding service (FastAPI, port 5020) for the SAE Dashboard. Users upload CSV/Excel files, interact with a Claude-powered chat agent that validates, transforms, and registers data as new dashboard indicators.

## Commands

```bash
# Run locally
cd mind && pip install -r requirements.txt && python app.py  # :5020

# Run via Docker Compose (from parent directory)
docker compose -f docker-compose.local.yml build mind
docker compose -f docker-compose.local.yml up mind

# Lint
flake8 --ignore=E501 mind/
```

No test suite exists yet.

## Architecture

```
app.py                          FastAPI entry, mounts all routers
controllers/
  upload.py     POST /upload     Accept CSV/Excel, create session, return validation
  chat.py       POST /chat       SSE stream — delegates to agentic loop
  indicators.py GET|PATCH|DELETE /indicators  Manage registered indicators
  data.py       GET /map, /timeseries, /indicators-data  Serve indicator data
  files.py      GET /files/{session_id}/{filename}  Serve generated plots
workflow/
  agent.py      Agentic loop: Claude + tool use, max 25 iterations, SSE progress
  tools.py      Tool implementations + TOOL_DISPATCH registry
  csv_validator.py  File loading, output validation, dot_name regex
storage/
  metadata_store.py  JSON-backed CRUD for IndicatorMetadata (Pydantic model)
```

## Key Patterns

**Agentic loop** (`workflow/agent.py`): Each `/chat` request runs a synchronous Claude loop — send messages → if `stop_reason == "tool_use"`, execute tools via `TOOL_DISPATCH`, append results, repeat. Streams SSE progress events. `_repair_session()` strips dangling tool_use blocks from history.

**Session state**: In-memory dict `sessions[session_id] → list[message]` for conversation history. `uploads_cache[session_id] → DataFrame` for data being transformed. Both are lost on restart.

**Tool dispatch**: `TOOL_DISPATCH` dict in `tools.py` maps tool name → lambda(input, session_id). `execute_python` is handled separately in the agent loop (returns files list). Python execution runs in subprocess with 120s timeout.

**Data flow**: Upload → `validate_upload` → `transform_csv` (iterative) → `finalize_indicator` → writes CSV to `/data/indicators/` + metadata to `/data/indicator_metadata.json`. The `data.py` controller then serves this data via `/map` and `/timeseries` endpoints.

**Column rename on read** (`controllers/data.py:_load_indicator`): `state→dot_name`, `pred→data`, `pred_upper→data_upper_bound`, `pred_lower→data_lower_bound`, `{indicator}→reference`, `se.{indicator}→reference_stderr` (then computes CI bounds from stderr).

## Data Format Contract

CSV filename: `{Country}__{Indicator}__{Subgroup}__{Version}.csv`

Required columns: `state`, `year`, `pred`, `pred_upper`, `pred_lower` (plus optional `{indicator}` and `se.{indicator}` for reference values).

`state` column uses dot_name format: `Africa:Country:Region[:District]` — validated by regex in `csv_validator.py`.

## Data Directories (runtime, `/data/`)

- `/data/uploads/{session_id}/` — user-uploaded files
- `/data/indicators/` — finalized CSV files (shared with main service)
- `/data/tmp/{session_id}/` — generated plots
- `/data/indicator_metadata.json` — indicator registry

## Environment Variables

- `ANTHROPIC_API_KEY` — required (or passed per-request via `api_key` field)
- `ANTHROPIC_MODEL_FAST` — default model (default: `claude-sonnet-4-6`)
- `ANTHROPIC_MODEL_STRONG` — escalation model for complex tasks (default: `claude-opus-4-6`)
- `SHAPES_DIR` — path to shape pickle files (default: `/data/shapefiles`)

## API Endpoints

```
POST /upload            (file: UploadFile) → {session_id, validation, sample_rows}
POST /chat              {session_id, message, api_key?} → SSE stream
GET  /indicators        → {indicators: [...]}
GET  /indicators/{id}   → indicator detail
PATCH /indicators/{id}  {hidden: bool}
DELETE /indicators/{id}
GET  /map               ?dot_name=&channel=&subgroup=&year=&admin_level=
GET  /timeseries        ?dot_name=&channel=&subgroup=
GET  /indicators-data   → dashboard-format indicator list
GET  /files/{session_id}/{filename}[/raw]
```
