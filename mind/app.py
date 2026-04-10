import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from controllers import upload, chat, indicators, files, data

app = FastAPI(title="SAE Indicator Manager")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(chat.router)
app.include_router(indicators.router)
app.include_router(files.router)
app.include_router(data.router)


@app.get("/")
async def root():
    return {"service": "mind", "status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5020)
