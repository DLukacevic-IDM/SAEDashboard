import uvicorn
from fastapi import FastAPI
from controllers import llm_runner
import warnings
import re

# Suppress the specific FutureWarning related to google-cloud-storage
warnings.filterwarnings(
    "ignore", 
    category=FutureWarning, 
    message=re.escape(
        "Support for google-cloud-storage < 3.0.0 will be removed in a future version of google-cloud-aiplatform. "
        "Please upgrade to google-cloud-storage >= 3.0.0."
    )
)

app = FastAPI()

app.include_router(llm_runner.router)


@app.get("/")
async def root():
    return {"message": "Hello World"}


if __name__ == "__main__":
    uvicorn.run(app, host='127.0.0.1', port=5001)
