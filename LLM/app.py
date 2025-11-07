import uvicorn
from fastapi import FastAPI
from controllers import llm_runner


app = FastAPI()

app.include_router(llm_runner.router)


@app.get("/")
async def root():
    return {"message": "Hello World"}


if __name__ == "__main__":
    uvicorn.run(app, host='127.0.0.1', port=5001)
