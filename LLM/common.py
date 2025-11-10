# Set Ollama host for communication inside the container
OLLAMA_HOST = "http://0.0.0.0:11434"

PDF_LOADER_PATH = './pdf_data'
CHROMA_DB_PATH = './model/chroma_db'

# Dictionary mapping model names to their required API key environment variable
# Empty string means local model (no API key required)
ALL_LLM_MODELS = {
    "llama3.2:3b-instruct-q4_K_M": "",  # Local Ollama model
    "gpt-4o": "OPENAI_API_KEY",
    "gpt-4o-mini": "OPENAI_API_KEY",
    "claude-sonnet-4-5-20250929": "ANTHROPIC_API_KEY",
    "gpt-oss-20b": "DATABRICKS_API_KEY",  # Databricks-hosted open-source model
    "gpt-oss-120b": "DATABRICKS_API_KEY"  # Databricks-hosted open-source model
}  # Can add more models like: "phi4-mini:3.8b-q4_K_M": ""

DEFAULT_LLM_MODEL_NAME = "gpt-4o-mini"  # Default to gpt-4o-mini

# MCP Server Configuration
import os
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:5010/sse")  # SSE endpoint for MCP server

# Databricks Configuration
DATABRICKS_API_BASE = os.getenv("DATABRICKS_API_BASE", "")


def ok_model_name(model_name: str) -> bool:
    return model_name and model_name in ALL_LLM_MODELS
