# LLM Model Comparison for Indicator Onboarding

Context: The mind agent runs an agentic tool-use loop (up to 25 iterations) that validates, transforms, and registers CSV/Excel data as dashboard indicators.

| | **Opus 4.6 (`claude-opus-4-6`)** | **Sonnet 4.6 (`claude-sonnet-4-6`)** |
|---|---|---|
| **Tool-use loops** | Best — improved multi-step tool orchestration | Good, occasional missteps on complex chains |
| **Code generation** | Best — better at generating correct pandas/transformation code | Good for straightforward transforms |
| **Data reasoning** | Best — better at understanding messy real-world data schemas | Adequate for well-structured inputs |
| **Latency** | Slow (~5-15s per turn) | **~3-5x faster** per turn |
| **Cost** | $15/$75 per 1M tokens (input/output) | **$3/$15** per 1M tokens (5x cheaper) |
| **25-iteration ceiling** | Likely fewer turns (better planning) | May need more turns |

## Automatic Model Routing

The agent automatically selects the right model per session — no user action required.

**Default**: Sonnet 4.6 — fast, cost-effective, sufficient for most onboarding tasks.

**Auto-escalation to Opus 4.6** when complexity is detected after the first data validation. Triggers include:
- Many columns (>10) or non-standard column names
- Missing standard SAE columns (state, pred, year, etc.)
- Multi-sheet Excel files
- User prompt mentions merging, pivoting, restructuring, or multiple indicators

The escalation is scored (threshold: 3 points). Once escalated, Opus stays active for the rest of the session. Users see a progress message: *"Complex data detected — switching to advanced model..."*

**Environment variables**:
- `ANTHROPIC_MODEL_FAST` — default model (default: `claude-sonnet-4-6`)
- `ANTHROPIC_MODEL_STRONG` — escalation model (default: `claude-opus-4-6`)
