import os
from pathlib import Path

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


@app.on_event("startup")
async def sync_indicators_with_service():
    import asyncio
    import httpx
    from storage.metadata_store import list_indicators

    indicators_dir = Path("/data/indicators")
    service_url = os.getenv("SERVICE_URL", "http://service:5000")

    for _ in range(5):
        try:
            httpx.get(f"{service_url}/", timeout=5.0)
            break
        except Exception:
            await asyncio.sleep(2)
    else:
        return

    for meta in list_indicators():
        if meta.hidden:
            try:
                httpx.post(
                    f"{service_url}/indicators/deregister",
                    json={"indicator_id": meta.id},
                    timeout=30.0,
                )
            except Exception:
                pass
        else:
            for csv_file in meta.csv_files:
                path = indicators_dir / csv_file
                if not path.exists():
                    continue
                try:
                    with open(path, "rb") as f:
                        httpx.post(
                            f"{service_url}/indicators/register",
                            files={"file": (csv_file, f, "text/csv")},
                            timeout=30.0,
                        )
                except Exception:
                    pass


@app.get("/")
async def root():
    return {"service": "mind", "status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5020)
