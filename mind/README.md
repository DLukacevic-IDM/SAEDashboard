# mind — Manage Indicators

AI-powered indicator onboarding service for the SAE Dashboard. Non-technical users upload CSV/Excel files and interact with a chat agent that validates, transforms, and registers their data as new dashboard indicators.

```bash
cd mind && pip install -r requirements.txt && python app.py  # :5020
# or
docker compose -f docker-compose.local.yml up mind
```

## Design Decisions

### Automatic Model Routing

Non-technical users cannot choose between LLM models, so the agent routes automatically based on task complexity.

| | **Opus 4.6 (`claude-opus-4-6`)** | **Sonnet 4.6 (`claude-sonnet-4-6`)** |
|---|---|---|
| **Tool-use loops** | Best — improved multi-step tool orchestration | Good, occasional missteps on complex chains |
| **Code generation** | Best — better at generating correct pandas/transformation code | Good for straightforward transforms |
| **Data reasoning** | Best — better at understanding messy real-world data schemas | Adequate for well-structured inputs |
| **Latency** | Slow (~5-15s per turn) | **~3-5x faster** per turn |
| **Cost** | $15/$75 per 1M tokens (input/output) | **$3/$15** per 1M tokens (5x cheaper) |
| **25-iteration ceiling** | Likely fewer turns (better planning) | May need more turns |

**Default**: Sonnet 4.6 — fast, cost-effective, sufficient for most onboarding tasks (column validation, renaming, reshaping to a fixed schema). Faster responses improve UX during SSE streaming, and 5x lower cost matters when each session runs 10-25 tool-use iterations.

**Auto-escalation to Opus 4.6** when complexity is detected after the first data validation. The agent scores complexity based on:

- **Data signals**: many columns (>10), missing standard SAE columns (state, pred, year), multi-sheet Excel files
- **Prompt signals**: user mentions merging, pivoting, restructuring, multiple indicators

The escalation is scored (threshold: 3 points). Once escalated, Opus stays active for the rest of the session. Users see a progress message: *"Complex data detected — switching to advanced model..."*

Configured via environment variables:
- `ANTHROPIC_MODEL_FAST` — default model (default: `claude-sonnet-4-6`)
- `ANTHROPIC_MODEL_STRONG` — escalation model (default: `claude-opus-4-6`)

### Shape Version Auto-Detection

The dashboard supports multiple versions of administrative boundary shapefiles per country. Different versions represent different administrative subdivisions — not just different geometry, but potentially different districts entirely:

| Version | Features | Description |
|---------|----------|-------------|
| v1 | ~79 districts | Standard GADM v4.1 boundaries |
| v3 | 4 super-regions | Aggregated zones |
| v4 | ~106 districts | Newer, finer-grained admin boundaries |

Version numbering is independent between indicator CSVs and shape files — there is no automatic pairing.

Users cannot be asked "which shape version was your data modeled against?" because they don't know the internals. Instead, the `detect_shape_version` tool infers it from the uploaded data by:

1. Finding the geographic column in the uploaded CSV (checks: `state`, `dot_name`, `region`, `district`, etc.)
2. Loading each available shape pickle and extracting its dot_names
3. Matching uploaded geographic values against each version using unicode-normalized comparison (handles accent mismatches like Sédhiou ↔ Sedhiou)
4. Ranking by match rate and recommending the best version

If the match rate is low (<50%), the agent asks the user to clarify their geographic naming.

The only user-facing question is about **geographic granularity**: *"Does your data cover the whole country, individual regions (like Dakar, Diourbel), or individual districts (like Pikine, Bambey)?"* — this determines admin level (l2 vs l3), and the specific shape version follows from name matching.

Shape files are mounted read-only into the mind container from `service/data/shapefiles/`.

### Visualization-Level Question

The system prompt guides the agent to ask about geographic granularity during the clarifying questions step. This is phrased in non-technical terms and lets the agent determine:
- **Admin level**: country (l1) vs regions (l2) vs districts (l3)
- **Shape version**: auto-detected via `detect_shape_version` after the state column exists

The detected `shape_version` is stored in `IndicatorMetadata` alongside the indicator, so the frontend can use the correct boundaries when rendering.

## API

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

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes* | — | *Or passed per-request via `api_key` field |
| `ANTHROPIC_MODEL_FAST` | No | `claude-sonnet-4-6` | Default model for simple tasks |
| `ANTHROPIC_MODEL_STRONG` | No | `claude-opus-4-6` | Escalation model for complex tasks |
| `SHAPES_DIR` | No | `/data/shapefiles` | Path to shape pickle files |
