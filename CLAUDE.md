# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A subnational map-based analytics dashboard (Senegal family planning data). Three services: React frontend, FastAPI backend, and an LLM agent service.

## Commands

### Docker (full stack)
```bash
docker compose -f docker-compose.local.yml build
docker compose -f docker-compose.local.yml up -d
# Dashboard at http://localhost
```

### Frontend (client/)
```bash
cd client && yarn install && yarn start   # dev server on :3000
cd client && yarn build                   # production build
cd client && yarn test --env=jsdom        # tests
```

### Backend (service/)
```bash
cd service && python app.py manage run    # API server on :5000
cd service && PYTHONPATH=${PWD}:${PYTHONPATH} py.test  # tests
```

### LLM service (LLM/)
```bash
cd LLM && python app.py manage run        # LLM server on :5001
```

### Linting
```bash
# Python
flake8 --ignore=E501 service/
# JS — ESLint (Google config) + Prettier
cd client && npx eslint src/
```

## Architecture

```
client/ (React 18, Redux, MUI, Leaflet, AmCharts)
  ├── src/components/    UI components + LLMClient
  ├── src/views/         Page views (dashboard, welcome, about)
  ├── src/redux/         Store, actions, reducers
  └── setupProxy.js      /api → service:5000, /llm → llm:5001

service/ (FastAPI, Python 3.9+, Uvicorn :5000)
  ├── app.py             Entry point, mounts routers
  ├── controllers/       API endpoints (map, indicators, timeseries, shapes, events, etc.)
  ├── schemas/           Pydantic models
  ├── helpers/           Data access utilities
  ├── data/              CSV data files (Senegal__*__*.csv), shapefiles, layer_data.json
  ├── mcp_server.py      FastMCP server (SSE on :5010)
  └── tests/             pytest (config in tests/controllers/pytest.ini)

LLM/ (FastAPI :5001, LangChain, Google Agent SDK)
  ├── app.py             Entry point
  ├── workflow/agent.py  Coordinator agent (LiteLLM multi-provider)
  ├── workflow/vector_db.py  ChromaDB RAG
  ├── workflow/sql_agent.py  SQL data queries
  └── controllers/       HTTP endpoints
```

## Data Flow

- Frontend proxies `/api/*` → service:5000 (REST: indicators, timeseries, shapes, events)
- Frontend proxies `/llm/*` → LLM:5001 (AI-powered data queries)
- LLM service connects to MCP server (SSE at :5010) for structured data access
- Backend reads CSV files from `service/data/data/` and shapefiles from `service/data/shapefiles/`

## Key Config Files

- `client/src/app_config.json` — UI settings (title, default country/region/indicator, themes)
- `service/config.yaml` — disaggregated indicators configuration
- `service/default_settings.py` — data directory paths, debug flags

## Documentation Index

Human-facing docs with SVG diagrams live in `docs/`. Read these for deep context:

- `docs/domain-knowledge.md` — SAE methodology, family planning indicators (modern_method, traditional_method, unmet_need), disaggregation dimensions (age, parity, residence), geographic hierarchy (dot names), data provenance
- `docs/data-ecosystem.md` — CSV naming convention (`{Country}__{Indicator}__{Subgroup}__{Version}.csv`), column structure (state/pred/pred_upper/pred_lower), shapefile format (pickled GeoJSON dicts), data prep tools
- `docs/features.md` — Dual choropleth maps, time-series charts with CI bounds, filtering controls, legend sync, difference maps, LLM chat, i18n (en/fr)
- `docs/architecture.md` — 4-service architecture (Client :3000, Service :5000, MCP :5010, LLM :5001), frontend Redux state management, backend data access pattern, API endpoint reference, agent routing logic
- `docs/data-workflows.md` — Offline data prep pipeline, runtime CSV loading/transformation (open_data_file → rename cols → compute CI → cache), request-response flow for /map /timeseries /shapes, LLM query paths (direct/SQL/RAG)

## Domain Concepts (Quick Reference)

```
Dot name:       Colon-separated hierarchy — Africa:Senegal:Dakar:Pikine
Admin levels:   0=continent, 1=country, 2=region, 3=district
Indicators:     modern_method, traditional_method, unmet_need
Subgroups:      all, 15-24, 25plus, Parity-0, Parity-1plus, urban, rural, combinations
CSV columns:    state, {indicator}, se.{indicator}, year, pred, pred_upper, pred_lower
Shape files:    {Country}__l{level}__{version}.shp.pickle (l2=regions, l3=districts)
Data caches:    DATA_CACHE (DataFrames), SHAPE_CACHE (GeoJSON dicts) in controller_helpers.py
CI formula:     reference ± (se × 1.96) for 95% confidence interval
```

## API Endpoints

```
GET /dot_names?dot_name=          → child regions
GET /indicators?dot_name=         → available indicators + metadata
GET /subgroups?dot_name=          → demographic subgroups
GET /shapes?dot_name=&admin_level=&shape_version= → GeoJSON boundaries
GET /map?dot_name=&channel=&subgroup=&year=&admin_level= → choropleth values
GET /timeseries?dot_name=&channel=&subgroup=      → trend data with bounds
GET /years?dot_name=&channel=&subgroup=            → start/end year
GET /events                       → timeline events
GET /layer_data                   → overlay layer JSON
GET /africa_map                   → continental GeoJSON
POST /llm/run {prompt, api_key?, model_name?}      → AI query response
```

## MCP Tools (service/mcp_server.py)

```
get_db_description()              → catalog of available data tables
get_db_schema(table_names)        → column info, types, sample values
get_db_query_guidelines()         → SQL patterns, value resolution rules
execute_db_query(sql_query)       → DuckDB execution against CSV files
```
