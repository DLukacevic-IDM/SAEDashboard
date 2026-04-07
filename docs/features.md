# Dashboard Features

## Dual Choropleth Maps

The dashboard displays two side-by-side interactive maps, enabling direct visual comparison of:
- Two different indicators (e.g., modern method vs. unmet need)
- The same indicator at two different time points
- The same indicator across different subgroups

Each map supports:
- **Click to select** a region/district and view its time-series chart below
- **Hover tooltips** showing indicator values
- **Admin level toggle** between regions (Admin 1) and districts (Admin 2)
- **Zoom and pan** controls
- **Image export** as PNG

## Time-Series Charts

Selecting a region on either map displays its trend chart below, showing:
- **Line charts** with model estimates (central prediction + 95% credible interval shading)
- **DHS reference data** overlay when available (survey-year point estimates with error bars)
- **Subgroup toggles** to show/hide specific demographic breakdowns on the same chart
- **Stacked bar charts** for categorical/composite indicators

## Filtering Controls

| Filter | Options |
|--------|---------|
| **Country** | Dropdown of available countries |
| **Admin Level** | Toggle between regions and districts |
| **Year** | Slider for map display year |
| **Month** | Slider (when monthly data is available) |
| **Indicator** | Independent selection for each map |
| **Subgroup** | Demographic disaggregation filter |
| **Color theme** | 40+ color palettes (RdBu, Viridis, etc.) |
| **Legend mode** | Equal interval or custom bounds |
| **Legend max** | Set upper bound of color scale (0-100%) |

## Comparison Tools

- **Legend sync** — lock both maps to the same color scale for fair comparison
- **Difference map** — show the arithmetic difference between the two maps
- **Independent year selection** — each map can show a different year

## AI Assistant (LLM Integration)

A side-panel chat interface powered by an LLM agent that can:
- **Answer general health questions** using model knowledge
- **Query indicator data** via SQL against the CSV dataset (MCP integration)
- **Search uploaded documents** using RAG (Retrieval-Augmented Generation)

Supports multiple model backends: GPT-4o, GPT-4o-mini, Claude, local Llama 3.2.

Example queries:
- *"Which region has the highest modern method coverage in 2020?"*
- *"Compare modern method trends between Dakar and Ziguinchor"*
- *"What barriers to family planning are mentioned in the health reports?"*

## Internationalization

Full French/English language toggle — all UI labels, filter names, and navigation are localized using `react-intl`.

## Navigation

| Page | Description |
|------|-------------|
| **Welcome** | Landing page with project overview |
| **Dashboard** | Main analytics view with maps and charts |
| **About** | Background on SAE methodology |
| **Instructions** | User guide |
| **Libraries** | Third-party dependency attributions |
