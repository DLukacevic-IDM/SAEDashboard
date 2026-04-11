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

---

## Testing: Adding a New Indicator

This walkthrough uses the test file `Senegal__Genomic__DrugR__4Testing.xlsx` — genomic antimalarial drug resistance surveillance data from 13 collection sites across 7 Senegal regions (130 rows, 16 columns, year 2023).

### What's in the test file

| Column | Example values | Purpose |
|--------|---------------|---------|
| `Region` | Tambacounda, Diourbel, Kolda | Administrative region (7 unique) |
| `Site` / `Code` | Gabou / GAB, Dialocoto / DIA | Collection site name and code (13 unique) |
| `Year` | 2023 | Single year |
| `Drug` | Sulfadoxine, Chloriquine, SP, ACT | Antimalarial drug (6 types) |
| `Res_Marker` | DHFR, crt, Kelch13, MDR | Resistance marker gene (6 types) |
| `Haplotype/SNP` | IRN, CVIET, NCS | Specific genetic variant (11 types) |
| `Type` | Mutant, Wild Type | Whether the variant confers resistance |
| `Haplotype frequency (%)` | 0.0 – 100.0 | **Main value** — prevalence of this variant |
| `Predicted drug sensitivities` | "resistance to pyrimethamine", "none" | Clinical interpretation |
| `Frequency category` | 0, 1, 2, 3 | Severity tier |
| `Recommendation` | "Maintain surveillance", "Attention to resistance needed" | Action guidance |

**Key challenge**
- This is NOT one indicator — each (Drug, Res_Marker, Haplotype/SNP, Type) combination is a separate sub-indicator. 
- The data also has multiple sites per region and uses site codes (GAB, DIA) that don't match standard shape boundaries.

### Step-by-step guide

#### 1. Start the service and upload

```bash
docker compose -f docker-compose.local.yml up mind
```

Upload `Senegal__Genomic__DrugR__4Testing.xlsx` via the UI or:
```bash
curl -F "file=@.local/Senegal__Genomic__DrugR__4Testing.xlsx" http://localhost:5020/upload
```
Note the `session_id` from the response.

#### 2. Send the initial prompt

> I want to add a drug resistance indicator for Senegal. This file has genomic surveillance data showing how common different antimalarial drug resistance markers are at collection sites. I'd like to focus on pyrimethamine resistance — specifically the DHFR-IRN mutation frequency — aggregated to the region level.

**Why this prompt**: It tells the agent exactly which slice of the data to use (DHFR marker, IRN haplotype, Mutant type) and that we want region-level aggregation. Without this specificity, the agent would have to ask several rounds of questions about which drug/marker combination to use.

**Expected**: The agent calls `validate_upload`, sees 16 columns / 130 rows, and will likely escalate to Opus (complexity score ≥ 3: >10 columns + no standard SAE columns).

#### 3. Agent asks clarifying questions — suggested answers

**Q: Which column contains the main indicator value?**
> The "Haplotype frequency (%)" column — it's the prevalence of each genetic variant as a percentage. That should become the `pred` column.

**Q: Do you have uncertainty bounds?**
> No. Please generate reasonable bounds — maybe ±5 percentage points, but clamped to 0–100.

**Q: How should the geographic data be mapped?**
> The "Region" column has the region names (Tambacounda, Diourbel, etc.). Since there are multiple sites per region, average the frequency values within each region. The dot_name format should be Africa:Senegal:{Region}. Note: "Touba" in the data is a city in the Diourbel region — map it to Diourbel.

**Q: Does your data cover the whole country, individual regions, or individual districts?**
> Individual regions — like Tambacounda, Kolda, Diourbel.

**Q: What subgroup does this represent?**
> "all" — this isn't broken down by age or demographic group.

#### 4. Expected agent actions

The agent should:
1. Filter to `Res_Marker == "DHFR"` and `Haplotype/SNP == "IRN"` and `Type == "Mutant"`
2. Replace "Touba" → "Diourbel" in the Region column
3. Group by Region and aggregate (mean of `Haplotype frequency (%)`)
4. Create the `state` column as `Africa:Senegal:{Region}`
5. Rename `Haplotype frequency (%)` → `pred`, generate `pred_upper` / `pred_lower`
6. Add `year` = 2023
7. Call `detect_shape_version` — should recommend **l2 v1** (6/7 regions match; Touba already remapped)
8. Call `finalize_indicator`

#### 5. Expected finalized output

The finalized CSV (`Senegal__dhfr_irn_resistance__all__1.csv`) should have ~6-7 rows:

| state | year | pred | pred_upper | pred_lower |
|-------|------|------|------------|------------|
| Africa:Senegal:Tambacounda | 2023 | ~78.0 | ~83.0 | ~73.0 |
| Africa:Senegal:Diourbel | 2023 | ~64.4 | ~69.4 | ~59.4 |
| ... | | | | |

#### 6. Verify

```bash
# Check the indicator was registered
curl http://localhost:5020/indicators

# Check the CSV was written
ls mind-data/indicators/Senegal__dhfr_irn_resistance__all__1.csv

# Check shape_version in metadata
cat mind-data/indicator_metadata.json | python3 -m json.tool
```

### What to watch for

- **Model escalation**: The 16-column file with no standard SAE columns should trigger auto-escalation to Opus. Look for the SSE event: *"Complex data detected — switching to advanced model..."*
- **Touba handling**: The agent must recognize Touba is not a standard region and remap it. If it doesn't, the shape version match rate will be lower.
- **Shape detection**: `detect_shape_version` should recommend l2 v1 with ~86-100% match rate (6/7 or 7/7 regions after Touba remap).
- **Aggregation**: Multiple sites per region must be averaged, not duplicated. The output should have one row per region per year.
- **Bounds clamping**: Generated upper bounds should not exceed 100 (since the value is a percentage).

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Yes* | — | *Or passed per-request via `api_key` field |
| `ANTHROPIC_MODEL_FAST` | No | `claude-sonnet-4-6` | Default model for simple tasks |
| `ANTHROPIC_MODEL_STRONG` | No | `claude-opus-4-6` | Escalation model for complex tasks |
| `SHAPES_DIR` | No | `/data/shapefiles` | Path to shape pickle files |
