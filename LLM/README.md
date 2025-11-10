
### DATA Setup

#### Linux:
1. Open a terminal and navigate to the root of the repository.
2. Change directory to 'LLM': cd LLM

#### Windows:
Open a terminal and navigate to the root of the repository.
Change directory to 'LLM': cd LLM

### Development Environment Setup
1. Open a terminal and navigate to the root of the repository.

2. Create a new virtual environment named 'venv': `python -m venv venvLLM`

3. Activate the virtual environment by running the following command in linux `source venvLLM/bin/activate`. 
In windows, the command is `venvLLM\Scripts\activate`

4. Install the required dependencies:
```
cd service
pip install -r requirements_dev.txt
```

5. Install the package:
```
pip install -e .
```

6. Install azcopy.  Looks like current version doesn't support windows / macOS

7. Obtain url from IDM and then run the following command to download LLM
```
azcopy cp --recursive "url" .
```

8. Set the following environment variables:
- `PYTHONPATH=%PYTHONPATH%;C:\Your\Project\Root`


#### Service Start
1. Open a terminal and navigate to the root of the repository.
2. Change directory to 'llm': cd llm
3. Run the application: `python app.py manage run`

## Architecture Diagram

```
                    ┌─────────────────────────────────────────────────────────────┐
                    │                         LLM Layer                           │
                    │                                                             │
                    │  ┌────────────────────────────────────────────────────┐     │
                    │  │  Coordinator Agent (LLM/workflow/agent.py)         │     │
                    │  │                                                    │     │
                    │  │  Decides which tool(s) to use based on query       │     │
                    │  └──────┬──────────────────┬───────────────┬──────────┘     │
                    │         │                  │               │                │
                    │         │ Tool 1           │ Tool 2        │ Tool 3         │
                    │         ▼                  ▼               ▼                │
                    │  ┌───────────────┐   ┌──────────────┐  ┌──────────────┐     │
                    │  │ ask_vector_db │   │ general_     │  │ MCPToolset   │     │
                    │  │               │   │ question     │  │              │     │
                    │  │ RAG queries   │   │              │  │ Data queries │     │
                    │  │ for docs      │   │ LLM direct   │  │ via MCP      │     │
                    │  └──────┬────────┘   └──────────────┘  └──────┬───────┘     │
                    └─────────┼───────────────────────────────────┼───────────────┘
                              │                                   │
                              │                                   │ SSE Connection
                              │                                   │ (localhost:5010/sse)
                 ┌────────────┘                                   │
                 │                                                │
                 ▼                                                ▼
┌───────────────────────────────────┐        ┌─────────────────────────────────────────────────────┐
│    RAG System (LLM/workflow/)     │        │       MCP Server Layer (service/)                   │
│                                   │        │                                                     │
│  ┌──────────────────────────────┐ │        │  ┌───────────────────────────────────────────────┐  │
│  │  vector_db.py                │ │        │  │  mcp_server.py (FastMCP/SSE)                  │  │
│  │  - Document retrieval        │ │        │  │                                               │  │
│  │  - Context injection         │ │        │  │  MCP Tools:                                   │  │
│  │  - Answer generation         │ │        │  │  • get_db_description                         │  │
│  └──────┬────────────────────┬──┘ │        │  │  • get_db_query_guidelines                    │  │
│         │ Query              │    │        │  │  • get_db_schema                              │  │
│         ▼                    │    │        │  │  • execute_db_query                           │  │
│  ┌──────────────┐            │    │        │  │                                               │  │
│  │  ChromaDB    │◄───────────┘    │        │  └────────────────┬──────────────────────────────┘  │
│  │  Vector DB   │   Embeddings    │        └───────────────────┼─────────────────────────────────┘
│  │              │   (Similarity)  │                            │
│  └──────────────┘                 │                            │
│         ▲                         │                            │
│         │ Embedding               │                            ▼
│         │ (BAAI/bge-small-en)     │         ┌───────────────────────────────────────────┐
│  ┌──────┴──────────┐              │         │     Service Layer (service/helpers/)      │
│  │  Embedding      │              │         │                                           │
│  │  Model          │              │         │  ┌────────────────────────────────────┐   │
│  │  (HuggingFace)  │              │         │  │  Data Access Layer                 │   │
│  └─────────────────┘              │         │  │  - controller_helpers.py           │   │
│         ▲                         │         │  │  - dot_name.py                     │   │
│         │ Documents               │         │  │  - get_dataframe()                 │   │
│         │                         │         │  │  - get_channels()                  │   │
│  ┌──────┴──────────┐              │         │  └───────────────┬────────────────────┘   │ 
│  │  PDF Documents  │              │         └──────────────────┼────────────────────────┘
│  │  (pdf_data/)    │              │                            │
│  │                 │              │                            │ Read CSV data
│  │  - Health       │              │                            ▼
│  │    bulletins    │              │        ┌────────────────────────────────────────────┐
│  │  - Research     │              │        │         Data Files (service/data/)         │
│  │    papers       │              │        │                                            │
│  │  - Reports      │              │        │  • Indicator CSV files (by country)        │
│  └─────────────────┘              │        │  • Channels (indicators)                   │
│                                   │        │  • Subgroups (demographics)                │
└───────────────────────────────────┘        │  • Versions (data snapshots)               │
                                             │  • Administrative levels (regions)         │
                                             └────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                   Query Flow Examples                                   │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                         │
│  1. General Question: "What is malaria?"                                                │
│     Agent → Agent LLM direct response                                                   │
│                                                                                         │
│  2. Document Query: "Selon les responsables gouvernementaux de la santé, quelles sont   │
│               les six régions qui représentent 90 % des cas de paludisme au Sénégal?"   │
│     Agent → ask_vector_db tool → ChromaDB (similarity search) → Context + LLM → Answer  │
│                                                                                         │
│  3. Data Analysis: "Which region has the highest malaria incidence indicator in 2022?"  │
│     Agent → SQL Agent → MCP Server → get_top_regions → Service Layer → CSV Data        │
│                                                                                         │
│  4. Hybrid Query: "What is R0 and what was it for Senegal in 2024?"                     │
│     Agent → MCPToolset + ask_vector_db (for Senegal data)                               │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘

Key Design Principles:
• Clean separation: LLM layer cannot import from service/ layer
• MCP as boundary: All structured data access goes through MCP server
• RAG for documents: Unstructured content (PDFs) accessed via vector DB
• Agent orchestration: Single coordinator decides tool routing
• Tool independence: Each tool operates independently
```
