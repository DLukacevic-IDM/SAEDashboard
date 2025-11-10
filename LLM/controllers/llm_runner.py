from fastapi import APIRouter, Request

from common import ok_model_name, DEFAULT_LLM_MODEL_NAME
from workflow.agent import get_response_dict

import time
router = APIRouter()


@router.post("/run")
async def run_ai_workflow(request: Request):
    """
    Example: /run
    Accepts: {"prompt": "your question", "api_key": "optional_api_key", "model_name": "optional_model_name"}

    API key requirements:
    - OpenAI models (gpt-*): Requires OpenAI API key
    - Anthropic models (claude-*): Requires Anthropic API key
    - Local models: No API key required

    return:
        {
            'input': 'test input',
            'output': 'test success'
        }
    """
    # Simulate processing the request

    data = await request.json()
    input_text = data.get("prompt", "")
    api_key = data.get("api_key", None)
    model_name = data.get("model_name", None)
    
    if not ok_model_name(model_name):
        print("Model name not provided (in the request) or is invalid, using default.")
        model_name = DEFAULT_LLM_MODEL_NAME

    if not input_text:
        return get_response_dict("", "No prompt provided")

    start_time = time.perf_counter()

    # Run agents workflow
    from workflow.agent import run_workflow
    workflow_result = await run_workflow(input_text, api_key=api_key, model_name=model_name)

    end_time = time.perf_counter()
    elapsed_time = end_time - start_time

    print(f"Elapsed time: {elapsed_time:.4f} seconds")

    # Extract workflow results
    final_answer = workflow_result.get('final_answer', '')
    references = workflow_result.get('references', [])
    execution_log = workflow_result.get('execution_log', [])
    rag_used = workflow_result.get('rag_used', False)
    mcp_used = workflow_result.get('mcp_used', False)

    # Format references to match expected frontend format
    # References from ask_vector_db now have: source, title, page_label, chunk_id, page_content_preview
    formatted_references = []
    for ref in references:
        formatted_references.append({
            'metadata': {
                'source': ref.get('source', ref.get('title', 'Unknown')),
                'page_label': ref.get('page_label', ref.get('page', 'Unknown')),
                'chunk_id': ref.get('chunk_id', 'Unknown')
            },
            'preview': ref.get('page_content_preview', '')
        })

    return {
        'input': input_text,
        'output': f"Model: {model_name}<br><br>Answer<br>{final_answer}",
        'references': formatted_references,
        'execution_log': execution_log,
        'rag_used': rag_used,
        'mcp_used': mcp_used,
        'elapsed_time': elapsed_time
    }


if __name__ == "__main__":
    
    # Test routs
    
    curl_commands = """

# RUN MCP CONTAINER FIRST
# docker-compose -f docker-compose.local.yml up mcp

# SET MODEL NAME and API KEY

export LLM_API_KEY=...

export LLM_MODEL_NAME_0=gpt-4o-mini
export LLM_MODEL_NAME_1=gpt-4o
export LLM_MODEL_NAME_2=claude-sonnet-4-5-20250929
export LLM_MODEL_NAME_3=llama3.2:3b-instruct-q4_K_M
export LLM_MODEL_NAME_4=gpt-oss-20b
export LLM_MODEL_NAME_5=gpt-oss-120b

export Q_1="What is the capital of Senegal?"
export Q_2="According to the health documents, what are the main barriers to family planning adoption in Senegal?"
export Q_3="Which region has the highest modern method usage in year 2022?"
export Q_33="Which region has the highest modern method usage in year 2020?"
export Q_4="What regions have the highest unmet need for family planning?"
export Q_5="Which region had the largest increase in modern method usage between 2015 and 2020? Provide the region name and the values for both years and by how much it increased?"
export Q_6="Compare modern method usage between urban and rural areas, tell me where the difference is greatest?"
export Q_7="Compare modern method and traditional method usage indicators, tell me which regions show strong preference for traditional methods?"
export Q_8="Which regions have the highest unmet need among women aged 15-24 in 2022?"
export Q_9="Show modern method usage trends for the Dakar region over time."
export Q_10="Which regions have the lowest modern method usage among women with parity 0?"


# ASK QUESTION

 curl -X POST http://localhost:5001/run \
    -H "Content-Type: application/json" \
    -d "{\"prompt\": \"${Q_1}\", \"model_name\": \"${LLM_MODEL_NAME_1}\", \"api_key\": \"${LLM_API_KEY}\"}" | jq --indent 4


#  | sed 's/<br>/\n/g'

"""