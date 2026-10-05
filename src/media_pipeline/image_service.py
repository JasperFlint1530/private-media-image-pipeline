from __future__ import annotations

import os
from pathlib import Path

import openai
import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse

from .image_jobs import AssetStore, ImageJobProcessor, ImageJobRequest, ImageJobResult, InfraiImageGenerator

app = FastAPI(title="Private media image pipeline")


def asset_store() -> AssetStore:
    return AssetStore(Path(os.environ.get("MEDIA_ASSET_DIR", "var/media-assets")))


def processor(store: AssetStore = Depends(asset_store)) -> ImageJobProcessor:
    return ImageJobProcessor(InfraiImageGenerator(), store)


@app.post("/jobs", response_model=ImageJobResult, status_code=201)
def create_job(
    request: ImageJobRequest,
    jobs: ImageJobProcessor = Depends(processor),
) -> ImageJobResult:
    try:
        return jobs.process(request)
    except openai.RateLimitError as error:
        raise HTTPException(status_code=429, detail="Image capacity is busy; retry later") from error
    except openai.APIStatusError as error:
        status = error.status_code if 400 <= error.status_code < 500 else 502
        raise HTTPException(status_code=status, detail="Image request was not accepted") from error


@app.get("/assets/{asset_id}", response_class=FileResponse)
def deliver_asset(asset_id: str, store: AssetStore = Depends(asset_store)) -> FileResponse:
    validated = ImageJobRequest(asset_id=asset_id, prompt="delivery lookup")
    path = store.path_for(validated.asset_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(path, media_type="image/png", filename=f"{asset_id}.png")


def run() -> None:
    uvicorn.run("media_pipeline.image_service:app", host="127.0.0.1", port=8000)
