# Clean implementation of agent workflow
import os
import time
import litellm
import logging

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool import MCPToolset
from google.adk.tools import ToolContext
from google.genai import types

from common import ALL_LLM_MODELS, ok_model_name, OLLAMA_HOST, DATABRICKS_API_BASE

# Prevent litellm logger async task message during cleanup
litellm_logger = logging.getLogger("LiteLLM")
litellm_logger.propagate = False


def get_response_dict(query, answer, docs=None):
    docs = docs or []
    return {
        "query": query,
        "result": answer,
        "source_documents": [
            {
                "page_content": doc.page_content,
                "metadata": doc.metadata
            } for doc in docs
        ]
    }


def create_model(model_name: str = None, api_key: str = None) -> LiteLlm:
    """Create a LiteLlm model instance with appropriate configuration.

    Args:
        model_name: Name of the model to create
        api_key: API key for cloud providers (OpenAI, Anthropic, Databricks)

    Returns:
        Configured LiteLlm model instance

    Raises:
        ValueError: If model_name is invalid or required API key is missing
    """
    if not ok_model_name(model_name):
        raise ValueError("Model name not provided or is invalid.")

    # Get the required API key environment variable for this model
    api_key_env = ALL_LLM_MODELS[model_name]

    # Local Ollama model (no API key required)
    if not api_key_env:
        os.environ["OPENAI_API_KEY"] = "unused"
        os.environ["OPENAI_API_BASE"] = "http://localhost:11434"
        return LiteLlm(model=f"ollama_chat/{model_name}", api_base=OLLAMA_HOST, stream=True)

    # Cloud provider models (require API key)
    if not api_key:
        provider_name = api_key_env.replace("_API_KEY", "").replace("_", " ").title()
        raise ValueError(f"{provider_name} API key is required for {model_name}. Please provide your API key.")

    # Set the API key environment variable
    os.environ[api_key_env] = api_key

    # Databricks-hosted models (custom endpoint)
    if api_key_env == "DATABRICKS_API_KEY":
        # Construct Databricks endpoint URL
        # Format: https://{workspace}/serving-endpoints/databricks-{model_name}/invocations
        assert DATABRICKS_API_BASE, "DATABRICKS_API_BASE environment variable is not set."

        # Reset OPENAI_API_BASE if it was set
        if "OPENAI_API_BASE" in os.environ:
            del os.environ["OPENAI_API_BASE"]

        # LiteLLM uses "databricks" as the provider prefix
        return LiteLlm(
            model=f"databricks/databricks-{model_name}",
            stream=True
        )

    # Standard cloud providers (OpenAI, Anthropic)
    # Reset OPENAI_API_BASE to default (remove Ollama endpoint)
    if "OPENAI_API_BASE" in os.environ:
        del os.environ["OPENAI_API_BASE"]

    return LiteLlm(model=model_name, stream=True)


def create_coordinator_agent(model: LiteLlm, mcp_toolset: MCPToolset) -> Agent:
    """Create the coordinator agent with proper model configuration.

    Args:
        model: LiteLlm model instance to use for the coordinator agent.
        mcp_toolset: MCPToolset instance with MCP server connection, shared with SQL agent.

    Returns:
        Configured coordinator Agent instance.
    """
    from workflow.vector_db import ask_vector_db
    from workflow.sql_agent import create_sql_agent
    from google.adk.tools import AgentTool

    # Build tools list with vector DB and SQL Agent
    # Pass the same model and mcp_toolset to the SQL agent so it uses the same LLM and connection
    sql_agent = create_sql_agent(model=model, mcp_toolset=mcp_toolset)
    tools: list = [ask_vector_db, AgentTool(agent=sql_agent)]

    coordinator = Agent(
        name="GlobalHealthRouter",
        model=model,
        generate_content_config=types.GenerateContentConfig(
            temperature=0.2,
        ),
        tools=tools,
        description="I answer health and disease questions and analyze indicators data.",
        instruction="""You are an expert coordinator in **global health and disease data analysis**. Your sole function is to process a user's request and decide whether to answer directly or use available tools to generate the best answer.

### **Decision-Making Protocol (Follow Step-by-Step)**

1.  **Analyze the User's Request:** Determine if the core subject of the question is **Health/Disease-Related**, **Data Analysis**, or **None-Health/Disease-Related**.

2.  **Tool Selection Logic (Strict Rules):**
    * **Rule A: GENERAL QUESTIONS** ➡️ If the question can be answered from general knowledge without requiring specific numerical data or document-based information.
        * **Examples:** 
            - "What is the capital of Senegal?"
            - "What is the Reproduction Number (R₀) in epidemiology?"
            - "What are common symptoms of malaria?"
        * **Action:** **Generate the response yourself directly** without using any tools.

    * **Rule B: QUANTITATIVE DATA ANALYSIS** ➡️ If the question asks for specific numerical data, comparisons, rankings, aggregations, or analysis of health indicators data. If a user's question explicitly asks you to use MCP use the `SQLAnalyst` agent tool only.
        * **Examples:**
            - "Which region has the highest malaria incidence in 2022?"
            - "What are the top 5 regions by reported incidence?"
            - "Compare malaria rates across all regions"
            - "What was the test positivity rate in Tambacounda in 2023?"
            - "What is the average malaria incidence across all regions?"
            - "Show me regions where incidence increased between 2020 and 2022"
            - "Which regions have both high incidence and low net usage?"
        * **Action:** Use the `SQLAnalyst` agent tool
            - Pass the user's complete question to the SQL Agent
            - The SQL Agent will handle table selection, SQL generation, and query execution
            - Return the SQL Agent's answer directly to the user
            - DO NOT make additional tool calls after the SQL Agent responds

    * **Rule C: SPECIFIC HEALTH/DISEASE-RELATED (Document-Based)** ➡️ If the question asks for detailed information from documents, reports, or qualitative descriptions that require knowledge base data. If a user's question explicitly asks you to use RAG use the `ask_vector_db` tool only.
        * **Example:** "What was the **incidence rate** of Tuberculosis in India in 2023 according to the health bulletin?"
        * **Action:** Use **ONLY** the `ask_vector_db` tool.

3.  **Final Output Generation:**
    * **Pre-execution:** NEVER output your **step-by-step reasoning** and the **final tool decision(s)** *before* executing the tool calls.
    * **Post-execution:** When you receive information from tool(s) or answer directly, integrate it into a single, cohesive, factual, and concise final answer.
    * **Final Answer Content:** ONLY answer the question directly. Your final output MUST always contain ONLY necessary facts. Eliminate all filler phrases and flowery language.
    * **Final Answer Format:** The final output must be *ONLY* the answer itself. DO NOT preface the final answer with any unnecessary commentary.
        """,
    )

    return coordinator


async def run_workflow(query: str, api_key: str = None, model_name: str = None) -> dict:
    """Run the agent workflow and capture tool outputs.

    Args:
        query: The user's question
        api_key: API key (required for OpenAI/Anthropic models, optional for local models)
        model_name: The LLM model_name to use (defaults to DEFAULT_LLM_MODEL if not provided)

    Returns dict with: final_answer, references, execution_log, rag_used, mcp_used
    """
    from google.adk.runners import Runner, InMemorySessionService
    from google.genai.types import Content
    from workflow.vector_db import tool_outputs_context
    from workflow.data_tools import create_mcp_toolset

    # Initialize context for this workflow run
    tool_outputs_context.set({})

    # Setup session
    app_name = "SenegalMEG Agent App"
    session_service = InMemorySessionService()
    session_id = "session-123"
    await session_service.create_session(
        app_name=app_name,
        user_id="current_user",
        session_id=session_id
    )

    runner = None
    mcp_toolset = None

    try:
        start_time = time.time()

        llm_model: LiteLlm = create_model(model_name=model_name, api_key=api_key)

        # Create MCP toolset for SQL agent (shared connection)
        mcp_toolset = create_mcp_toolset()

        # Create and run agent
        runner = Runner(
            agent=create_coordinator_agent(model=llm_model, mcp_toolset=mcp_toolset),
            app_name=app_name,
            session_service=session_service
        )

        event_stream = runner.run_async(
            user_id="current_user",
            session_id=session_id,
            new_message=Content(role="user", parts=[{"text": query}])
        )

        # Collect agent's final answer
        final_answer = ""
        accumulated_text = ""
        execution_log = []
        mcp_used = False
        tools_called = []

        # Add agent start log
        execution_log.append({
            'type': 'agent_start',
            'agent': 'GlobalHealthRouter',
            'timestamp': 0.0,
            'message': 'Agent started processing query'
        })

        # Process events to get final answer and track tool usage
        async for event in event_stream:
            # Track tool calls
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        tool_name = part.function_call.name

                        # Track SQL Agent invocation
                        if tool_name == 'SQLAnalyst':
                            mcp_used = True
                        if tool_name not in tools_called:
                            tools_called.append(tool_name)
                            current_time = time.time() - start_time
                            tool_type = 'SQL Agent' if tool_name == 'SQLAnalyst' else 'Tool'
                            execution_log.append({
                                'type': 'tool_call',
                                'tool': tool_name,
                                'timestamp': current_time,
                                'message': f'Calling {tool_type}: {tool_name}'
                            })

                    # Check for function responses
                    if hasattr(part, 'function_response') and part.function_response:
                        tool_name = part.function_response.name
                        current_time = time.time() - start_time
                        response_preview = str(part.function_response.response)[:200] if part.function_response.response else ''
                        tool_type = 'SQL Agent' if tool_name == 'SQLAnalyst' else 'Tool'
                        execution_log.append({
                            'type': 'tool_result',
                            'tool': tool_name,
                            'timestamp': current_time,
                            'message': f'{tool_type} {tool_name} completed',
                            'preview': response_preview
                        })

            # Collect final answer
            if (event.content and event.content.parts and
                event.author == "GlobalHealthRouter" and
                event.content.role == "model"):

                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        if event.partial:
                            accumulated_text += part.text
                        else:
                            if accumulated_text:
                                final_answer = accumulated_text + part.text
                                accumulated_text = ""
                            else:
                                final_answer = part.text

                            if event.is_final_response():
                                break

        if not final_answer and accumulated_text:
            final_answer = accumulated_text

        elapsed = time.time() - start_time

        # Get tool outputs from context
        tool_outputs = tool_outputs_context.get()
        rag_data = tool_outputs.get('ask_vector_db', {})
    
        references = rag_data.get('references', [])
        rag_used = rag_data.get('called', False)

        # Build execution log from tool outputs
        if rag_used:
            execution_log.append({
                'type': 'tool_call',
                'tool': 'ask_vector_db',
                'timestamp': elapsed * 0.3,  # Approximate
                'message': 'Calling tool: ask_vector_db'
            })
            execution_log.append({
                'type': 'tool_result',
                'tool': 'ask_vector_db',
                'timestamp': elapsed * 0.7,  # Approximate
                'message': f'Tool ask_vector_db completed - Retrieved {rag_data.get("num_sources", 0)} sources',
                'preview': rag_data.get('answer', '')[:200]
            })

        execution_log.append({
            'type': 'agent_complete',
            'timestamp': elapsed,
            'duration': elapsed,
            'message': 'Agent completed processing'
        })

    finally:
        # Clean up resources in reverse order of creation
        # 1. Close runner first (stops agent execution)
        if runner:
            try:
                await runner.close()
            except Exception as e:
                print(f"Warning: Failed to close runner: {e}")

        # 2. Close MCP toolset connection
        if mcp_toolset:
            try:
                await mcp_toolset.close()
            except Exception as e:
                print(f"Warning: Failed to close MCP toolset: {e}")

        # 3. Clean up session
        if session_service:
            try:
                await session_service.delete_session(
                    app_name=app_name,
                    user_id="current_user",
                    session_id=session_id
                )
            except Exception as e:
                print(f"Warning: Failed to delete session: {e}")
        
        
    print(f"\n{'='*60}")
    print(f"WORKFLOW COMPLETE")
    print(f"Model Used: {model_name}")
    print(f"RAG Used: {rag_used}")
    print(f"MCP Used: {mcp_used}")
    print(f"References: {len(references)}")
    print(f"Duration: {elapsed:.2f}s")
    print(f"{'='*60}\n")

    return {
        'final_answer': final_answer,
        'references': references,
        'execution_log': execution_log,
        'rag_used': rag_used,
        'mcp_used': mcp_used,
        'tools_called': tools_called
    }

